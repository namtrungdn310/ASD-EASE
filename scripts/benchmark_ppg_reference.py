"""Đối chiếu C++ PpgRate với ECG-HR BIDMC; không thay nghiệm thu MAX30102/cổ tay.

Nguồn: Pimentel et al., BIDMC PPG and Respiration Dataset v1.0.0,
https://physionet.org/content/bidmc/1.0.0/, DOI10.13026/C2208R.
Dữ liệu mở theo Open Data Commons Attribution1.0; giữ LICENSE cùng bản tải.
Không tải tự động nếu không truyền --download. Không gửi dữ liệu ra MQTT/backend.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory
from urllib.request import urlopen

import numpy as np

BASE = "https://physionet.org/files/bidmc/1.0.0/"


def required_file(directory, name, download):
    target = directory / name
    if not target.exists():
        if not download:
            raise FileNotFoundError(f"Thiếu {target}; tải có kiểm soát bằng --download")
        with urlopen(BASE + name, timeout=60) as response:
            raw = response.read(8_000_001)
        if len(raw) > 8_000_000:
            raise ValueError("File quá lớn so với CSV BIDMC dự kiến")
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as file:
            file.write(raw)
    return target


def prepare_signal(path):
    data = np.genfromtxt(path, delimiter=",", names=True, autostrip=True)
    time = data[data.dtype.names[0]]
    ppg = data["PLETH"]
    if not np.isfinite(time).all() or not np.isfinite(ppg).all():
        raise ValueError("Waveform có giá trị thiếu; không tự nối qua khoảng mất")
    # CSV gốc làm tròn cột thời gian tới0,01s ở đoạn muộn, có timestamp lặp.
    # Khôi phục từ index/125 theo metadata; chỉ chấp nhận sai số làm tròn≤5ms.
    nominal = time[0] + np.arange(len(time))/125
    if np.max(np.abs(time-nominal)) > .005001:
        raise ValueError("Cột thời gian không khớp index/125Hz trong sai số làm tròn CSV")
    time = nominal
    # FIR161tap/Hann/cutoff20Hz trước đổi125→50Hz; zero-phase offline.
    # Biên được phản chiếu, score bỏ giây đầu/cuối; không gọi là acquisition thật.
    taps = np.arange(-80, 81)
    kernel = 2*(20/125)*np.sinc(2*(20/125)*taps)*np.hanning(len(taps))
    kernel /= kernel.sum()
    filtered = np.convolve(np.pad(ppg, (80, 80), mode="reflect"), kernel, mode="valid")
    target_time = np.arange(time[0], time[-1]+0.001, .02)
    # Ánh xạ affine cố định sang counts giả lập; không dùng HR để chuẩn hóa.
    # Một kênh PLETH vào IR; RED phẳng, không nhân đôi thành hai kênh độc lập.
    ir = np.rint(100000 + np.interp(target_time, time, filtered)*10000).astype(np.int64)
    if np.any((ir < 10000) | (ir >= 0x3ffff)):
        raise ValueError("Ánh xạ vượt dải; không clamp hoặc tự chỉnh theo đáp án")
    payload = "".join(f"{round(t*1000)+1000},80000,{v}\n" for t, v in zip(target_time, ir))
    return payload, time[-1]


def score(rows, numeric, last_time):
    nt = numeric[numeric.dtype.names[0]]
    reference = numeric["HR"]  # ECG-derived monitor HR; không dùng PULSE từ PPG làm đáp án.
    eligible = accepted = missing_reference = outside_range = 0
    errors = []
    accepted_rows = []
    for row in rows:
        end = (int(row[0])-1000)/1000
        if end < 12 or end > last_time-1:
            continue
        mask = (nt >= end-8) & (nt <= end)
        values = reference[mask]
        if len(values) < 8 or not np.isfinite(values).all():
            missing_reference += 1
            continue
        if np.any((values < 40) | (values > 200)):
            outside_range += 1
            continue
        eligible += 1
        if row[1] != "1":
            continue
        accepted += 1
        expected = float(np.median(values))
        estimate = float(row[2])
        errors.append(estimate-expected)
        accepted_rows.append({"end_s": end, "estimate_bpm": estimate, "reference_bpm": expected})
    absolute = np.abs(errors)
    return {
        "eligible_windows": eligible, "accepted_windows": accepted,
        "missing_reference_windows": missing_reference, "outside_range_windows": outside_range,
        "availability_pct": 100*accepted/eligible if eligible else None,
        "mae_bpm_on_accepted": float(np.mean(absolute)) if accepted else None,
        "p95_absolute_error_bpm": float(np.percentile(absolute, 95)) if accepted else None,
        "max_absolute_error_bpm": float(np.max(absolute)) if accepted else None,
        "over10bpm_windows": int(np.sum(absolute > 10)),
        "estimates": accepted_rows,
    }, errors


def main():
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records", type=int, nargs="+", default=[1, 2, 3, 4, 5], choices=range(1, 54))
    parser.add_argument("--download", action="store_true")
    parser.add_argument("--source-dir", type=Path, default=root/"backend/storage/local/bidmc-1.0.0")
    parser.add_argument("--report", type=Path, default=root/"backend/storage/local/ppg-reference-report.json")
    args = parser.parse_args()
    if len(args.records) != len(set(args.records)):
        parser.error("Mỗi recording chỉ được tính một lần")
    compiler = shutil.which(os.environ.get("CXX", "g++")) or shutil.which("clang++")
    if not compiler:
        raise RuntimeError("Cần g++/clang++ để dùng bộ xử lý C++ thực")
    license_file = required_file(args.source_dir, "LICENSE", args.download)
    manifest = required_file(args.source_dir, "SHA256SUMS.txt", args.download)
    checks = {parts[1].lstrip("*"): parts[0] for line in manifest.read_text().splitlines()
              if len(parts := line.split(maxsplit=1)) == 2}
    if hashlib.sha256(license_file.read_bytes()).hexdigest() != checks.get("LICENSE"):
        raise ValueError("SHA256 LICENSE không khớp manifest")
    report = {"dataset": "BIDMC1.0.0", "source": "https://physionet.org/content/bidmc/1.0.0/",
              "role": "development benchmark; not held-out clinical validation",
              "reference": "median ECG-derived monitor HR in trailing8s, sampled1Hz",
              "resampling": "index125Hz clock after validating CSV rounding; FIR161tap Hann20Hz,125to50Hz,affine counts,constant RED",
              "records": []}
    all_errors = []
    header = root/"ai/edge_firmware/include/processing/ppg_rate.h"
    report["ppg_rate_sha256"] = hashlib.sha256(header.read_bytes()).hexdigest()
    with TemporaryDirectory(prefix="asd-reference-") as temporary:
        executable = Path(temporary)/("rate.exe" if os.name == "nt" else "rate")
        subprocess.run([compiler, "-std=c++17", "-O2", "-Wall", "-Wextra", "-Werror",
                        "-I", str(root/"ai/edge_firmware/include"),
                        str(root/"ai/edge_firmware/tests/native/ppg_rate_test.cpp"), "-o", str(executable)], check=True)
        for index in args.records:
            files = []
            hashes = {}
            for kind in ["Signals", "Numerics"]:
                name = f"bidmc_csv/bidmc_{index:02d}_{kind}.csv"
                path = required_file(args.source_dir, name, args.download)
                digest = hashlib.sha256(path.read_bytes()).hexdigest()
                if digest != checks.get(name):
                    raise ValueError(f"SHA256 không khớp manifest: {name}")
                hashes[kind] = digest
                files.append(path)
            payload, last_time = prepare_signal(files[0])
            ran = subprocess.run([str(executable), "replay"], input=payload, capture_output=True, text=True, check=True)
            rows = [line.split(",") for line in ran.stdout.splitlines()]
            numeric = np.genfromtxt(files[1], delimiter=",", names=True, autostrip=True)
            result, errors = score(rows, numeric, last_time)
            record = {"record": index, "source_hashes": hashes, **result}
            report["records"].append(record)
            all_errors.extend(errors)
            print(json.dumps({k: v for k, v in record.items() if k not in ["estimates", "source_hashes"]}), flush=True)
    eligible = sum(r["eligible_windows"] for r in report["records"])
    accepted = len(all_errors)
    absolute = np.abs(all_errors)
    report["aggregate"] = {"eligible_windows": eligible, "accepted_windows": accepted,
                           "availability_pct": 100*accepted/eligible if eligible else None,
                           "mae_bpm_on_accepted": float(np.mean(absolute)) if accepted else None,
                           "p95_absolute_error_bpm": float(np.percentile(absolute, 95)) if accepted else None,
                           "over10bpm_windows": int(np.sum(absolute > 10))}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report["aggregate"]))
    print("Report:", args.report)


if __name__ == "__main__":
    main()
