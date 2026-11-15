"""Ứng viên HR cho sóng yếu, chỉ chạy offline; chưa dùng trong firmware.

Không nhận HR tham chiếu làm đầu vào. Không điền số cũ khi cửa sổ hiện tại
không đạt. Ngưỡng là giả thuyết kỹ thuật, không phải xác suất đúng/y khoa.
"""
from dataclasses import asdict, dataclass

import numpy as np

from ppg_msptd_reference import detect


@dataclass(frozen=True)
class Configuration:
    name: str = 'robust_peaks'
    rr_tolerance: float = .25
    min_interval_fraction: float = .60
    min_intervals: int = 4
    min_score: float = .65
    min_correlation: float = .30
    min_spectral_fraction: float = .40


CONFIGURATIONS = (Configuration(), Configuration(name='period_consensus', min_score=.60,
                                                min_correlation=.35, min_spectral_fraction=.45))
ALGORITHMS = tuple(c.name for c in CONFIGURATIONS)


def specifications():
    return {
        'version': 2, 'configurations': [asdict(c) for c in CONFIGURATIONS],
        'input': 'production causal HP0.5/LP4Hz, trailing 400 samples at nominal 50Hz',
        'preprocessing': 'linear detrend within available past window; no zero-phase replacement',
        'range_bpm': [40, 200], 'minimum_amplitude_counts': 4,
        'score_weights': {'rr': .25, 'template': .20, 'spectrum': .25,
                          'autocorrelation': .20, 'recent': .10},
        'spectral_half_width_hz': .15, 'harmonics': 3,
        'confirmations': 2, 'maximum_confirmation_gap_ms': 1500,
        'maximum_confirmation_difference_fraction': .12,
        'two_usable_channels_conflict_fraction': .12,
        'selection': 'best observed score; no preferred HR range or reference input',
        'deployment': 'offline only; not a hybrid fallback that preserves baseline mistakes',
        'period_consensus': {
            'robust_clip_mad_sigma': 6, 'fft_points': 2048,
            'min_peak_relative_power': .20, 'autocorrelation_lag_tolerance_samples': 2,
            'full_recent_weights': [.35, .25], 'spectrum_weight': .40,
            'recent_samples': 300, 'min_recent_correlation': .20,
            'min_tail_energy_fraction': .12, 'tail_samples': 75,
            'subharmonic': 'prefer candidate at half dominant frequency only with >=25% fundamental peak power and score within .10 of best',
            'note': 'trailing-window operation only; FFT zero padding interpolates spectrum, not true frequency resolution',
        },
    }


def detrend(values):
    axis = np.arange(len(values), dtype=float) - (len(values)-1)/2
    return values-values.mean()-axis*np.dot(axis, values)/np.dot(axis, axis)


def spectrum_fraction(x, bpm):
    power = np.abs(np.fft.rfft(x*np.hanning(len(x))))**2
    frequency = np.fft.rfftfreq(len(x), .02)
    band = (frequency >= .5) & (frequency <= 4)
    pulse = np.zeros(len(power), dtype=bool)
    for harmonic in (1, 2, 3):
        pulse |= np.abs(frequency-harmonic*bpm/60) <= .15
    total = power[band].sum()
    return float(power[band & pulse].sum()/total) if total > 0 else 0.


def correlation(x, lag):
    if lag <= 0 or lag >= len(x)-2:
        return 0.
    a, b = x[lag:], x[:-lag]
    a, b = a-a.mean(), b-b.mean()
    norm = np.linalg.norm(a)*np.linalg.norm(b)
    return float(np.dot(a, b)/norm) if norm > 1e-12 else 0.


def _template(x, peaks, mask):
    waves = []
    for left, right in zip(peaks[:-1][mask], peaks[1:][mask]):
        segment = x[left:right+1]
        segment = segment-np.linspace(segment[0], segment[-1], len(segment))
        wave = np.interp(np.linspace(0, 1, 32), np.linspace(0, 1, len(segment)), segment)
        wave -= wave.mean()
        norm = np.linalg.norm(wave)
        if norm > 1e-9:
            waves.append(wave/norm)
    if len(waves) < 2:
        return 0.
    waves = np.array(waves)
    others = (waves.sum(axis=0)[None, :]-waves)/(len(waves)-1)
    norms = np.linalg.norm(others, axis=1)
    return float(np.median(np.sum(waves*others, axis=1)/np.maximum(norms, 1e-12)))


def robust_peaks(values, configuration):
    x = np.asarray(values, dtype=float)
    if x.shape != (400,) or not np.isfinite(x).all():
        return {'usable': False, 'reason': 'INVALID_WINDOW'}
    x = detrend(x)
    amplitude = float(2*np.sqrt(2*np.mean(x*x)))
    if amplitude < 4:
        return {'usable': False, 'reason': 'LOW_AMPLITUDE'}
    detected, _ = detect(x)
    peaks = []
    for p in detected:
        if peaks and p-peaks[-1] < 15:
            if x[p] > x[peaks[-1]]:
                peaks[-1] = int(p)
        else:
            peaks.append(int(p))
    peaks = np.array(peaks, dtype=int)
    rr = np.diff(peaks)/50
    valid = (rr >= .3) & (rr <= 1.5)
    if np.sum(valid) < configuration.min_intervals:
        return {'usable': False, 'reason': 'INSUFFICIENT_INTERVALS'}
    center = float(np.median(rr[valid]))
    keep = valid & (np.abs(rr-center) <= configuration.rr_tolerance*center)
    # Bỏ ngoại lệ khỏi ước tính, không sửa timestamp hoặc bịa thêm một đỉnh.
    if np.sum(keep) < configuration.min_intervals or keep.mean() < configuration.min_interval_fraction:
        return {'usable': False, 'reason': 'INCOHERENT_INTERVALS'}
    intervals = rr[keep]
    bpm = float(60/intervals.mean())
    last_peak = int(peaks[1:][keep][-1])
    if (399-last_peak)/50 > min(3, 1.5*float(np.median(intervals))+.05):
        return {'usable': False, 'reason': 'STALE_PEAK'}
    lag = round(3000/bpm)
    periodicity = max(correlation(x, n) for n in range(max(1, lag-1), lag+2))
    spectral = spectrum_fraction(x, bpm)
    template = _template(x, peaks, keep)
    cv = float(np.std(intervals)/intervals.mean())
    # Recent chỉ đóng góp bằng chứng: hai đỉnh sai không phủ quyết cả 8 giây.
    recent = rr[keep & (peaks[1:] >= 200)]
    recent_difference = abs(60/recent.mean()-bpm)/bpm if len(recent) >= 2 else None
    recent_score = max(0., 1-recent_difference/.25) if recent_difference is not None else .5
    score = (.25*max(0., 1-cv/.25) + .20*max(0., template) +
             .25*spectral + .20*max(0., periodicity) + .10*recent_score)
    usable = (40 <= bpm <= 200 and periodicity >= configuration.min_correlation and
              spectral >= configuration.min_spectral_fraction and score >= configuration.min_score)
    return {'usable': bool(usable), 'reason': 'ACCEPTABLE' if usable else 'WEAK_EVIDENCE',
            'bpm': bpm, 'score': float(score), 'amplitude': amplitude,
            'intervals_total': len(rr), 'intervals_used': int(keep.sum()), 'rr_cv': cv,
            'template': template, 'spectral_fraction': spectral,
            'correlation': periodicity, 'recent_difference': recent_difference}


def period_consensus(values, configuration):
    """Chu kỳ đủ bằng chứng, không cần phát hiện đủ từng đỉnh của sóng yếu."""
    x = np.asarray(values, dtype=float)
    if x.shape != (400,) or not np.isfinite(x).all():
        return {'usable': False, 'reason': 'INVALID_WINDOW'}
    x = detrend(x)
    center = float(np.median(x))
    scale = 1.4826*float(np.median(np.abs(x-center)))
    if scale < 1e-9:
        return {'usable': False, 'reason': 'FLAT_WINDOW'}
    # Chỉ giảm ảnh hưởng xung trong cửa sổ đã có; không sửa raw hay dùng mẫu tương lai.
    x = detrend(np.clip(x, center-6*scale, center+6*scale))
    energy = float(np.mean(x*x))
    amplitude = float(2*np.sqrt(2*energy))
    if amplitude < 4 or np.mean(x[-75:]**2) < .12*energy:
        return {'usable': False, 'reason': 'LOW_OR_OLD_ENERGY'}
    power = np.abs(np.fft.rfft(x*np.hanning(400), n=2048))**2
    frequencies = np.fft.rfftfreq(2048, .02)
    indices = np.arange(1, len(power)-1)
    peaks = indices[(power[indices] >= power[indices-1]) & (power[indices] > power[indices+1]) &
                    (frequencies[indices] >= 40/60-25/2048) &
                    (frequencies[indices] <= 200/60+25/2048)]
    if not len(peaks):
        return {'usable': False, 'reason': 'NO_SPECTRAL_PEAK'}
    dominant = int(peaks[np.argmax(power[peaks])])
    options = []
    for peak in peaks:
        if power[peak] < .20*power[dominant]:
            continue
        target_lag = round(50/frequencies[peak])
        lags = range(max(15, target_lag-2), min(75, target_lag+2)+1)
        lag = max(lags, key=lambda n: correlation(x, n))
        # Không lấy sườn một đỉnh tương quan nằm ngoài vùng ứng viên làm chu kỳ.
        left, middle, right = [correlation(x, n) for n in (lag-1, lag, lag+1)]
        if middle < left or middle < right:
            continue
        denominator = left-2*middle+right
        offset = .5*(left-right)/denominator if 15 < lag < 75 and denominator < -1e-9 else 0.
        period = lag+float(np.clip(offset, -.5, .5))
        bpm = 3000/period
        if not 40 <= bpm <= 200 or abs(bpm/60-frequencies[peak]) > .12*frequencies[peak]:
            continue
        recent = correlation(detrend(x[-300:]), lag)
        spectral = spectrum_fraction(x, bpm)
        score = .35*max(0., middle)+.25*max(0., recent)+.40*spectral
        if middle >= configuration.min_correlation and recent >= .20 and spectral >= configuration.min_spectral_fraction:
            options.append({'bpm': float(bpm), 'score': float(score), 'correlation': middle,
                            'recent_correlation': recent, 'spectral_fraction': spectral,
                            'relative_peak_power': float(power[peak]/power[dominant])})
    if not options:
        return {'usable': False, 'reason': 'PERIOD_EVIDENCE_MISMATCH'}
    chosen = max(options, key=lambda f: f['score'])
    # Có thành phần cơ bản rõ cùng hài mạnh: không tự chọn gấp đôi vì đỉnh phổ cao hơn.
    lower = [o for o in options if o['relative_peak_power'] >= .25 and
             abs(2*o['bpm']-60*frequencies[dominant]) <= .10*60*frequencies[dominant] and
             o['score'] >= chosen['score']-.10]
    if lower:
        chosen = max(lower, key=lambda f: f['score'])
    usable = chosen['score'] >= configuration.min_score
    return {**chosen, 'usable': bool(usable), 'reason': 'ACCEPTABLE' if usable else 'WEAK_EVIDENCE',
            'amplitude': amplitude}


class Evaluator:
    def __init__(self):
        self.previous = {}

    def __call__(self, window, now_ms, segment, baseline):
        del baseline  # Đánh giá ứng viên độc lập, không kế thừa số sai của baseline.
        if window is not None:
            window = np.asarray(window, dtype=float)
            if window.shape != (400, 2) or not np.isfinite(window).all():
                window = None
        predictions, diagnostics = {}, {}
        for config in CONFIGURATIONS:
            estimator = robust_peaks if config.name == 'robust_peaks' else period_consensus
            channels = [estimator(window[:, i], config) for i in (0, 1)] if window is not None else []
            good = [f for f in channels if f['usable']]
            conflict = len(good) == 2 and abs(good[0]['bpm']-good[1]['bpm']) > .12*good[0]['bpm']
            chosen = max(good, key=lambda f: f['score']) if good and not conflict else None
            previous = self.previous.get(config.name)
            confirmed = (chosen is not None and previous is not None and previous[2] == segment and
                         0 < now_ms-previous[0] <= 1500 and
                         abs(chosen['bpm']-previous[1]) <= .12*chosen['bpm'])
            self.previous[config.name] = (now_ms, chosen['bpm'], segment) if chosen is not None else None
            predictions[config.name] = chosen['bpm'] if confirmed else None
            diagnostics[config.name] = {'channels': channels, 'conflict': bool(conflict),
                                        'confirmed': bool(confirmed)}
        return predictions, diagnostics
