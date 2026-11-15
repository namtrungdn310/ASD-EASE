"""Hồi quy end-to-end bộ lọc/HR C++ thật và quality offline trên tín hiệu tổng hợp."""
import os
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory

from benchmark_ppg_candidates import ROOT, controls, evaluate
from ppg_quality_candidate import Evaluator, EXTRA_ALGORITHMS


def main():
    compiler = shutil.which(os.environ.get('CXX','g++')) or shutil.which('clang++')
    if not compiler:
        raise RuntimeError('Need g++/clang++ for actual production-filter pipeline test')
    wanted = ['SYNTHETIC_clean_80','SYNTHETIC_colored_73_1000','SYNTHETIC_white_17_1000']
    data = {name:(t,x) for name,t,x in controls() if name in wanted}
    cases = 0
    with TemporaryDirectory(prefix='asd-quality-test-') as temp:
        exe = Path(temp)/('test.exe' if os.name=='nt' else 'test')
        subprocess.run([compiler,'-std=c++17','-O2','-Wall','-Wextra','-Werror','-I',str(ROOT/'ai/edge_firmware/include'),
                        str(ROOT/'ai/edge_firmware/tests/native/ppg_benchmark_harness.cpp'),'-o',str(exe)],check=True)
        for name in wanted+['SYNTHETIC_clean80_gap']:
            t,x = data['SYNTHETIC_clean_80' if name.endswith('_gap') else name]
            payload = ''.join(f'{1000+round(s*1000)},{int(80000+v*.8)},{int(100000+v)}\n'
                              for s,v in zip(t,x) if not (name.endswith('_gap') and 20<=s<26))
            report = evaluate(exe,payload,extra_algorithms=EXTRA_ALGORITHMS,extra_evaluator=Evaluator())
            if name=='SYNTHETIC_clean_80':
                assert report['summary']['current_cpp']['accepted_windows']==47
                assert report['summary']['hybrid_strict']['accepted_windows']==47
                assert report['summary']['quality_strict']['accepted_windows']>40
                assert all(abs(r['predictions']['hybrid_strict']-80)<2 for r in report['rows'])
            elif name.endswith('_gap'):
                rows = {r['end_s']:r for r in report['rows']}
                for end in range(21,26):
                    assert all(value is None for value in rows[end]['predictions'].values())
                for end in range(26,37):
                    assert rows[end]['predictions']['quality_strict'] is None
                assert any(r['predictions']['hybrid_strict'] is not None for r in report['rows'] if r['end_s']>=40)
            else:
                assert report['summary']['current_cpp']['accepted_windows']==0
                assert report['summary']['hybrid_strict']['accepted_windows']==0
            cases += 1
    print(f'PASS: {cases} actual C++/quality pipeline controls (clean, colored/white noise, gap recovery)')


if __name__=='__main__':
    main()
