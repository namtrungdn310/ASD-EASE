"""So sánh cùng input với snapshot trước thay đổi; raw người không gán nhãn HR."""
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import random
import shutil
import subprocess
import math
import argparse
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-include", type=Path, help="Thư mục include có processing/ của bản trước sửa")
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--trace", type=Path, action="append", default=[])
    args = parser.parse_args()
    pointer = ROOT / "backend/storage/local/hr-v2-current.json"
    saved = Path(json.loads(pointer.read_text())["directory"]) if pointer.exists() else None
    if args.baseline_include is None and saved is None:
        parser.error("Cần --baseline-include trỏ bản trước sửa; không tự coi code hiện tại là baseline")
    directory = args.output_dir or saved or ROOT / "backend/storage/local/hr-v2-benchmark"
    directory.mkdir(parents=True, exist_ok=True)
    baseline = args.baseline_include or saved / "baseline"
    if baseline.resolve() == (ROOT / "ai/edge_firmware/include").resolve():
        parser.error("Baseline phải là phiên bản trước sửa")
    compiler = shutil.which(os.environ.get("CXX", "g++")) or shutil.which("clang++")
    source = ROOT / "ai/edge_firmware/tests/native/ppg_optimization_replay.cpp"
    executables = {}
    for name, includes in (("before", baseline), ("after", ROOT / "ai/edge_firmware/include")):
        executable = directory / (name + (".exe" if os.name == "nt" else ""))
        subprocess.run([compiler, "-std=c++17", "-O2", "-Wall", "-Wextra", "-Werror",
                        *(["-DPPG_OPTIMIZATION_V2"] if name == "after" else []),
                        "-I", str(includes), str(source), "-o", str(executable)], check=True)
        executables[name] = executable
    records = []

    def evaluate(name, rows, reference=None, category="SYNTHETIC"):
        text = "\n".join(",".join(map(str, row)) for row in rows) + "\n"
        record = {"name": name, "category": category, "reference_bpm": reference,
                  "input_sha256": hashlib.sha256(text.encode()).hexdigest(), "profiles": {}}
        for profile, exe in executables.items():
            output = subprocess.run([str(exe)], input=text, capture_output=True, text=True, check=True)
            windows = [[float(v) for v in line] for line in csv.reader(io.StringIO(output.stdout)) if line]
            accepted = [row for row in windows if row[1]]
            errors = [abs(row[2] - reference) for row in accepted] if reference is not None else []
            record["profiles"][profile] = {
                "evaluations": len(windows), "accepted": len(accepted),
                "availability_pct": 100 * len(accepted) / len(windows) if windows else 0,
                "mae_bpm": sum(errors) / len(errors) if errors else None,
                "errors_over_10": sum(error > 10 for error in errors),
                "range": [min(row[2] for row in accepted), max(row[2] for row in accepted)] if accepted else None,
                "mean_sqi": sum(row[3] for row in accepted) / len(accepted) if accepted and profile == "after" else None,
                "corrected_windows": sum(row[6] for row in windows),
            }
        records.append(record)
        print(json.dumps(record), flush=True)

    for bpm in (40, 60, 80, 110, 150, 180, 200):
        for motion in (False, True):
            rows = []
            cadence = 132 if abs(bpm - 132) > 20 else 75
            for i in range(3000):
                t = i / 50
                pulse = 100 * math.sin(2 * math.pi * bpm * t / 60)
                artifact = 250 * math.sin(2 * math.pi * cadence * t / 60) if motion else 0
                rows.append([1000 + 20 * i, int(80000 + .7 * pulse + .8 * artifact),
                             int(100000 + pulse + artifact), artifact / 1000, 0, 0, 0, 0, 0, 1, 0])
            evaluate(f"pulse_{bpm}_{'motion' if motion else 'still'}", rows, bpm)
    for kind in ("flat", "white", "colored", "motion_only"):
        rng = random.Random(148811); drift = 0; rows = []
        for i in range(3000):
            noise = rng.gauss(0, 150); drift = .95 * drift + .05 * noise
            artifact = 250 * math.sin(2 * math.pi * 100 * i / 3000)
            x = {"flat": 0, "white": noise, "colored": drift, "motion_only": artifact}[kind]
            rows.append([1000 + i * 20, int(80000 + .7 * x), int(100000 + x),
                         artifact / 1000 if kind == "motion_only" else 0, 0, 0, 0, 0, 0, 1, 0])
        evaluate(kind, rows)
    trace_paths = []
    manifest = ROOT / "backend/storage/local/hr-optical-manifest-20261107.json"
    if manifest.exists():
        for trace in json.loads(manifest.read_text())["traces"]:
            if not trace["included_in_four_complete_trials"]:
                continue
            trace_paths.append(ROOT / trace["raw_csv"])
    for path in dict.fromkeys(trace_paths + args.trace):
        if not path.exists():
            raise FileNotFoundError(path)
        motion_path = path.with_name(path.stem + "-motion.csv")
        refs = {}
        if motion_path.exists():
            with motion_path.open(encoding="utf-8-sig", newline="") as file:
                refs = {int(row["t_ms"]): row for row in csv.DictReader(file)}
        rows = []
        with path.open(encoding="utf-8-sig", newline="") as file:
            for row in csv.DictReader(file):
                raw = [int(row[key]) for key in ("t_ms", "red", "ir")]
                ref = refs.get(raw[0])
                if ref:
                    aligned = int(ref["valid"]) == 1 and abs(raw[0] - int(ref["imu_t_ms"])) <= 25
                    raw += [float(ref[key]) for key in ("ax_g", "ay_g", "az_g", "gx_90dps", "gy_90dps", "gz_90dps")]
                    raw += [int(aligned), int(ref["exposure_generation"])]
                rows.append(raw)
        evaluate(path.name, rows, category="DEVICE_no_synchronous_reference_" + ("aligned_IMU" if refs else "no_IMU"))
    report = {"role": "development comparison; not clinical or independent human validation",
              "same_inputs": True, "AGC_replayed": False,
              "note": "AGC decisions tested separately on fake I2C; human HR has no synchronous reference.",
              "source_hashes": {profile: {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                                         for path in (includes / "processing").glob("*.h")}
                                for profile, includes in (("before", baseline), ("after", ROOT / "ai/edge_firmware/include"))},
              "records": records}
    report_path = directory / ("comparison-" + datetime.now().strftime("%Y%m%d-%H%M%S") + ".json")
    report_path.write_text(json.dumps(report, indent=2, allow_nan=False), encoding="utf-8")
    print("REPORT", report_path)


if __name__ == "__main__":
    main()
