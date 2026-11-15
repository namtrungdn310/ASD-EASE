"""Thu PPG thô chẩn đoán qua USB; dữ liệu Dashboard vẫn dùng MQTT, không qua script này."""
import argparse
import csv
from datetime import datetime
import json
from pathlib import Path
import re
import time
import uuid

import serial


def capture_trace(directory, port_name, seconds, *, port_factory=serial.Serial, clock=time.monotonic):
    """Giữ raw và chẩn đoán đã thu khi USB bị rút; không tự nối lại hoặc reset ESP."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    output = directory / ("ppg-" + datetime.now().strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:6] + ".csv")
    motion_output = output.with_name(output.stem + "-motion.csv")
    motion_count = 0
    port = None
    count = 0
    intervals = []
    previous = None
    dropped = 0
    diagnostics = []
    error = None
    cleanup_errors = []
    finished = False
    trace_requested = False
    started = clock()
    try:
        port = port_factory(port=None, baudrate=115200, timeout=.2)
        port.dtr = port.rts = False
        port.port = port_name
        port.open()
        port.reset_input_buffer()
        trace_requested = True
        port.write(b"p")
        with output.open("x", newline="", encoding="utf-8") as file, motion_output.open("x", newline="", encoding="utf-8") as motion_file:
            writer = csv.writer(file)
            writer.writerow(["t_ms", "red", "ir"])
            motion_writer = csv.writer(motion_file)
            motion_writer.writerow(["t_ms", "imu_t_ms", "valid", "ax_g", "ay_g", "az_g",
                                   "gx_90dps", "gy_90dps", "gz_90dps", "red_led", "ir_led", "exposure_generation"])
            started = clock()
            end = started + seconds
            while clock() < end:
                line = port.readline().decode("utf-8", errors="replace").strip()
                match = re.fullmatch(r"\[PPG-RAW\] t=(\d+) red=(\d+) ir=(\d+)(?: imu=(\d+),([01]),([-+0-9.,]+) led=(\d+),(\d+),(\d+))?", line)
                if match:
                    measured, red, ir = map(int, match.groups()[:3])
                    writer.writerow([measured, red, ir])
                    if match.group(4) is not None:
                        axes = match.group(6).split(",")
                        if len(axes) == 6:
                            motion_writer.writerow([measured, match.group(4), match.group(5), *axes,
                                                    match.group(7), match.group(8), match.group(9)])
                            motion_count += 1
                    if previous is not None:
                        intervals.append(measured - previous)
                    previous = measured
                    count += 1
                elif line.startswith("[PPG-TRACE]"):
                    match = re.search(r"dropped=(\d+)", line)
                    if match:
                        dropped = max(dropped, int(match[1]))
                elif line.startswith(("[PPG-OPT]", "[PPG-DAQ]", "[PPG-REG]", "[PPG-RATE]", "[PPG-INIT]", "[PPG-IO]", "[PPG-HYBRID]", "[PPG-TRACK]", "[PPG-CAUSE]", "[PPG-WRIST]", "[IMU-DAQ]", "[NET]", "[NET-LINK]")):
                    # Chỉ lưu counters/chẩn đoán, không lưu dòng CONFIG/SSID/credential.
                    diagnostics.append(line)
            finished = True
    except (serial.SerialException, OSError, KeyboardInterrupt) as failure:
        error = {"type": type(failure).__name__, "message": str(failure)[:300]}
    finally:
        elapsed = clock() - started
        if port is not None:
            try:
                if port.is_open and trace_requested:
                    port.write(b"q")
            except (serial.SerialException, OSError) as failure:
                cleanup_errors.append({"operation": "stop_trace", "type": type(failure).__name__,
                                       "message": str(failure)[:300]})
            finally:
                try:
                    port.close()
                except (serial.SerialException, OSError) as failure:
                    cleanup_errors.append({"operation": "close_port", "type": type(failure).__name__,
                                           "message": str(failure)[:300]})
    status = "complete" if finished and count else "no_samples" if finished else "interrupted"
    details = {"file": str(output), "motion_file": str(motion_output), "motion_rows": motion_count,
               "motion_units": "acceleration/g, angular_velocity/(90 degrees/s), before PPG bandpass",
               "samples": count, "requested_seconds": seconds,
               "capture_status": status, "elapsed_seconds": round(elapsed, 3),
               "capture_error": error, "cleanup_errors": cleanup_errors,
               "max_interval_ms": max(intervals, default=None), "trace_dropped": dropped,
               "nonpositive_intervals": sum(delta <= 0 for delta in intervals)}
    output.with_suffix(".json").write_text(json.dumps({**details, "diagnostics": diagnostics}, ensure_ascii=False, indent=2), encoding="utf-8")
    return details


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", default="COM7")
    parser.add_argument("--seconds", type=int, default=35, choices=range(10, 56), metavar="10..55")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    details = capture_trace(root / "backend/storage/local", args.port, args.seconds)
    print(json.dumps(details, ensure_ascii=False))
    if details["capture_status"] == "interrupted":
        raise SystemExit("Lượt thu bị gián đoạn. Đã lưu phần dữ liệu/chẩn đoán còn thu được; không tự nối lại hoặc reset ESP.")
    if details["samples"] == 0:
        raise SystemExit("Không có PPG-RAW: kiểm tra firmware có hỗ trợ lệnh p/q và Serial diagnostics.")
    if details["cleanup_errors"]:
        raise SystemExit("Đã lưu lượt thu nhưng chưa xác nhận dừng trace qua USB; xem cleanup_errors trong JSON.")


if __name__ == "__main__":
    main()
