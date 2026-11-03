"""Biên dịch và điều khiển core C++ thật bằng clock/transport giả trên máy."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import threading
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
FIRMWARE = ROOT / "ai" / "edge_firmware"


class NativeFirmware:
    def __init__(self):
        self.temporary = TemporaryDirectory(prefix="asd-native-")
        self.mutex = threading.Lock()
        compiler = shutil.which(os.environ.get("CXX", "g++")) or shutil.which("clang++")
        if not compiler:
            raise RuntimeError("Cần g++/clang++ native; không thay test C++ bằng fixture Python")
        include = FIRMWARE / ".pio/libdeps/esp32s3_supermini/ArduinoJson/src"
        if not include.is_dir():
            raise RuntimeError("Chạy platformio run -d ai/edge_firmware -e esp32s3_supermini trước để cài ArduinoJson đã pin")
        self.executable = Path(self.temporary.name) / ("protocol.exe" if os.name == "nt" else "protocol")
        compiled = subprocess.run([compiler, "-std=c++17", "-Wall", "-Wextra", "-Werror", "-O1", "-DARDUINOJSON_ENABLE_DEPRECATED=0",
            "-I", str(FIRMWARE / "include"), "-I", str(include),
            str(FIRMWARE / "src/communication/session_protocol.cpp"), str(FIRMWARE / "tests/native/protocol_harness.cpp"),
            "-o", str(self.executable)], capture_output=True, text=True)
        if compiled.returncode:
            self.temporary.cleanup()
            raise RuntimeError(compiled.stderr)
        self.process = subprocess.Popen([str(self.executable)], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, encoding="utf-8")

    def call(self, operation, now=0, **values):
        with self.mutex:
            return self._call(operation, now, **values)

    def _call(self, operation, now=0, **values):
        if operation == "receive" and "payload" in values and "wire" not in values:
            # Giữ nguyên token JSON1.0 để thử strict-int, không qua serialize lại của ArduinoJson.
            values["wire"] = json.dumps(values.pop("payload"), allow_nan=False, separators=(",", ":"))
        self.process.stdin.write(json.dumps({"op": operation, "now": now, **values}, allow_nan=False) + "\n")
        self.process.stdin.flush()
        line = self.process.stdout.readline()
        if not line:
            raise RuntimeError("Native firmware stopped: " + self.process.stderr.read())
        return json.loads(line)

    def close(self):
        if getattr(self, "process", None):
            self.process.stdin.close()
            self.process.wait(timeout=5)
            self.process.stdout.close(); self.process.stderr.close()
        self.temporary.cleanup()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
