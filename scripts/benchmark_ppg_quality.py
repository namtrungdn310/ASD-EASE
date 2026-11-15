"""Chạy hai policy bước3 đã chốt, chỉ offline. Không chỉnh firmware hoặc dùng nhãn HR để lọc."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory

import numpy as np

from benchmark_ppg_candidates import ROOT, DEFAULT_TRACES, controls, digest, evaluate
from benchmark_ppg_reference import required_file, prepare_signal
from ppg_quality_candidate import Evaluator, EXTRA_ALGORITHMS, POLICIES, specifications


def aggregate(records,name):
    rows = [x for r in records for x in r['rows']]
    accepted = [r for r in rows if r['predictions'][name] is not None]
    errors = [abs(r['predictions'][name]-r['reference_bpm']) for r in accepted if r['reference_bpm'] is not None]
    added = [r for r in accepted if r['predictions']['current_cpp'] is None]
    added_errors = [abs(r['predictions'][name]-r['reference_bpm']) for r in added if r['reference_bpm'] is not None]
    return {'eligible':len(rows),'accepted':len(accepted),
            'availability_pct':100*len(accepted)/len(rows) if rows else None,
            'mae':float(np.mean(errors)) if errors else None,
            'p95':float(np.percentile(errors,95)) if errors else None,
            'over10':sum(e>10 for e in errors),'added_windows':len(added),
            'added_mae':float(np.mean(added_errors)) if added_errors else None,
            'added_over10':sum(e>10 for e in added_errors)}


def decision(records):
    public = [r for r in records if r['category']=='BIDMC_ECG_HR']
    noise = [r for r in records if r.get('expected_no_pulse')]
    base = aggregate(public,'current_cpp')
    result = {'baseline':base,'candidates':{}}
    for policy in POLICIES:
        name = f'hybrid_{policy.name}'
        ref = aggregate(public,name)
        bad = aggregate(noise,name)
        checks = {'no_noise_acceptance':bad['accepted']==0,
                  'no_additional_over10':ref['over10']<=base['over10'],
                  'mae_within_budget':ref['mae'] is not None and ref['mae']<=base['mae']+.2,
                  'p95_within_budget':ref['p95'] is not None and ref['p95']<=base['p95']+.5,
                  'gains_reference_windows':ref['added_windows']>0}
        result['candidates'][policy.name] = {'reference':ref,'noise':bad,'checks':checks,'passes':all(checks.values())}
    eligible = [(name,r) for name,r in result['candidates'].items() if r['passes']]
    # Chốt trước xem dữ liệu: ưu tiên MAE phần nhận thêm, rồi coverage.
    result['selected_policy'] = min(eligible,key=lambda p:(p[1]['reference']['added_mae'],-p[1]['reference']['added_windows'],p[0]))[0] if eligible else None
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--phase',choices=['development','validation'],default='development')
    parser.add_argument('--download',action='store_true')
    parser.add_argument('--development-report',type=Path,default=ROOT/'backend/storage/local/ppg-quality-development.json')
    args = parser.parse_args()
    policy = specifications()
    encoded = json.dumps(policy,sort_keys=True).encode()
    policy_hash = hashlib.sha256(encoded).hexdigest()
    files = ['scripts/ppg_quality_candidate.py','scripts/ppg_msptd_reference.py',
             'scripts/benchmark_ppg_quality.py','scripts/benchmark_ppg_candidates.py',
             'ai/edge_firmware/include/processing/ppg_rate.h',
             'ai/edge_firmware/tests/native/ppg_benchmark_harness.cpp']
    hashes = {p:digest(ROOT/p) for p in files}
    chosen = None
    if args.phase=='validation':
        dev = json.loads(args.development_report.read_text(encoding='utf-8'))
        if dev['policy_sha256']!=policy_hash or dev['source_hashes']!=hashes:
            raise ValueError('Policy hoặc source đã đổi sau phát triển; không dùng như vòng kiểm cấu hình đã chốt')
        chosen = dev['decision']['selected_policy']
        if chosen is None:
            raise ValueError('Không có ứng viên đạt vòng phát triển; không mở vòng validation để chọn lại theo điểm')
    report = {'phase':args.phase,'policy':policy,'policy_sha256':policy_hash,'source_hashes':hashes,
              'reference':'median ECG monitor HR in trailing8s; no beat-level truth; no wrist HR reference',
              'selected_before_validation':chosen,'records':[]}
    compiler = shutil.which(os.environ.get('CXX','g++')) or shutil.which('clang++')
    if not compiler:
        raise RuntimeError('Need g++/clang++')
    with TemporaryDirectory(prefix='asd-quality-') as temp:
        executable = Path(temp)/('quality.exe' if os.name=='nt' else 'quality')
        subprocess.run([compiler,'-std=c++17','-O2','-Wall','-Wextra','-Werror','-I',str(ROOT/'ai/edge_firmware/include'),
                        str(ROOT/'ai/edge_firmware/tests/native/ppg_benchmark_harness.cpp'),'-o',str(executable)],check=True)
        def add(name,category,payload,**kwargs):
            result = evaluate(executable,payload,extra_algorithms=EXTRA_ALGORITHMS,extra_evaluator=Evaluator(),**kwargs)
            result.update({'name':name,'category':category,'input_sha256':hashlib.sha256(payload.encode()).hexdigest()})
            report['records'].append(result)
            print(json.dumps({'name':name,'summary':result['summary']}),flush=True)
            return result
        if args.phase=='development':
            for n in DEFAULT_TRACES:
                p = ROOT/'backend/storage/local'/n
                add(n,'DEVICE_no_reference','\n'.join(p.read_text(encoding='utf-8-sig').splitlines()[1:])+'\n')
        source = ROOT/'backend/storage/local/bidmc-1.0.0'
        license_file = required_file(source,'LICENSE',args.download)
        manifest = required_file(source,'SHA256SUMS.txt',args.download)
        checks = {p[1].lstrip('*'):p[0] for line in manifest.read_text().splitlines() if len(p:=line.split(maxsplit=1))==2}
        if digest(license_file)!=checks.get('LICENSE'):
            raise ValueError('License hash mismatch')
        for index in (range(1,11) if args.phase=='development' else range(11,16)):
            paths,source_hashes = [],{}
            for kind in ['Signals','Numerics']:
                name = f'bidmc_csv/bidmc_{index:02d}_{kind}.csv'
                path = required_file(source,name,args.download)
                if digest(path)!=checks.get(name):
                    raise ValueError(f'Checksum mismatch: {name}')
                paths.append(path);source_hashes[kind] = digest(path)
            payload,last = prepare_signal(paths[0])
            row = add(f'BIDMC_{index:02d}','BIDMC_ECG_HR',payload,
                      numeric=np.genfromtxt(paths[1],delimiter=',',names=True,autostrip=True),last_time=last)
            row['source_hashes'] = source_hashes
        seeds = (17,37,73,101,211) if args.phase=='development' else (907,911,919,929,937)
        for name,t,x in controls(seeds=seeds):
            payload = ''.join(f'{1000+round(s*1000)},{int(80000+v*.8)},{int(100000+v)}\n' for s,v in zip(t,x))
            known = int(name.rsplit('_',1)[-1]) if name.startswith('SYNTHETIC_clean_') else None
            row = add(name,'SYNTHETIC_known_control',payload,reference_constant=known)
            row['expected_no_pulse'] = name.startswith(('SYNTHETIC_white','SYNTHETIC_colored','SYNTHETIC_flat'))
    report['decision'] = decision(report['records'])
    if args.phase=='validation':
        # Không chọn cấu hình khác nếu cấu hình đã chốt thất bại.
        checks = report['decision']['candidates'][chosen]['checks']
        report['locked_candidate_passes_validation'] = all(checks.values())
        report['decision']['selected_policy'] = chosen
    path = ROOT/f'backend/storage/local/ppg-quality-{args.phase}.json'
    path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report['decision']),flush=True)
    print('Report:',path)


if __name__=='__main__':
    main()
