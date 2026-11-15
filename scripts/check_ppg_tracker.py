"""Chấm tracker C++ thật: raw/replay/mô phỏng/tham chiếu; không mở COM hoặc MQTT."""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory

import numpy as np

from benchmark_ppg_candidates import controls
from benchmark_ppg_weak import simulations, payload
from benchmark_ppg_reference import prepare_signal, required_file

ROOT=Path(__file__).resolve().parents[1]
LOCAL=ROOT/'backend/storage/local'


def longest_missing(values):
    longest=current=0
    for valid in values:
        current=0 if valid else current+1
        longest=max(longest,current)
    return longest


def build_native(executable,compiler):
    subprocess.run([compiler,'-std=c++17','-O2','-Wall','-Wextra','-Werror',
                    '-I',str(ROOT/'ai/edge_firmware/include'),
                    str(ROOT/'ai/edge_firmware/tests/native/ppg_tracker_test.cpp'),'-o',str(executable)],check=True)
    subprocess.run([str(executable)],check=True)
    range_executable=executable.with_name('tracking-range'+executable.suffix)
    subprocess.run([compiler,'-std=c++17','-O2','-Wall','-Wextra','-Werror',
                    '-I',str(ROOT/'ai/edge_firmware/include'),
                    str(ROOT/'ai/edge_firmware/tests/native/ppg_tracking_range_test.cpp'),
                    '-o',str(range_executable)],check=True)
    subprocess.run([str(range_executable)],check=True)
    shape_executable=executable.with_name('cycle-shape'+executable.suffix)
    subprocess.run([compiler,'-std=c++17','-O2','-Wall','-Wextra','-Werror',
                    '-I',str(ROOT/'ai/edge_firmware/include'),
                    str(ROOT/'ai/edge_firmware/tests/native/ppg_cycle_shape_test.cpp'),
                    '-o',str(shape_executable)],check=True)
    subprocess.run([str(shape_executable)],check=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--phase',choices=('development','validation'),default='development')
    parser.add_argument('--traces',action='store_true')
    parser.add_argument('--trace',type=Path,action='append',default=[],help='Raw CSV bổ sung, không tự gán HR tham chiếu')
    parser.add_argument('--report',type=Path)
    parser.add_argument('--development-report',type=Path,default=LOCAL/'ppg-tracker-development.json')
    parser.add_argument('--download',action='store_true')
    parser.add_argument('--unit-only',action='store_true',help='Chỉ kiểm core C++, không cần dataset hoặc mạng')
    args=parser.parse_args()
    compiler=shutil.which(os.environ.get('CXX','g++')) or shutil.which('clang++')
    if not compiler: raise RuntimeError('Need g++/clang++')
    if args.unit_only:
        with TemporaryDirectory(prefix='asd-tracker-core-') as temp:
            build_native(Path(temp)/('tracker.exe' if os.name=='nt' else 'tracker'),compiler)
        return
    target=args.report or LOCAL/f'ppg-tracker-{args.phase}.json'
    if target.exists(): raise FileExistsError(target)
    sources=['ai/edge_firmware/include/processing/ppg_cycle_tracker.h',
             'ai/edge_firmware/include/processing/ppg_cycle_shape.h',
             'ai/edge_firmware/include/processing/ppg_rate.h','ai/edge_firmware/include/processing/ppg_contact.h',
             'ai/edge_firmware/tests/native/ppg_tracker_test.cpp','scripts/check_ppg_tracker.py',
             'ai/edge_firmware/tests/native/ppg_tracking_range_test.cpp',
             'ai/edge_firmware/tests/native/ppg_cycle_shape_test.cpp',
             'scripts/benchmark_ppg_candidates.py','scripts/benchmark_ppg_reference.py','scripts/benchmark_ppg_weak.py']
    hashes={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in sources}
    if args.phase=='validation':
        previous=json.loads(args.development_report.read_text(encoding='utf-8'))
        if previous['source_hashes']!=hashes or not previous.get('complete'):
            raise ValueError('Source khác vòng phát triển hoặc vòng trước chưa hoàn tất')
    report={'phase':args.phase,'role':'engineering tracking experiment, no wrist reference or clinical accuracy claim',
            'source_hashes':hashes,'records':[],'complete':False,
            'motion_guard_in_replay':False,'overlapping_windows_independent':False,
            'reference_definition':'BIDMC median ECG-monitor HR in trailing8s; no beat-by-beat labels',
            'public_reference_records_seen_before':args.phase=='development',
            'note':'Canonical clean controls are reused; validation changes simulation seeds and public records.'}
    target.parent.mkdir(parents=True,exist_ok=True)
    with target.with_suffix('.lock.json').open('x',encoding='utf-8') as f: json.dump(report,f,indent=2)
    with TemporaryDirectory(prefix='asd-tracker-') as temp:
        exe=Path(temp)/('tracker.exe' if os.name=='nt' else 'tracker')
        build_native(exe,compiler)

        def add(name,category,text,reference=None,numeric=None,last=None,no_pulse=False,periodic=False):
            run=subprocess.run([str(exe),'replay'],input=text,text=True,capture_output=True,check=True)
            data=np.atleast_2d(np.genfromtxt(io.StringIO(run.stdout),delimiter=','))
            row={'name':name,'category':category,'input_sha256':hashlib.sha256(text.encode()).hexdigest(),
                 'expected_no_pulse':no_pulse,'periodic_interference':periodic,'profiles':{}}
            for profile,valid_column,bpm_column in (('standard',5,6),('tracker',1,2)):
                values=[];errors=[]
                for v in data:
                    expected=reference;end=(v[0]-1000)/1000
                    if numeric is not None:
                        if end<13 or end>last-1: continue
                        nt=numeric[numeric.dtype.names[0]]
                        hr=numeric['HR'][(nt>=end-8)&(nt<=end)]
                        if len(hr)<8 or not np.isfinite(hr).all() or np.any((hr<40)|(hr>200)): continue
                        expected=float(np.median(hr))
                    valid=bool(v[valid_column]);bpm=float(v[bpm_column]) if valid else None
                    if valid and expected is not None:
                        error=abs(bpm-expected);errors.append(error)
                    values.append({'timestamp_ms':int(v[0]),'valid':valid,'bpm':bpm,'reference_bpm':expected,
                                   'mass_score':float(v[3]),'evidence':float(v[4]),
                                   'raw_candidate_bpm':float(v[7]) if profile=='tracker' and valid else None})
                accepted=[v['bpm'] for v in values if v['valid']]
                row['profiles'][profile]={'evaluations':len(values),'accepted':len(accepted),
                    'availability_pct':100*len(accepted)/len(values) if values else None,
                    'mae_bpm':float(np.mean(errors)) if errors else None,
                    'p95_error_bpm':float(np.percentile(errors,95)) if errors else None,
                    'over10_bpm':sum(e>10 for e in errors),
                    'longest_missing_evaluations':longest_missing(v['valid'] for v in values),
                    'range_bpm':[min(accepted),max(accepted)] if accepted else None,'rows':values}
            report['records'].append(row)
            tmp=target.with_suffix('.tmp')
            tmp.write_text(json.dumps(report,indent=2,allow_nan=False),encoding='utf-8');tmp.replace(target)
            print(json.dumps({'name':name,'accepted':{p:r['accepted'] for p,r in row['profiles'].items()}}),flush=True)

        paths=[]
        if args.traces:
            manifest=json.loads((LOCAL/'hr-optical-manifest-20261107.json').read_text(encoding='utf-8'))
            paths=[ROOT/t['raw_csv'] for t in manifest['traces'] if t['included_in_four_complete_trials']]
            paths += [LOCAL/'ppg-20261107-161019-282878.csv',LOCAL/'ppg-20261107-161819-856c88.csv']
            paths += [LOCAL/name for name in ('ppg-20261107-170056-d8f67d.csv',
                                             'ppg-20261107-170616-259f68.csv') if (LOCAL/name).exists()]
        for path in dict.fromkeys(paths+args.trace):
            add(path.name,'DEVICE_no_reference','\n'.join(path.read_text(encoding='utf-8-sig').splitlines()[1:])+'\n')
        for name,t,x in controls(seeds=(17,37) if args.phase=='development' else (11801,11813)):
            ref=float(name.rsplit('_',1)[-1]) if name.startswith('SYNTHETIC_clean_') else None
            add(name,'SYNTHETIC_clean' if ref is not None else 'SYNTHETIC_noise',
                payload(t,80000+.8*x,100000+x),reference=ref,no_pulse=ref is None)
        for seed in ((3411,) if args.phase=='development' else (11717,11731)):
            for name,t,red,ir,known,no_pulse,periodic in simulations(seed):
                add(f'{name}_seed{seed}','SYNTHETIC_pulse' if known is not None else 'SYNTHETIC_noise',
                    payload(t,red,ir),reference=known,no_pulse=no_pulse,periodic=periodic)
        source=LOCAL/'bidmc-1.0.0'
        checks={p[1].lstrip('*'):p[0] for line in required_file(source,'SHA256SUMS.txt',args.download).read_text().splitlines()
                if len(p:=line.split(maxsplit=1))==2}
        for index in (range(1,6) if args.phase=='development' else range(16,21)):
            paths=[required_file(source,f'bidmc_csv/bidmc_{index:02d}_{kind}.csv',args.download) for kind in ('Signals','Numerics')]
            for p in paths:
                if hashlib.sha256(p.read_bytes()).hexdigest()!=checks.get('bidmc_csv/'+p.name): raise ValueError('Checksum mismatch')
            text,end=prepare_signal(paths[0])
            add(f'BIDMC_{index:02d}','BIDMC_ECG_monitor',text,numeric=np.genfromtxt(paths[1],delimiter=',',names=True,autostrip=True),last=end)
        report['complete']=True
    if hashes!={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in sources}: raise RuntimeError('Source changed during benchmark')
    target.write_text(json.dumps(report,indent=2,allow_nan=False),encoding='utf-8')
    print('Complete:',target,flush=True)


if __name__=='__main__': main()
