"""Biên dịch/test bộ đọc FIFO C++ dùng trong driver; không thay nghiệm thu ESP."""
import os
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory


def main():
    root = Path(__file__).resolve().parents[1]
    firmware = root / "ai/edge_firmware"
    compiler = shutil.which(os.environ.get("CXX", "g++")) or shutil.which("clang++")
    if not compiler:
        raise RuntimeError("Cần g++/clang++ để test bộ đọc FIFO C++ thật")
    with TemporaryDirectory(prefix="asd-ppg-") as temporary:
        executable = Path(temporary) / ("ppg.exe" if os.name == "nt" else "ppg")
        subprocess.run([
            compiler, "-std=c++17", "-Wall", "-Wextra", "-Werror", "-O1",
            "-I", str(firmware / "include"),
            str(firmware / "tests/native/ppg_fifo_test.cpp"), "-o", str(executable),
        ], check=True)
        subprocess.run([str(executable)], check=True)


if __name__ == "__main__":
    main()
