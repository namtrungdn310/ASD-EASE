"""So ứng viên HR yếu trên raw cổ tay, BIDMC đã xem và mô phỏng có nhãn.

Chỉ offline, không mở COM, không đổi firmware/MQTT. Khóa source trước chạy;
validation chỉ dùng seed mới của mô phỏng, không gọi BIDMC cũ là test mới.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory

import numpy as np

from benchmark_ppg_candidates import ROOT, controls, digest, evaluate
from benchmark_ppg_quality import aggregate
from benchmark_ppg_reference import prepare_signal, required_file
from ppg_weak_candidate import ALGORITHMS, Evaluator, specifications


def simulations(seed):
    """Mô hình hiện tượng, không mô phỏng quang học đã hiệu chuẩn tại cổ tay."""
    t = np.arange(3000)/50
    rng = np.random.default_rng(seed)
    for bpm in (48, 72, 105, 165):
        phase = 2*np.pi*bpm*t/60
        for amplitude in (6, 20, 60):
            for kind in ('weak_white', 'drift_spikes', 'amplitude_modulation', 'strong_harmonic'):
                pulse = amplitude*(np.sin(phase)+.25*np.sin(2*phase+.3))
                if kind == 'strong_harmonic':
                    pulse = amplitude*(np.sin(phase)+1.3*np.sin(2*phase+.3))
                if kind == 'amplitude_modulation':
                    pulse *= .6+.4*np.sin(2*np.pi*.10*t)
                drift = 300*np.sin(2*np.pi*.12*t) if kind == 'drift_spikes' else 0.
                spikes = np.zeros(len(t))
                if kind == 'drift_spikes':
                    at = rng.choice(np.arange(100, len(t)-100), 10, replace=False)
                    spikes[at] = rng.choice((-500., 500.), len(at))
                ir = 170000+pulse+drift+spikes+rng.normal(0, 12, len(t))
                red = 100000+.7*pulse+.9*drift+.8*spikes+rng.normal(0, 12, len(t))
                yield f'{kind}_{bpm}_{amplitude}', t, red, ir, bpm, False, False
    # Nền quang cao không được tự coi là có mạch.
    for kind in ('white', 'colored', 'spikes', 'periodic_optical_interference'):
        ir = rng.normal(0, 30, len(t))
        red = rng.normal(0, 30, len(t))
        if kind == 'colored':
            for signal in (ir, red):
                for i in range(1, len(signal)):
                    signal[i] += .97*signal[i-1]
        elif kind == 'spikes':
            at = rng.choice(np.arange(100, len(t)-100), 40, replace=False)
            ir[at] += rng.choice((-800., 800.), len(at))
            red[at] += ir[at]*.8
        elif kind == 'periodic_optical_interference':
            artifact = 200*np.sin(2*np.pi*1.3*t)
            ir += artifact
            red += artifact*.8
        yield kind, t, 100000+red, 170000+ir, None, kind != 'periodic_optical_interference', kind == 'periodic_optical_interference'


def payload(t, red, ir):
    return ''.join(f'{1000+round(at*1000)},{round(r)},{round(i)}\n' for at, r, i in zip(t, red, ir))


def save_report(target, report):
    # Đọc checkpoint lúc chạy không gặp file bị truncate/nửa JSON.
    temporary = target.with_suffix(target.suffix+'.tmp')
    temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
    temporary.replace(target)


def choose(records):
    public = [r for r in records if r['category'] == 'BIDMC_seen_regression']
    noise = [r for r in records if r.get('expected_no_pulse')]
    clean = [r for r in records if r['category'] == 'SYNTHETIC_clean']
    pulse = [r for r in records if r['category'] == 'SYNTHETIC_weak_pulse']
    result = {'baseline_reference': aggregate(public, 'current_cpp'), 'candidates': {}}
    for name in ALGORITHMS:
        ref, bad, easy, weak = [aggregate(group, name) for group in (public, noise, clean, pulse)]
        base = result['baseline_reference']
        # Chọn để kiểm vòng mới, chưa phải quyết định nạp lên người.
        checks = {
            'no_aperiodic_noise_acceptance': bad['accepted'] == 0,
            'clean_coverage_at_least_90pct': easy['availability_pct'] is not None and easy['availability_pct'] >= 90,
            'clean_mae_at_most_2bpm': easy['mae'] is not None and easy['mae'] <= 2,
            'reference_mae_budget': ref['mae'] is not None and base['mae'] is not None and ref['mae'] <= base['mae']+.2,
            'reference_p95_budget': ref['p95'] is not None and base['p95'] is not None and ref['p95'] <= base['p95']+.5,
            'no_more_reference_large_errors': ref['over10'] <= base['over10'],
            'reference_coverage_loss_at_most_5pct': ref['accepted'] >= .95*base['accepted'],
            'adds_reference_windows': ref['added_windows'] > 0,
            'added_weak_pulse_mae_at_most_5bpm': weak['added_mae'] is not None and weak['added_mae'] <= 5,
            'no_added_weak_pulse_large_error': weak['added_over10'] == 0,
        }
        result['candidates'][name] = {'reference': ref, 'noise': bad, 'clean': easy, 'weak': weak,
                                      'checks': checks, 'passes': all(checks.values())}
    passing = [name for name, value in result['candidates'].items() if value['passes']]
    result['selected_for_new_simulation'] = min(passing, key=lambda name: (
        result['candidates'][name]['reference']['added_mae'],
        -result['candidates'][name]['reference']['added_windows'], name)) if passing else None
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--phase', choices=('development', 'validation'), default='development')
    parser.add_argument('--report', type=Path)
    parser.add_argument('--development-report', type=Path, default=ROOT/'backend/storage/local/ppg-weak-development.json')
    args = parser.parse_args()
    target = args.report or ROOT/f'backend/storage/local/ppg-weak-{args.phase}.json'
    if target.exists():
        raise FileExistsError(f'Không ghi đè báo cáo: {target}')
    files = ('scripts/ppg_weak_candidate.py', 'scripts/benchmark_ppg_weak.py',
             'scripts/benchmark_ppg_candidates.py', 'scripts/benchmark_ppg_reference.py',
             'scripts/ppg_msptd_reference.py', 'scripts/benchmark_ppg_quality.py',
             'ai/edge_firmware/tests/native/ppg_benchmark_harness.cpp',
             'ai/edge_firmware/include/processing/ppg_rate.h',
             'ai/edge_firmware/include/processing/ppg_contact.h',
             'ai/edge_firmware/include/processing/sensor_math.h')
    hashes = {p: digest(ROOT/p) for p in files}
    selected = None
    if args.phase == 'validation':
        dev = json.loads(args.development_report.read_text(encoding='utf-8'))
        if dev['source_hashes'] != hashes or dev['specifications'] != specifications():
            raise ValueError('Source/cấu hình đã đổi sau development; không gọi là validation khóa trước')
        selected = dev['decision']['selected_for_new_simulation']
        if selected is None:
            raise ValueError('Không ứng viên nào qua development; không chọn bằng validation')
    report = {'role': 'offline algorithm experiment, not firmware deployment or wrist accuracy validation',
              'phase': args.phase, 'source_hashes': hashes, 'specifications': specifications(),
              'selected_before_validation': selected, 'records': [],
              'reference_limitations': ['BIDMC01-15 already seen: regression only, not independent test.',
                                        'No synchronized HR reference on DEVICE wrist traces.',
                                        'Simulation is not a calibrated skin/optical model.',
                                        'Periodic optical interference can resemble a pulse; reported separately.']}
    target.parent.mkdir(parents=True, exist_ok=True)
    lock = target.with_suffix('.lock.json')
    with lock.open('x', encoding='utf-8') as handle:
        json.dump({k: v for k, v in report.items() if k != 'records'}, handle, ensure_ascii=False, indent=2)
    compiler = shutil.which(os.environ.get('CXX', 'g++')) or shutil.which('clang++')
    if not compiler:
        raise RuntimeError('Cần C++ compiler để chạy bộ lọc thực tế')
    with TemporaryDirectory(prefix='asd-weak-') as temp:
        exe = Path(temp)/('weak.exe' if os.name == 'nt' else 'weak')
        subprocess.run([compiler, '-std=c++17', '-O2', '-Wall', '-Wextra', '-Werror',
                        '-I', str(ROOT/'ai/edge_firmware/include'),
                        str(ROOT/'ai/edge_firmware/tests/native/ppg_benchmark_harness.cpp'),
                        '-o', str(exe)], check=True)

        def add(name, category, text, **kwargs):
            result = evaluate(exe, text, extra_algorithms=ALGORITHMS, extra_evaluator=Evaluator(), **kwargs)
            result.update(name=name, category=category, input_sha256=hashlib.sha256(text.encode()).hexdigest())
            report['records'].append(result)
            # Lưu checkpoint sau từng trace, không mất tiến độ nếu có lỗi.
            save_report(target, report)
            print(json.dumps({'name': name, 'accepted': {n: r['accepted_windows'] for n, r in result['summary'].items()}}), flush=True)
            return result

        if args.phase == 'development':
            manifest_path = ROOT/'backend/storage/local/hr-optical-manifest-20261107.json'
            manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
            report['trace_manifest_sha256'] = digest(manifest_path)
            for trace in manifest['traces']:
                if not trace['included_in_four_complete_trials']:
                    continue
                path = ROOT/trace['raw_csv']
                if digest(path) != trace['raw_sha256']:
                    raise ValueError('Hash trace không khớp manifest')
                add(trace['trial'], 'DEVICE_no_reference', '\n'.join(path.read_text(encoding='utf-8-sig').splitlines()[1:])+'\n')
            source = ROOT/'backend/storage/local/bidmc-1.0.0'
            checks = {p[1].lstrip('*'): p[0] for line in required_file(source, 'SHA256SUMS.txt', False).read_text().splitlines()
                      if len(p := line.split(maxsplit=1)) == 2}
            if digest(required_file(source, 'LICENSE', False)) != checks.get('LICENSE'):
                raise ValueError('Hash LICENSE không khớp')
            for index in range(1, 11):
                paths = [required_file(source, f'bidmc_csv/bidmc_{index:02d}_{kind}.csv', False)
                         for kind in ('Signals', 'Numerics')]
                for path in paths:
                    if digest(path) != checks.get('bidmc_csv/'+path.name):
                        raise ValueError(f'Checksum mismatch: {path.name}')
                text, end = prepare_signal(paths[0])
                row = add(f'BIDMC_{index:02d}', 'BIDMC_seen_regression', text,
                          numeric=np.genfromtxt(paths[1], delimiter=',', names=True, autostrip=True), last_time=end)
                row['source_hashes'] = {p.name: digest(p) for p in paths}
        seeds = (3411,) if args.phase == 'development' else (9011, 9029)
        # Cùng bộ noise regression cũ, validation dùng seed đã định trước khác.
        for name, t, x in controls(seeds=(17, 37, 73, 101, 211) if args.phase == 'development' else (941, 953)):
            known = float(name.rsplit('_', 1)[-1]) if name.startswith('SYNTHETIC_clean_') else None
            row = add(name, 'SYNTHETIC_clean' if known is not None else 'SYNTHETIC_noise',
                      payload(t, 80000+.8*x, 100000+x), reference_constant=known)
            row['expected_no_pulse'] = known is None
        for seed in seeds:
            for name, t, red, ir, known, no_pulse, periodic in simulations(seed):
                row = add(f'{name}_seed{seed}', 'SYNTHETIC_weak_pulse' if known is not None else 'SYNTHETIC_noise',
                          payload(t, red, ir), reference_constant=known)
                row['expected_no_pulse'] = no_pulse
                row['known_periodic_interference'] = periodic
        report['decision'] = choose(report['records']) if args.phase == 'development' else {
            'locked_candidate': selected,
            'noise': aggregate([r for r in report['records'] if r.get('expected_no_pulse')], selected),
            'weak': aggregate([r for r in report['records'] if r['category'] == 'SYNTHETIC_weak_pulse'], selected)}
    report['complete'] = True
    if hashes != {p: digest(ROOT/p) for p in files}:
        raise RuntimeError('Source đổi trong lúc benchmark')
    save_report(target, report)
    print(json.dumps(report['decision']), flush=True)


if __name__ == '__main__':
    main()
