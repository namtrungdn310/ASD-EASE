"""Đối chiếu phương pháp PPG đã công bố (MSPTDfast v2) với baseline cũ và ECG tham chiếu trên WESAD.

Chỉ chạy offline; không nạp firmware, không sửa dữ liệu gốc, không train model.
"""

from __future__ import annotations

import argparse
import csv
import gc
import hashlib
import importlib.metadata
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "ai"))

from src.preprocessing.ppg_published import (
    MSPTD_DEFAULT_CONFIG,
    PUBLISHED_METHOD_NAME,
    PUBLISHED_UPSTREAM_COMMIT,
    PUBLISHED_UPSTREAM_URL,
    estimate_hr_msptd,
)
from src.preprocessing.wesad import write_csv, write_json
from audit_wesad import ARCHIVE_SHA256, SUBJECTS


def read_csv_rows(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def compute_metrics(
    rows: list[dict], pred_key: str, error_key: str, ref_key: str = "ecg_hr_bpm"
) -> dict:
    """Tính toán thống kê độ phủ và sai số trên các cửa sổ."""
    total = len(rows)
    usable_ref = [r for r in rows if r[ref_key] is not None and r[ref_key] != ""]
    paired = [r for r in usable_ref if r[pred_key] is not None and r[pred_key] != ""]
    errors = np.array([abs(float(r[error_key])) for r in paired], dtype=float)

    return {
        "total_windows": total,
        "ecg_usable_windows": len(usable_ref),
        "covered_windows": len(paired),
        "coverage_all_windows_pct": float(100.0 * len(paired) / total) if total else 0.0,
        "coverage_among_ecg_pct": float(100.0 * len(paired) / len(usable_ref)) if usable_ref else 0.0,
        "mae_bpm": float(np.mean(errors)) if len(errors) else None,
        "median_ae_bpm": float(np.median(errors)) if len(errors) else None,
        "p90_ae_bpm": float(np.percentile(errors, 90)) if len(errors) else None,
        "within_5bpm_pct": float(100.0 * np.mean(errors <= 5.0)) if len(errors) else None,
    }


def compute_head_to_head(rows: list[dict]) -> dict:
    """So sánh trực diện cửa sổ chung (common) và cửa sổ mở rộng (disjoint)."""
    usable_ref = [r for r in rows if r["ecg_hr_bpm"] is not None and r["ecg_hr_bpm"] != ""]

    common = [
        r
        for r in usable_ref
        if r["old_ppg_bpm"] != "" and r["msptd_raw_bpm"] != ""
    ]
    disjoint_msptd = [
        r
        for r in usable_ref
        if r["old_ppg_bpm"] == "" and r["msptd_raw_bpm"] != ""
    ]

    err_old_common = [abs(float(r["old_error_bpm"])) for r in common if r["old_error_bpm"] != ""]
    err_msptd_common = [abs(float(r["msptd_raw_error_bpm"])) for r in common if r["msptd_raw_error_bpm"] != ""]
    err_disjoint = [abs(float(r["msptd_raw_error_bpm"])) for r in disjoint_msptd if r["msptd_raw_error_bpm"] != ""]

    return {
        "common_windows_count": len(common),
        "common_old_mae_bpm": float(np.mean(err_old_common)) if err_old_common else None,
        "common_old_p90_bpm": float(np.percentile(err_old_common, 90)) if err_old_common else None,
        "common_msptd_mae_bpm": float(np.mean(err_msptd_common)) if err_msptd_common else None,
        "common_msptd_p90_bpm": float(np.percentile(err_msptd_common, 90)) if err_msptd_common else None,
        "disjoint_windows_count": len(disjoint_msptd),
        "disjoint_msptd_mae_bpm": float(np.mean(err_disjoint)) if err_disjoint else None,
        "disjoint_msptd_median_bpm": float(np.median(err_disjoint)) if err_disjoint else None,
        "disjoint_msptd_p90_bpm": float(np.percentile(err_disjoint, 90)) if err_disjoint else None,
    }


def summarize_condition_groups(rows: list[dict]) -> dict:
    """Tổng hợp theo các nhóm nhãn: baseline (1), stress (2), amusement (3), binary (1/2/3)."""
    groups = {
        "all_labels": rows,
        "binary_task": [r for r in rows if str(r["source_label_code"]) in ("1", "2", "3")],
        "baseline": [r for r in rows if str(r["source_label_code"]) == "1"],
        "stress": [r for r in rows if str(r["source_label_code"]) == "2"],
        "amusement": [r for r in rows if str(r["source_label_code"]) == "3"],
    }

    summary = {}
    for name, subset in groups.items():
        summary[name] = {
            "old_causal_peaks": compute_metrics(subset, "old_ppg_bpm", "old_error_bpm"),
            "msptd_raw": compute_metrics(subset, "msptd_raw_bpm", "msptd_raw_error_bpm"),
            "msptd_gated": compute_metrics(subset, "msptd_gated_bpm", "msptd_gated_error_bpm"),
            "head_to_head": compute_head_to_head(subset),
        }
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, default=ROOT / "ai/data/external/wesad/archives/WESAD.zip")
    parser.add_argument("--normalized", type=Path, default=ROOT / "ai/data/interim/wesad/normalized-v1")
    parser.add_argument("--hr_review", type=Path, default=ROOT / "ai/data/interim/wesad/hr-ecg-review-v1")
    parser.add_argument("--output", type=Path, default=ROOT / "ai/data/interim/wesad/hr-published-review-v1")
    parser.add_argument("--subjects", choices=SUBJECTS, nargs="+", default=list(SUBJECTS))
    args = parser.parse_args()

    if args.output.exists():
        parser.error("Output directory already exists; specify a new directory.")

    # Kiểm tra hash archive
    with args.archive.open("rb") as f:
        digest = hashlib.file_digest(f, "sha256").hexdigest()
    if digest != ARCHIVE_SHA256:
        parser.error("Archive SHA-256 mismatch")

    norm_run = json.loads((args.normalized / "run.json").read_text(encoding="utf-8"))
    if norm_run["status"] != "COMPLETE":
        parser.error("Normalized data run is not COMPLETE")

    review_run = json.loads((args.hr_review / "report.json").read_text(encoding="utf-8"))
    if review_run["status"] != "COMPLETE":
        parser.error("Prior HR review run is not COMPLETE")

    args.output.mkdir(parents=True)
    started = datetime.now(timezone(timedelta(hours=7))).isoformat()

    report = {
        "version": "wesad-ppg-published-benchmark-v1",
        "status": "RUNNING",
        "started_at": started,
        "archive_sha256": digest,
        "published_method": {
            "name": PUBLISHED_METHOD_NAME,
            "upstream_commit": PUBLISHED_UPSTREAM_COMMIT,
            "upstream_url": PUBLISHED_UPSTREAM_URL,
            "config": MSPTD_DEFAULT_CONFIG,
        },
        "baseline_method": {
            "name": norm_run["hr_method"],
            "config": norm_run["hr_config"],
        },
        "reference_method": {
            "name": review_run["reference_method"],
            "config": review_run["reference_config"],
        },
        "subjects": args.subjects,
        "subject_summaries": [],
    }

    all_compared_rows = []

    try:
        for subject in args.subjects:
            print(f"Processing subject {subject}...", flush=True)
            norm_subj_dir = args.normalized / "signals" / subject
            review_subj_dir = args.hr_review / subject

            # Đọc BVP
            bvp_rows = read_csv_rows(norm_subj_dir / "bvp.csv")
            bvp_values = np.array(
                [float(r["value"]) if r["value"] != "" else np.nan for r in bvp_rows],
                dtype=float,
            )

            # Đọc so sánh cũ với ECG (đã có ecg_hr_bpm chuẩn)
            old_comp_rows = read_csv_rows(review_subj_dir / "comparison.csv")

            # Chạy MSPTDfast v2 trên BVP
            msptd_rows = estimate_hr_msptd(bvp_values, fs=64.0, config=MSPTD_DEFAULT_CONFIG)

            if len(msptd_rows) != len(old_comp_rows):
                raise ValueError(
                    f"Row count mismatch for {subject}: MSPTD {len(msptd_rows)} vs Old {len(old_comp_rows)}"
                )

            compared = []
            for m, o in zip(msptd_rows, old_comp_rows):
                if int(m["time_ms"]) != int(o["time_ms"]):
                    raise ValueError(f"Time alignment mismatch at {m['time_ms']} vs {o['time_ms']}")

                ecg_val = float(o["ecg_hr_bpm"]) if o["ecg_hr_bpm"] != "" else None
                old_ppg = float(o["ppg_hr_bpm"]) if o["ppg_hr_bpm"] != "" else None
                old_cand = float(o["ungated_candidate_bpm"]) if o["ungated_candidate_bpm"] != "" else None
                msptd_raw = m["raw_bpm"]
                msptd_gated = m["gated_bpm"]

                err_old = old_ppg - ecg_val if old_ppg is not None and ecg_val is not None else None
                err_msptd_raw = msptd_raw - ecg_val if msptd_raw is not None and ecg_val is not None else None
                err_msptd_gated = msptd_gated - ecg_val if msptd_gated is not None and ecg_val is not None else None

                row = {
                    "subject": subject,
                    "time_ms": m["time_ms"],
                    "window_start_ms": m["window_start_ms"],
                    "window_end_ms": m["window_end_ms"],
                    "source_label_code": o["source_label_code"],
                    "target_label": o["target_label"],
                    "ecg_hr_bpm": format(ecg_val, ".6f") if ecg_val is not None else "",
                    "reference_reason": o["reference_reason"],
                    "old_ppg_bpm": format(old_ppg, ".6f") if old_ppg is not None else "",
                    "old_candidate_bpm": format(old_cand, ".6f") if old_cand is not None else "",
                    "old_reason": o["ppg_reason"],
                    "old_error_bpm": format(err_old, ".6f") if err_old is not None else "",
                    "msptd_raw_bpm": format(msptd_raw, ".6f") if msptd_raw is not None else "",
                    "msptd_gated_bpm": format(msptd_gated, ".6f") if msptd_gated is not None else "",
                    "msptd_reason": m["reason"],
                    "msptd_peak_count": m["peak_count"],
                    "msptd_rr_cv": format(m["rr_cv"], ".6f") if m["rr_cv"] is not None else "",
                    "msptd_raw_error_bpm": format(err_msptd_raw, ".6f") if err_msptd_raw is not None else "",
                    "msptd_gated_error_bpm": format(err_msptd_gated, ".6f") if err_msptd_gated is not None else "",
                }
                compared.append(row)

            all_compared_rows.extend(compared)

            # Xuất thư mục subject
            subj_target = args.output / subject
            subj_target.mkdir(parents=True)
            cols = list(compared[0].keys())
            write_csv(subj_target / "comparison_published.csv", cols, (r.values() for r in compared))

            subj_summary = summarize_condition_groups(compared)
            subj_summary["subject"] = subject
            write_json(subj_target / "summary.json", subj_summary)
            report["subject_summaries"].append(subj_summary)

            del bvp_rows, bvp_values, old_comp_rows, msptd_rows, compared
            gc.collect()

        # Tổng hợp toàn bộ
        print("Computing pooled statistics across all subjects...", flush=True)
        report["pooled"] = summarize_condition_groups(all_compared_rows)

        # Macro subject metrics
        report["macro_subject"] = {}
        for condition in ("all_labels", "binary_task", "baseline", "stress", "amusement"):
            report["macro_subject"][condition] = {
                "old_causal_peaks_mae_bpm": float(
                    np.nanmean([
                        s[condition]["old_causal_peaks"]["mae_bpm"]
                        for s in report["subject_summaries"]
                        if s[condition]["old_causal_peaks"]["mae_bpm"] is not None
                    ])
                ),
                "msptd_raw_mae_bpm": float(
                    np.nanmean([
                        s[condition]["msptd_raw"]["mae_bpm"]
                        for s in report["subject_summaries"]
                        if s[condition]["msptd_raw"]["mae_bpm"] is not None
                    ])
                ),
                "msptd_gated_mae_bpm": float(
                    np.nanmean([
                        s[condition]["msptd_gated"]["mae_bpm"]
                        for s in report["subject_summaries"]
                        if s[condition]["msptd_gated"]["mae_bpm"] is not None
                    ])
                ),
                "old_causal_peaks_coverage_pct": float(
                    np.mean([s[condition]["old_causal_peaks"]["coverage_among_ecg_pct"] for s in report["subject_summaries"]])
                ),
                "msptd_raw_coverage_pct": float(
                    np.mean([s[condition]["msptd_raw"]["coverage_among_ecg_pct"] for s in report["subject_summaries"]])
                ),
                "msptd_gated_coverage_pct": float(
                    np.mean([s[condition]["msptd_gated"]["coverage_among_ecg_pct"] for s in report["subject_summaries"]])
                ),
            }

        report["status"] = "COMPLETE"
        report["completed_at"] = datetime.now(timezone(timedelta(hours=7))).isoformat()
        write_json(args.output / "report.json", report)
        print(f"Benchmark completed successfully! Results written to: {args.output}")

    except BaseException as error:
        report["status"] = "INTERRUPTED_OR_FAILED"
        report["error_type"] = type(error).__name__
        report["error_message"] = str(error)
        write_json(args.output / "report.json", report)
        raise


if __name__ == "__main__":
    main()
