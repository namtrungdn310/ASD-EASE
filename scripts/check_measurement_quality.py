"""Kiểm điểm chất lượng C++ và gói serializer thực bằng schema backend."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory


def main():
    root = Path(__file__).resolve().parents[1]
    firmware = root / "ai/edge_firmware"
    sys.path.insert(0, str(root / "backend"))
    from app.schemas.ingestion import InboundTelemetry

    compiler = shutil.which(os.environ.get("CXX", "g++")) or shutil.which("clang++")
    if not compiler:
        raise RuntimeError("Cần g++/clang++ để kiểm tra C++")
    with TemporaryDirectory(prefix="asd-quality-") as temporary:
        exe = Path(temporary) / ("quality.exe" if os.name == "nt" else "quality")
        subprocess.run([
            compiler, "-std=c++17", "-Wall", "-Wextra", "-Werror", "-O2",
            "-I", str(firmware / "tests/native/stubs"), "-I", str(firmware / "include"),
            "-I", str(firmware / ".pio/libdeps/esp32s3_supermini/ArduinoJson/src"),
            *(str(firmware / name) for name in ["tests/native/measurement_quality_test.cpp",
              "src/communication/telemetry_serializer.cpp", "src/communication/session_protocol.cpp"]),
            "-o", str(exe)], check=True)
        result = subprocess.run([str(exe)], capture_output=True, text=True)
        if result.returncode:
            raise RuntimeError(result.stdout + result.stderr)
        packets = 0
        for line in result.stdout.splitlines():
            if line.startswith("{"):
                packet = InboundTelemetry.model_validate_json(line)
                assert packet.telemetry().schema_version == "1.2"
                packets += 1
            else:
                print(line)
        assert packets == 4
        print(f"PASS: {packets} C++ quality packets through backend runtime schema")


if __name__ == "__main__":
    main()
