"""Hồi quy phần chấm: không lấp thời gian mất mẫu bằng dự đoán đã cũ."""
import io
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np

from benchmark_ppg_candidates import evaluate, ALGORITHMS


def fixture(gap=False):
    t = np.arange(2000)*20
    if gap:
        t = t[(t<20000)|(t>=26000)]
    raw = np.column_stack((t+1000,np.full(len(t),80000),np.full(len(t),100000)))
    stream = np.column_stack((t+1000,np.ones(len(t)),np.full(len(t),80),
                              np.sin(t/100),np.sin(t/100),np.ones(len(t)),(t>=26000).astype(int) if gap else np.zeros(len(t))))
    payload = '\n'.join(','.join(str(int(x)) for x in row) for row in raw)+'\n'
    output = io.StringIO()
    np.savetxt(output,stream,delimiter=',')
    return payload,SimpleNamespace(stdout=output.getvalue())


def main():
    payload,run = fixture(gap=True)
    with patch('benchmark_ppg_candidates.subprocess.run',return_value=run), patch('benchmark_ppg_candidates.heart_rate',return_value=(80,10,10)):
        report = evaluate(Path('fake'),payload)
    rows = {r['end_s']:r for r in report['rows']}
    # Mốc20s vẫn cách mẫu19,98s chỉ20ms, nằm trong tuổi mẫu40ms cho phép.
    for second in range(21,26):
        assert all(rows[second]['predictions'][a] is None for a in ALGORITHMS)
    for second in range(26,36):
        assert rows[second]['predictions']['msptd_ir_candidate'] is None
    assert report['no_fresh_sample_windows']==5
    assert rows[36]['predictions']['msptd_ir_candidate']==80
    cases = 3
    payload,run = fixture()
    with patch('benchmark_ppg_candidates.subprocess.run',return_value=run), patch('benchmark_ppg_candidates.heart_rate',return_value=(80,10,10)):
        known = evaluate(Path('fake'),payload,reference_constant=80)
        for name in ALGORITHMS:
            assert known['summary'][name]['mae_on_accepted_bpm']==0
        missing = np.zeros(41,dtype=[('time',float),('HR',float)])
        missing['time']=np.arange(41);missing['HR']=np.nan
        absent = evaluate(Path('fake'),payload,numeric=missing,last_time=40)
        assert not absent['rows']
        assert absent['summary']['current_cpp']['mae_on_accepted_bpm'] is None
        assert absent['summary']['current_cpp']['availability_pct'] is None
    cases += 2
    try:
        evaluate(Path('fake'),'1000,80000,100000\n900,80000,100000\n')
    except ValueError:
        cases += 1
    else:
        raise AssertionError('Reordered timestamps accepted')
    print(f'PASS: {cases} scoring cases (gap freshness/recovery history/reference missing/known rate/timestamp order)')


if __name__=='__main__':
    main()
