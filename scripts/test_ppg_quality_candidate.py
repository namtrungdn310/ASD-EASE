"""Hồi quy ứng viên chất lượng, không thay đánh giá dữ liệu ngoài hoặc đo người."""
from pathlib import Path
from unittest.mock import patch

import numpy as np

from benchmark_ppg_candidates import evaluate
from ppg_quality_candidate import Evaluator, POLICIES, EXTRA_ALGORITHMS, features, qualifies
from test_ppg_candidate_scoring import fixture


def main():
    cases = 0
    for bpm in [40,60,80,100,150,180,200]:
        x = np.sin(np.arange(400)*2*np.pi*bpm/3000)*1800
        f = features(x)
        if bpm==40 and f.get('reason')=='INSUFFICIENT_BEATS':
            # 8s ở40bpm có thể không đủ5 đỉnh sau xử lý biên. Không nới policy
            # để ép pass: hybrid vẫn phải giữ HR40 đã được bộ đối chứng xác nhận.
            kept,_ = Evaluator()(np.column_stack((x,x*.7)),13000,1,40.)
            assert all(kept['hybrid_'+p.name]==40 and kept['quality_'+p.name] is None for p in POLICIES)
            cases += 1
            continue
        for policy in POLICIES:
            assert qualifies(f,policy),(bpm,policy,f)
        evaluator = Evaluator()
        window = np.column_stack((x,x*.7))
        a,_ = evaluator(window,13000,1,None)
        b,_ = evaluator(window,14000,1,None)
        assert all(a[k] is None for k in EXTRA_ALGORITHMS)
        assert all(b[k] is not None and abs(b[k]-bpm)<2 for k in EXTRA_ALGORITHMS)
        c,_ = evaluator(None,15000,1,None)
        assert all(c[k] is None for k in EXTRA_ALGORITHMS)
        d,_ = evaluator(window,16000,1,None)
        assert all(d[k] is None for k in EXTRA_ALGORITHMS)
        cases += 1
    for x in [np.ones(400),np.full(400,np.nan),np.ones(399)]:
        f = features(x)
        assert not any(qualifies(f,p) for p in POLICIES)
        cases += 1
    x = np.sin(np.arange(400)*2*np.pi*80/3000)*1800
    window = np.column_stack((x,x*.7))
    evaluator = Evaluator();evaluator(window,13000,1,None)
    changed,_ = evaluator(window,14000,2,None)
    assert all(changed[k] is None for k in EXTRA_ALGORITHMS)
    cases += 1
    evaluator = Evaluator();evaluator(window,13000,1,None)
    late,_ = evaluator(window,15001,1,None)
    assert all(late[k] is None for k in EXTRA_ALGORITHMS)
    cases += 1
    evaluator = Evaluator()
    disagree = np.column_stack((x,np.sin(np.arange(400)*2*np.pi*130/3000)*1800))
    evaluator(disagree,13000,1,None)
    rejected,_ = evaluator(disagree,14000,1,None)
    assert all(rejected[k] is None for k in EXTRA_ALGORITHMS)
    cases += 1
    # Hybrid không được thay số đã được bộ hiện tại công nhận hoặc giả HR lúc None.
    evaluator = Evaluator()
    kept,_ = evaluator(None,13000,1,73.2)
    assert all(kept['hybrid_'+p.name]==73.2 and kept['quality_'+p.name] is None for p in POLICIES)
    cases += 1
    # Không dùng nhãn tham chiếu làm đầu vào hoặc dừng cập nhật state khi thiếu nhãn.
    payload,run = fixture()
    numeric = np.zeros(41,dtype=[('time',float),('HR',float)])
    numeric['time']=np.arange(41);numeric['HR']=np.nan
    class Counter:
        calls = 0
        def __call__(self,*args):
            self.calls += 1
            return {'probe':None},{}
    counter = Counter()
    with patch('benchmark_ppg_candidates.subprocess.run',return_value=run),patch('benchmark_ppg_candidates.heart_rate',return_value=(80,10,10)):
        absent = evaluate(Path('fake'),payload,numeric=numeric,last_time=40,
                          extra_algorithms=('probe',),extra_evaluator=counter)
    assert not absent['rows'] and counter.calls==27
    cases += 1
    print(f'PASS: {cases} quality candidate cases (clean rates, rejection, freshness, segment, conflict, baseline preservation, reference independence)')


if __name__=='__main__':
    main()
