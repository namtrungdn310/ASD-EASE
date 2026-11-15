"""Chạy driver sản xuất với I2C/ADC/clock giả; không thay nghiệm thu phần cứng."""
import os
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory


def main():
    argparse.ArgumentParser(description=__doc__).parse_args()
    root = Path(__file__).resolve().parents[1]
    firmware = root / "ai/edge_firmware"
    sys.path.insert(0, str(root / "backend"))
    from app.schemas.ingestion import InboundTelemetry
    compiler = shutil.which(os.environ.get("CXX", "g++")) or shutil.which("clang++")
    if not compiler:
        raise RuntimeError("Cần g++/clang++ để kiểm tra driver C++")
    json_include = firmware / ".pio/libdeps/esp32s3_supermini/ArduinoJson/src"
    with TemporaryDirectory(prefix="asd-sensors-") as temporary:
        rate_test = Path(temporary) / ("ppg-rate.exe" if os.name == "nt" else "ppg-rate")
        subprocess.run([compiler, "-std=c++17", "-Wall", "-Wextra", "-Werror", "-O2",
                        "-I", str(firmware / "include"),
                        str(firmware / "tests/native/ppg_rate_test.cpp"), "-o", str(rate_test)], check=True)
        subprocess.run([str(rate_test)], check=True)
        executable = Path(temporary) / ("sensors.exe" if os.name == "nt" else "sensors")
        sources = ["tests/native/sensor_drivers_test.cpp", "src/sensors/MAX30102Sensor.cpp",
                   "src/sensors/MPU6050Sensor.cpp", "src/sensors/GSRSensor.cpp",
                   "src/filter/EMA.cpp", "src/communication/telemetry_serializer.cpp",
                   "src/communication/session_protocol.cpp"]
        subprocess.run([
            compiler, "-std=c++17", "-Wall", "-Wextra", "-Werror", "-O1",
            # Đối chiếu PpgRate offline, không phải firmware để nạp lên ESP.
            "-DASD_PPG_TRACKER_ENABLED=0",
            "-I", str(firmware / "tests/native/stubs"),
            "-I", str(firmware / "include"), "-I", str(json_include),
            *(str(firmware / source) for source in sources), "-o", str(executable),
        ], check=True)
        ran = subprocess.run([str(executable)], capture_output=True, text=True)
        if ran.returncode:
            raise RuntimeError(ran.stdout + ran.stderr)
        packets = 0
        for line in ran.stdout.splitlines():
            if line.startswith("{"):
                packet = json.loads(line)
                InboundTelemetry.model_validate(packet)
                assert packet["data_origin"] == "SYNTHETIC"
                assert packet["firmware_version"].endswith("-native-baseline"), "Sai nhãn test offline"
                packets += 1
            else:
                print(line)
        print("Native baseline: acquisition 200Hz/avg4, LED10mA; not a deployable firmware profile")
        assert packets >= 10, "Thiếu bằng chứng serializer từ driver thực"
        print(f"PASS: {packets} production driver snapshots through C++ serializer and backend schema")


if __name__ == "__main__":
    main()
