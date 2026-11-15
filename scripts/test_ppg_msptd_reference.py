"""Kiểm bản chuyển thuật toán offline; không thay chạy MATLAB hoặc nghiệm thu board."""
import numpy as np
from ppg_msptd_reference import detect, scalogram_extrema, heart_rate


def main():
    rng = np.random.default_rng(1206)
    cases = 0
    for n in [51,100,151,201]:
        for fs in [20,25,50]:
            for x in [rng.normal(size=n), np.sin(np.arange(n)*.3), np.ones(n)]:
                a = scalogram_extrema(x, fs)
                b = scalogram_extrema(x, fs, literal=True)
                assert all(np.array_equal(left,right) for left,right in zip(a,b))
                cases += 1
    for bpm in [40,60,80,100,150,180,200]:
        x = np.sin(np.arange(400)*2*np.pi*bpm/3000)
        a = detect(x)
        b = detect(x,literal=True)
        assert all(np.array_equal(left,right) for left,right in zip(a,b))
        hr, _, _ = heart_rate(x)
        assert hr is not None and abs(hr-bpm)<2, (bpm,hr)
        cases += 1
    assert heart_rate(np.ones(400))[0] is None
    peaks, _ = detect(-np.cos(np.arange(400)*2*np.pi/50))
    assert np.array_equal(peaks,np.arange(25,400,50)), peaks
    cases += 1
    for bad in [np.full(400,np.nan),np.full(400,np.inf)]:
        try:
            detect(bad)
        except ValueError:
            cases += 1
        else:
            raise AssertionError("Nonfinite trace accepted")
    print(f"PASS: {cases+1} offline MSPTD port cases (literal-loop equivalence, clean rates, flat/nonfinite)")


if __name__ == '__main__':
    main()
