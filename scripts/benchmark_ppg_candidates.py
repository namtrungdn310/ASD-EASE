"""Bước2: đối chiếu PpgRate C++ và bản chuyển MSPTDfast v2 trên cùng dữ liệu.

Chỉ offline; không đổi/nạp firmware hoặc gửi gói đo vào backend. NumPy đã có
trong môi trường dự án. --download mới tải CSV có hash chính thức từ PhysioNet.
"""
import argparse
import hashlib
import io
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory
import time

import numpy as np

from benchmark_ppg_reference import required_file, prepare_signal
from ppg_msptd_reference import heart_rate, UPSTREAM_COMMIT, UPSTREAM_URL

ROOT = Path(__file__).resolve().parents[1]
ALGORITHMS = ['current_cpp', 'msptd_ir_candidate', 'msptd_red_candidate']
DEFAULT_TRACES = [
    'ppg-20261106-174444-63d1de.csv',  # finger0.3.11
    'ppg-20261106-174808-5adb40.csv',  # wrist0.3.11
    'ppg-20261106-175215-0ab533.csv',  # wrist repeat/no pressing0.3.11
    'ppg-20261106-022934-82bbc4.csv',  # finger0.3.10, includes6.221s gap
]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def summarize(rows, name, reference_available):
    values = [r['predictions'][name] for r in rows if r['predictions'][name] is not None]
    errors = [abs(r['predictions'][name]-r['reference_bpm']) for r in rows
              if r['predictions'][name] is not None and r['reference_bpm'] is not None]
    return {
        'eligible_windows': len(rows), 'accepted_windows': len(values),
        'availability_pct': 100*len(values)/len(rows) if rows else None,
        'bpm_range': [min(values),max(values)] if values else None,
        'median_bpm': float(np.median(values)) if values else None,
        'reference_available': reference_available,
        'mae_on_accepted_bpm': float(np.mean(errors)) if errors else None,
        'p95_absolute_error_bpm': float(np.percentile(errors,95)) if errors else None,
        'over10bpm_windows': int(np.sum(np.array(errors)>10)) if reference_available else None,
    }


def evaluate(executable, payload, *, numeric=None, last_time=None, reference_constant=None,
             extra_algorithms=(), extra_evaluator=None):
    raw = np.genfromtxt(io.StringIO(payload),delimiter=',',invalid_raise=True)
    if raw.ndim != 2 or raw.shape[1] != 3 or not np.isfinite(raw).all():
        raise ValueError('CSV phải có timestamp,RED,IR hữu hạn; không tự nối dữ liệu thiếu')
    if np.any(raw != np.floor(raw)) or np.any(raw[:,1:]<0) or np.any(raw[:,1:]>=0x3ffff):
        raise ValueError('Mẫu không nguyên/ngoài dải/bị clip; cần đoạn không clip để đối chiếu')
    if np.any(np.diff(raw[:,0])<=0):
        raise ValueError('Timestamp lặp/lùi; không tự sắp xếp hoặc sửa mẫu')
    started = time.perf_counter()
    run = subprocess.run([str(executable)],input=payload,text=True,capture_output=True,check=True)
    cpp_ms = (time.perf_counter()-started)*1000
    stream = np.genfromtxt(io.StringIO(run.stdout),delimiter=',')
    relative = (stream[:,0]-stream[0,0])/1000
    rows, missing_reference, out_of_range, skipped_discontinuous, stale_samples = [], 0, 0, 0, 0
    names = ALGORITHMS+list(extra_algorithms)
    msptd_times = []
    for end in range(13, math.floor(relative[-1])+1):
        index = int(np.searchsorted(relative,end,side='right')-1)
        expected = reference_constant
        score_this = True
        if numeric is not None:
            # BIDMC payload có thêm1000ms như công cụ baseline; end là thời gian recording.
            if last_time is not None and end > last_time-1:
                score_this = False
            nt = numeric[numeric.dtype.names[0]]
            values = numeric['HR'][(nt >= end-8) & (nt <= end)]
            if len(values)<8 or not np.isfinite(values).all():
                missing_reference += 1
                score_this = False
            elif np.any((values<40)|(values>200)):
                out_of_range += 1
                score_this = False
            else:
                expected = float(np.median(values))
        predictions = dict.fromkeys(names)
        fresh_sample = end-relative[index] <= .040001
        if not fresh_sample:
            stale_samples += 1
        if fresh_sample and stream[index,1] == 1 and stream[index,5] == 1:
            predictions['current_cpp'] = float(stream[index,2])
        # Cùng cần400 mẫu cửa sổ sau100 mẫu warmup. Không đưa đầu đoạn mất mẫu vào LMS.
        history = stream[max(0,index-499):index+1]
        valid_history = (fresh_sample and len(history)==500 and np.all(history[:,5]==1) and
                         np.all(history[:,6]==history[-1,6]) and
                         np.isfinite(history[:,3:5]).all() and
                         np.all(np.diff(history[:,0])<=40))
        if valid_history:
            for column,name in [(3,'msptd_ir_candidate'),(4,'msptd_red_candidate')]:
                then = time.perf_counter()
                predictions[name] = heart_rate(history[-400:,column])[0]
                msptd_times.append((time.perf_counter()-then)*1000)
        else:
            skipped_discontinuous += 1
        diagnostics = None
        if extra_evaluator is not None:
            added,diagnostics = extra_evaluator(history[-400:,3:5] if valid_history else None,
                                               int(stream[index,0]),int(stream[index,6]),predictions['current_cpp'])
            if set(added)!=set(extra_algorithms):
                raise ValueError('Unexpected candidate names')
            predictions.update(added)
        # Luôn cập nhật thuật toán trước khi dùng nhãn tham chiếu để quyết định chấm.
        # Nhãn thiếu không được thay đổi máy trạng thái ứng viên.
        if score_this:
            row = {'end_s':end,'reference_bpm':expected,'predictions':predictions}
            if diagnostics is not None:
                row['quality_diagnostics'] = diagnostics
            rows.append(row)
    return {
        'summary':{name:summarize(rows,name,numeric is not None or reference_constant is not None) for name in names},
        'missing_reference_windows':missing_reference,'outside_reference_range_windows':out_of_range,
        'candidate_no_continuous_history_windows':skipped_discontinuous,
        'no_fresh_sample_windows':stale_samples,
        'laptop_cpp_process_ms':cpp_ms,
        'laptop_numpy_candidate_call_ms':{'median':float(np.median(msptd_times)) if msptd_times else None,
                                          'max':max(msptd_times) if msptd_times else None},
        'rows':rows,
    }


def controls(seeds=(17,37,73,101,211)):
    for bpm in [40,60,80,100,150,180,200]:
        t = np.arange(3000)*.02
        x = 1800*np.sin(2*np.pi*bpm*t/60)
        yield f'SYNTHETIC_clean_{bpm}',t,x
    t = np.arange(3000)*.02
    yield 'SYNTHETIC_flat',t,np.zeros(len(t))
    for kind in ['white','colored']:
        for seed in seeds:
            for amplitude in [10,100,1000]:
                state, drift, x = seed,0,[]
                for _ in t:
                    state = (state*1664525+1013904223)&0xffffffff
                    noise = ((state>>8)/16777216-.5)*amplitude
                    drift = .97*drift+.03*noise
                    x.append(noise if kind=='white' else drift)
                yield f'SYNTHETIC_{kind}_{seed}_{amplitude}',t,np.array(x)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--records',type=int,nargs='*',default=[1,2,3,4,5],choices=range(1,54))
    parser.add_argument('--download',action='store_true')
    parser.add_argument('--trace',type=Path,action='append',help='Mặc định4 file trên máy Trung; truyền file của máy khác')
    parser.add_argument('--skip-controls',action='store_true')
    parser.add_argument('--report',type=Path,default=ROOT/'backend/storage/local/ppg-candidates-step2.json')
    args = parser.parse_args()
    if len(set(args.records))!=len(args.records):
        parser.error('Không tính một recording hai lần')
    compiler = shutil.which(os.environ.get('CXX','g++')) or shutil.which('clang++')
    if not compiler:
        raise RuntimeError('Cần g++/clang++ để chạy đúng bộ C++ sản phẩm')
    report = {
        'role':'offline development comparison, not a firmware deployment or wrist accuracy validation',
        'upstream':{'commit':UPSTREAM_COMMIT,'url':UPSTREAM_URL},
        'preprocessing':'both candidates use production C++ causal HP0.5Hz/LP4Hz at50Hz, initialDC/warmup/contact/gap; not the published full preprocessing pipeline',
        'evaluation':'trailing8s, score every1s from13s; no future samples; MSPTD6s internal windows; candidates have NO signal-quality gate',
        'port_validation':'vectorized NumPy compared with literal loops and clean controls; MATLAB/Octave not available, upstream executable not run',
        'hashes':{name:digest(ROOT/name) for name in [
            'ai/edge_firmware/include/processing/ppg_rate.h',
            'ai/edge_firmware/tests/native/ppg_benchmark_harness.cpp',
            'scripts/ppg_msptd_reference.py','scripts/benchmark_ppg_candidates.py']},
        'software':{'numpy':np.__version__},'records':[],
    }
    with TemporaryDirectory(prefix='asd-ppg-candidates-') as temp:
        executable = Path(temp)/('benchmark.exe' if os.name=='nt' else 'benchmark')
        subprocess.run([compiler,'-std=c++17','-O2','-Wall','-Wextra','-Werror',
                        '-I',str(ROOT/'ai/edge_firmware/include'),
                        str(ROOT/'ai/edge_firmware/tests/native/ppg_benchmark_harness.cpp'),'-o',str(executable)],check=True)
        def add(name,category,payload,**kwargs):
            result = evaluate(executable,payload,**kwargs)
            result.update({'name':name,'category':category,'input_sha256':hashlib.sha256(payload.encode()).hexdigest()})
            report['records'].append(result)
            print(json.dumps({'name':name,'summary':result['summary']}),flush=True)
            return result
        for path in args.trace or [ROOT/'backend/storage/local'/n for n in DEFAULT_TRACES]:
            wire = path.read_text(encoding='utf-8-sig').splitlines()
            add(path.name,'DEVICE_no_reference','\n'.join(wire[1:])+'\n')['raw_file_sha256'] = digest(path)
        source = ROOT/'backend/storage/local/bidmc-1.0.0'
        if args.records:
            license_file = required_file(source,'LICENSE',args.download)
            manifest = required_file(source,'SHA256SUMS.txt',args.download)
            checks = {p[1].lstrip('*'):p[0] for line in manifest.read_text().splitlines() if len(p:=line.split(maxsplit=1))==2}
            if digest(license_file)!=checks.get('LICENSE'):
                raise ValueError('License hash mismatch')
        for index in args.records:
            files,hashes = [],{}
            for kind in ['Signals','Numerics']:
                name = f'bidmc_csv/bidmc_{index:02d}_{kind}.csv'
                path = required_file(source,name,args.download)
                if digest(path)!=checks.get(name):
                    raise ValueError(f'Official checksum mismatch: {name}')
                files.append(path);hashes[kind] = digest(path)
            payload,last = prepare_signal(files[0])
            numeric = np.genfromtxt(files[1],delimiter=',',names=True,autostrip=True)
            row = add(f'BIDMC_{index:02d}','BIDMC_ECG_HR',payload,numeric=numeric,last_time=last)
            row['source_hashes'] = hashes
            row['previously_used_for_tuning_current'] = index in [1,2,3,4,5]
        if not args.skip_controls:
            for name,t,x in controls():
                payload = ''.join(f'{1000+round(s*1000)},{int(80000+v*.8)},{int(100000+v)}\n' for s,v in zip(t,x))
                known = int(name.rsplit('_',1)[-1]) if name.startswith('SYNTHETIC_clean_') else None
                row = add(name,'SYNTHETIC_known_control',payload,reference_constant=known)
                row['expected_no_pulse'] = name.startswith(('SYNTHETIC_white','SYNTHETIC_colored','SYNTHETIC_flat'))
    args.report.parent.mkdir(parents=True,exist_ok=True)
    args.report.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Report:',args.report)


if __name__=='__main__':
    main()
