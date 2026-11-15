"""Chạy driver sản xuất với kết quả task giả để kiểm tích hợp/timestamp/generation."""
import os
import argparse
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory

root=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--tracker',action='store_true')
args=parser.parse_args()
firmware=root/'ai/edge_firmware'
compiler=shutil.which(os.environ.get('CXX','g++')) or shutil.which('clang++')
if not compiler:raise RuntimeError('Need g++/clang++')
with TemporaryDirectory(prefix='asd-hybrid-driver-') as temp:
    output=Path(temp)/('test.exe' if os.name=='nt' else 'test')
    subprocess.run([compiler,'-std=c++17','-O1','-Wall','-Wextra','-Werror','-DASD_PPG_NATIVE_HYBRID_TEST=1',
                    f'-DASD_PPG_TRACKER_ENABLED={int(args.tracker)}',
                    '-I',str(firmware/'tests/native/stubs'),'-I',str(firmware/'include'),
                    str(firmware/'tests/native/ppg_hybrid_driver_test.cpp'),
                    str(firmware/'src/sensors/MAX30102Sensor.cpp'),'-o',str(output)],check=True)
    subprocess.run([str(output)],check=True)
