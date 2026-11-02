"""Biên dịch các tổ hợp header mà main firmware có thể chưa dùng."""

import json
from pathlib import Path
import subprocess
import sys


def main() -> int:
    project = Path(__file__).resolve().parents[2] / "ai" / "edge_firmware"
    metadata_run = subprocess.run(
        [
            sys.executable, "-m", "platformio", "project", "metadata",
            "-d", str(project), "-e", "esp32s3_supermini", "--json-output",
        ],
        check=True, capture_output=True, text=True,
    )
    metadata = json.loads(metadata_run.stdout)["esp32s3_supermini"]
    flags = [
        flag for flag in metadata["cxx_flags"]
        if flag not in ("-MMD", "-MD", "-MP")
    ]
    for define in metadata["defines"]:
        if isinstance(define, list):
            define = "=".join(str(value) for value in define)
        flags.append("-D" + define)
    for path in metadata["includes"]["build"]:
        flags.extend(["-I", path])

    combinations = (
        ("sensor_config.h",),
        (
            "pins.h", "sensor_config.h", "board_config.h", "interfaces.h",
            "common_types.h", "pins.h", "sensor_config.h",
        ),
        (
            "common_types.h", "interfaces.h", "board_config.h",
            "sensor_config.h", "pins.h",
        ),
        (
            "interfaces.h", "MAX30102Sensor.h", "MPU6050Sensor.h",
            "GSRSensor.h", "pins.h", "sensor_config.h",
        ),
    )
    for headers in combinations:
        source = "\n".join(f'#include "{header}"' for header in headers)
        # Kiểm tra alias và kiểu dữ liệu, không gán cứng giá trị phần cứng.
        source += """
static_assert(PIN_I2C_SDA == PIN_MAX30102_SDA, "SDA alias mismatch");
static_assert(PIN_I2C_SCL == PIN_MAX30102_SCL, "SCL alias mismatch");
static_assert(PPG_SAMPLE_RATE_HZ > 0, "PPG rate must be positive");
static_assert(IMU_SAMPLE_RATE_HZ > 0, "IMU rate must be positive");
static_assert(GSR_SAMPLE_RATE_HZ > 0, "GSR rate must be positive");
constexpr Availability unavailable = Availability::UNAVAILABLE;
"""
        if "interfaces.h" in headers:
            source += """
TelemetryFrame frame{};
void checkInterfaces() {
    frame.state = EngineeringState::CALIBRATING;
    SignalProcessor processor;
    Availability result = processor.begin();
    (void)result;
}
"""
        subprocess.run(
            [metadata["cxx_path"], *flags, "-fsyntax-only", "-x", "c++", "-"],
            input=source, text=True, cwd=project, check=True,
        )
        print("PASS: " + " + ".join(headers))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as error:
        if error.stderr:
            print(error.stderr, file=sys.stderr)
        raise SystemExit(error.returncode)
