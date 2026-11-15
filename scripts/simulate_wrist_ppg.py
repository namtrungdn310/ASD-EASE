"""Mô phỏng cổ tay qua driver/quality C++ thực; không thay dữ liệu ESP hoặc nhịp tham chiếu."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory

import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def scenarios(seed=601,chip_hz=200):
    """Mô hình hiện tượng: hệ số ghép quang không phải khoảng cách mm đã đo."""
    rng = np.random.default_rng(seed)
    if chip_hz not in [200,400]:raise ValueError('Unsupported acquisition profile')
    averaging=chip_hz//50
    t = np.arange(chip_hz*60)/chip_hz  # 60s, đầu ra vẫn50Hz.
    for name, coupling, bpm, noise, movement, leakage, dropout, clip in [
        ('steady', 1., 80., 8., 0., 0., False, False),
        ('loose', .25, 80., 8., 0., 0., False, False),
        ('very_weak', .02, 80., 20., 0., 0., False, False),
        ('weak_pulse_high_dc', .02, 80., 20., 0., 0., False, False),
        ('no_contact', 0., None, 8., 0., 0., False, False),
        ('light_leak', .25, 80., 15., 0., 15000., False, False),
        ('sliding_contact', .25, 80., 12., 1200., 0., True, False),
        ('motion_no_pulse', .25, None, 12., 1200., 0., False, False),
        ('periodic_interference_no_pulse', .25, None, 8., 0., 0., False, False),
        ('adc_clip', 1., 80., 8., 0., 0., False, True),
    ]:
        phase = 2*np.pi*(bpm or 80)*t/60
        pulse = (np.sin(phase)+.18*np.sin(2*phase))*(900*coupling if bpm else 0)
        # Nhiễu chuyển động không đồng nhất với nhịp đập.
        artifact = movement*(np.sin(2*np.pi*.7*t)+.35*np.sin(2*np.pi*1.13*t*t/60))
        if name == 'periodic_interference_no_pulse':
            artifact = 700*np.sin(2*np.pi*80*t/60)
        ambient = leakage*(.5+.3*np.sin(2*np.pi*.12*t))
        dc = 800+99000*coupling
        if name=='weak_pulse_high_dc': dc=90000
        ir = dc+pulse+artifact+ambient+rng.normal(0, noise, len(t))
        red = 700+80000*coupling+.7*pulse+.8*artifact+ambient*.9+rng.normal(0, noise, len(t))
        if name=='weak_pulse_high_dc': red+=70000
        if dropout:
            ir[(t>=22)&(t<25)] = 800
            red[(t>=22)&(t<25)] = 700
        if clip:
            ir += 300000
            red += 300000
        # Không giả ánh sáng ngoài là tăng dòng LED; ALC flag là fixture riêng.
        alc = (name == 'light_leak') & ((t>=20)&(t<23))
        if np.isscalar(alc): alc = np.full(len(t), alc)
        ir = np.clip(np.rint(ir.reshape(-1,averaging).mean(axis=1)),0,0x3ffff).astype(int)
        red = np.clip(np.rint(red.reshape(-1,averaging).mean(axis=1)),0,0x3ffff).astype(int)
        flags = np.asarray(alc).reshape(-1,averaging).any(axis=1)
        times = 2000+np.arange(len(ir))*20
        motion_scores=np.full(len(ir),.4 if movement else 0.)
        yield name,bpm,times,red,ir,flags,motion_scores


def run(seed, report, dense=False):
    fw = ROOT/'ai/edge_firmware'
    compiler = shutil.which(os.environ.get('CXX','g++')) or shutil.which('clang++')
    if not compiler: raise RuntimeError('Need g++/clang++')
    # Kiểm mô hình: thêm mẫu trung bình giảm nhiễu trắng không tương quan.
    # Không giả cùng mức giảm cho chuyển động/ánh sáng hoặc PPG trên người.
    noise=np.random.default_rng(seed).normal(size=8000)
    variance_ratio=float(np.var(noise.reshape(-1,8).mean(axis=1))/
                         np.var(noise[::2].reshape(-1,4).mean(axis=1)))
    assert .4<variance_ratio<.65, variance_ratio
    rows = []
    with TemporaryDirectory(prefix='asd-wrist-sim-') as temp:
        exe = Path(temp)/('wrist.exe' if os.name=='nt' else 'wrist')
        subprocess.run([compiler,'-std=c++17','-O2','-Wall','-Wextra','-Werror',
                        '-DASD_PPG_NATIVE_HYBRID_TEST=1','-DASD_PPG_TRACKER_ENABLED=0',
                        '-I',str(fw/'tests/native/stubs'),
                        '-I',str(fw/'include'),str(fw/'tests/native/ppg_wrist_harness.cpp'),
                        str(fw/'src/sensors/MAX30102Sensor.cpp'),'-o',str(exe)],check=True)
        for name,bpm,t,red,ir,flags,motion in scenarios(seed,400 if dense else 200):
            wire=''.join(f'{at} {r} {i} {int(a)} {m}\n' for at,r,i,a,m in zip(t,red,ir,flags,motion))
            output=subprocess.run([str(exe)],input=wire,text=True,capture_output=True,check=True)
            import io
            samples=np.genfromtxt(io.StringIO(output.stdout),delimiter=',')
            samples=samples[samples[:,0]>=t[0]+13000]
            accepted=samples[samples[:,1]==1]
            errors=np.abs(accepted[:,2]-bpm) if bpm is not None else np.array([])
            row={'scenario':name,'data_origin':'SYNTHETIC','reference_bpm':bpm,
                 'samples_scored':len(samples),'accepted':len(accepted),
                 'availability_pct':100*len(accepted)/len(samples),
                 'mae_bpm':float(errors.mean()) if len(errors) else None,
                 'false_hr_samples':len(accepted) if bpm is None else None,
                 'source_counts':{str(i):int(np.sum(accepted[:,3]==i)) for i in [1,2,3,4]}}
            row['status']='KNOWN_LIMITATION_FALSE_POSITIVE' if bpm is None and len(accepted) else 'REPORTED'
            # Chỉ assert những điều fixture thực sự chứng minh, không giấu ca giới hạn.
            assert np.all(accepted[:,0]>=accepted[:,4])
            assert np.all(accepted[:,0]-accepted[:,4]<=3000)
            if name in ['steady','loose']:
                assert row['availability_pct']>80 and row['mae_bpm']<4, row
            if name in ['no_contact','adc_clip','motion_no_pulse','sliding_contact']:
                assert not len(accepted), row
            if name=='light_leak':
                assert not np.any((accepted[:,0]>=t[0]+20000)&(accepted[:,0]<t[0]+23000)), row
            rows.append(row)
            print(json.dumps(row),flush=True)
    result={'role':'SYNTHETIC engineering fixtures, not optical calibration or wrist accuracy',
            'seed':seed,'chip_hz':400 if dense else 200,'averaging':8 if dense else 4,'fifo_hz':50,'driver_chip_hz':200,'driver_averaging':4,
            'worker_delay_model_ms':150,'fixed_policy':'hybrid_strict, unchanged',
            'white_noise_variance_ratio_model_8_vs_4':variance_ratio,
            'limitations':['Coupling is not measured air gap or contact pressure.',
                           'Synchronous host computation is not ESP timing.',
                           'Periodic interference can resemble pulse in PPG alone; report false HR honestly.',
                           'Fixtures do not select an optimal LED current or prove clinical accuracy.'],
            'rows':rows,
            'source_sha256':{name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in [
                'scripts/simulate_wrist_ppg.py',
                'ai/edge_firmware/tests/native/ppg_wrist_harness.cpp',
                'ai/edge_firmware/src/sensors/MAX30102Sensor.cpp',
                'ai/edge_firmware/include/processing/ppg_init.h',
                'ai/edge_firmware/include/processing/ppg_wrist_motion.h',
                'ai/edge_firmware/include/processing/ppg_rate.h',
                'ai/edge_firmware/include/processing/ppg_quality.h',
                'ai/edge_firmware/include/processing/sensor_math.h',
                'ai/edge_firmware/include/board_config.h']}}
    report.parent.mkdir(parents=True,exist_ok=True)
    report.write_text(json.dumps(result,indent=2),encoding='utf-8')
    limitations=sum(r['status']=='KNOWN_LIMITATION_FALSE_POSITIVE' for r in rows)
    print(f'Completed 10 scenarios; engineering assertions passed; {limitations} unresolved false-positive scenario(s)')
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seed',type=int,default=601)
    parser.add_argument('--dense',action='store_true',help='Chỉ mô phỏng đầu vào400Hz/avg8; cấu hình driver vẫn200Hz/avg4')
    parser.add_argument('--report',type=Path,default=ROOT/'backend/storage/local/ppg-wrist-simulation.json')
    args=parser.parse_args()
    run(args.seed,args.report,args.dense)
