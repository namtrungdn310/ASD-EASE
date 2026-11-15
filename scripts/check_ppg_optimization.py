"""Kiểm AGC/kênh/SQI/khử nhiễu bằng core C++ thật; không giả là số đo người."""
import os
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory


def main():
    root = Path(__file__).resolve().parents[1]
    compiler = shutil.which(os.environ.get("CXX", "g++")) or shutil.which("clang++")
    if not compiler:
        raise RuntimeError("Cần g++ hoặc clang++")
    with TemporaryDirectory(prefix="asd-ppg-optimization-") as temporary:
        executable = Path(temporary) / ("check.exe" if os.name == "nt" else "check")
        subprocess.run([compiler, "-std=c++17", "-O2", "-Wall", "-Wextra", "-Werror",
                        "-I", str(root / "ai/edge_firmware/include"),
                        str(root / "ai/edge_firmware/tests/native/ppg_optimization_test.cpp"),
                        "-o", str(executable)], check=True)
        subprocess.run([str(executable)], check=True)


if __name__ == "__main__":
    main()
