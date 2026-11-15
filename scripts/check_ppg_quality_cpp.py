"""Đối chiếu port C++ với policy Python đã khóa; không nạp ESP."""
import argparse
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory

import numpy as np

from benchmark_ppg_candidates import ROOT, controls
from benchmark_ppg_reference import prepare_signal
from ppg_quality_candidate import Evaluator

REASONS={'LOW_AMPLITUDE':2,'INSUFFICIENT_BEATS':3,'RR_RANGE':4,
         'RECENT_DISAGREEMENT':5,'STALE_PEAK':6,'FLAT_BEAT':7,'INVALID_WINDOW':1}
FIELDS={'bpm':3,'recent_bpm':4,'amplitude':5,'rr_cv':6,'template_median':7,
        'template_p20':8,'spectral_fraction':9,'peak_age_s':10,'peak_count':11}


def verify(executable,cases):
    wire=''.join(f'{t} {generation} '+' '.join(format(float(x),'.9g') for x in w.T.ravel())+'\n'
                 for t,generation,w,_ in cases)
    result=subprocess.run([str(executable)],input=wire,text=True,capture_output=True,check=True)
    lines=result.stdout.splitlines()
    if len(lines)!=len(cases):
        raise AssertionError('C++ output count mismatch')
    for index,(line,case) in enumerate(zip(lines,cases)):
        t,generation,window,expected=case
        row=np.array(line.split(),dtype=float)
        policy=expected['policies']['strict']
        if bool(row[1])!=policy['qualified'] or bool(row[2])!=policy['confirmed']:
            raise AssertionError(f'Window{index} t={t}: decision C++={row[:5]} Python={policy} features={expected["channels"]}')
        for channel,start in enumerate([5,17]):
            if not expected['channels']:
                continue
            f=expected['channels'][channel];actual=row[start:start+12]
            if bool(actual[0])!=f['usable'] or int(actual[1])!=REASONS.get(f.get('reason'),0):
                raise AssertionError(f'Window{index} channel{channel}: reason C++={actual} Python={f}')
            for name,column in FIELDS.items():
                if name in f and f[name] is not None and not np.isclose(actual[column],f[name],rtol=2e-5,atol=2e-5):
                    raise AssertionError(f'Window{index} channel{channel} {name}: C++={actual[column]} Python={f[name]}')
        if policy['qualified']:
            source=3 if policy['source']=='IR' else 4
            if int(row[4])!=source:
                raise AssertionError('Source selection mismatch')
    return len(cases)


def synthetic():
    evaluator=Evaluator();cases=[];now=10000;generation=1
    rng=np.random.default_rng(1212)
    for bpm in [40,60,80,100,150,180,200]:
        for phase in [0,.4,1.2]:
            base=np.sin(np.arange(400)*2*np.pi*bpm/3000+phase)*1800
            window=np.column_stack((base,base*.7)).astype(np.float32)
            for _ in range(3):
                now+=1000
                _,diag=evaluator(window,now,generation,None);cases.append((now,generation,window,diag))
        generation+=1
    for kind in ['flat','noise','drift','conflict']:
        for _ in range(8):
            now+=1000
            if kind=='flat':window=np.zeros((400,2),dtype=np.float32)
            elif kind=='noise':window=rng.normal(0,100,(400,2)).astype(np.float32)
            elif kind=='drift':window=np.column_stack((np.arange(400)*2,np.arange(400))).astype(np.float32)
            else:window=np.column_stack((np.sin(np.arange(400)*2*np.pi*80/3000)*1800,np.sin(np.arange(400)*2*np.pi*130/3000)*1800)).astype(np.float32)
            _,diag=evaluator(window,now,generation,None);cases.append((now,generation,window,diag))
        generation+=1
    return cases


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reports',type=Path,nargs='*',default=[])
    args=parser.parse_args()
    compiler=shutil.which(os.environ.get('CXX','g++')) or shutil.which('clang++')
    if not compiler:raise RuntimeError('Need g++/clang++')
    firmware=ROOT/'ai/edge_firmware'
    total=0;records=[]
    with TemporaryDirectory(prefix='asd-quality-cpp-') as temp:
        temp=Path(temp)
        quality=temp/('quality.exe' if os.name=='nt' else 'quality')
        baseline=temp/('baseline.exe' if os.name=='nt' else 'baseline')
        for source,target in [('ppg_quality_harness.cpp',quality),('ppg_benchmark_harness.cpp',baseline)]:
            subprocess.run([compiler,'-std=c++17','-O2','-Wall','-Wextra','-Werror','-I',str(firmware/'include'),
                            str(firmware/'tests/native'/source),'-o',str(target)],check=True)
        count=verify(quality,synthetic());total+=count;print('PASS synthetic C++/Python parity:',count,flush=True)
        for path in args.reports:
            report=json.loads(path.read_text(encoding='utf-8'))
            phase=report['phase']
            generated={}
            for name,t,x in controls(seeds=(17,37,73,101,211) if phase=='development' else (907,911,919,929,937)):
                generated[name]=''.join(f'{1000+round(s*1000)},{int(80000+v*.8)},{int(100000+v)}\n' for s,v in zip(t,x))
            for record in report['records']:
                name=record['name']
                if record['category']=='DEVICE_no_reference':
                    wire=(ROOT/'backend/storage/local'/name).read_text(encoding='utf-8-sig').splitlines();payload='\n'.join(wire[1:])+'\n'
                elif record['category']=='BIDMC_ECG_HR':
                    payload,_=prepare_signal(ROOT/f'backend/storage/local/bidmc-1.0.0/bidmc_csv/bidmc_{int(name[-2:]):02d}_Signals.csv')
                else:payload=generated[name]
                run=subprocess.run([str(baseline)],input=payload,text=True,capture_output=True,check=True)
                stream=np.genfromtxt(io.StringIO(run.stdout),delimiter=',');relative=(stream[:,0]-stream[0,0])/1000
                cases=[]
                for expected in record['rows']:
                    index=int(np.searchsorted(relative,expected['end_s'],side='right')-1)
                    history=stream[max(0,index-499):index+1]
                    valid=(expected['end_s']-relative[index]<=.040001 and len(history)==500 and np.all(history[:,5]==1)
                           and np.all(history[:,6]==history[-1,6]) and np.isfinite(history[:,3:5]).all() and np.all(np.diff(history[:,0])<=40))
                    window=history[-400:,3:5].astype(np.float32) if valid else np.zeros((400,2),dtype=np.float32)
                    cases.append((int(stream[index,0]),int(stream[index,6]),window,expected['quality_diagnostics']))
                n=verify(quality,cases);total+=n;records.append({'phase':phase,'name':name,'windows':n})
                print('PASS',phase,name,n,flush=True)
    print('PASS total C++/Python quality decision windows:',total)
    if args.reports:
        path=ROOT/'backend/storage/local/ppg-quality-cpp-parity.json'
        path.write_text(json.dumps({'total_windows':total,'records':records},indent=2),encoding='utf-8')


if __name__=='__main__':main()
