"""Ứng viên MSPTD + kiểm chất lượng, chỉ offline, ngưỡng kỹ thuật chưa kiểm định.

Ý tưởng template correlation tham khảo tài liệu tác giả PPG-quality:
https://ppg-quality.readthedocs.io/en/latest/functions/assess_ppg_quality/
Không sao chép bộ ppgSQI125Hz hay coi các ngưỡng dưới là ngưỡng của công bố đó.
Hai cấu hình được chốt trước chạy bộ bước3; không lấy HR tham chiếu làm đầu vào.
"""
from dataclasses import asdict, dataclass

import numpy as np

from ppg_msptd_reference import detect, heart_rate


@dataclass(frozen=True)
class Policy:
    name: str
    max_rr_cv: float
    min_template_median: float
    min_template_p20: float
    min_spectral_fraction: float


POLICIES = (
    Policy('balanced',.18,.85,.65,.55),
    Policy('strict',.12,.90,.75,.65),
)
EXTRA_ALGORITHMS = tuple(f'{mode}_{p.name}' for p in POLICIES for mode in ['quality','hybrid'])


def specifications():
    return {
        'policies':[asdict(p) for p in POLICIES],
        'shared':{'fs':50,'window_samples':400,'template_points':32,'min_intervals':4,
                  'bpm_range':[40,200],'min_equivalent_amplitude_counts':4,
                  'recent_window_samples':200,'max_full_recent_difference_fraction':.12,
                  'spectrum_band_hz':[.5,4],'harmonic_count':3,'harmonic_half_width_hz':.15,
                  'max_peak_age_rr_factor':1.5,'peak_age_tolerance_s':.05,
                  'confirmations':2,'max_confirmation_gap_ms':1500},
        'hybrid':'preserve current C++ valid result; only use independently confirmed quality candidate when current is null',
        'warning':'engineering research policy; regularity gate can reject irregular rhythms; not a diagnosis or quality probability',
    }


def _detrend(x):
    axis = np.arange(len(x),dtype=float)-(len(x)-1)/2
    return x-x.mean()-axis*np.dot(axis,x)/np.dot(axis,axis)


def features(values, fs=50):
    x = np.asarray(values,dtype=float)
    if x.shape!=(400,) or not np.isfinite(x).all():
        return {'usable':False,'reason':'INVALID_WINDOW'}
    clean = _detrend(x)
    amplitude = float(2*np.sqrt(2*np.mean(clean**2)))
    if amplitude<4:
        return {'usable':False,'reason':'LOW_AMPLITUDE','amplitude':amplitude}
    detected,_ = detect(x,fs)
    # Gom đỉnh gần hơn thời gian trơ tối thiểu200bpm; giữ đỉnh cao hơn.
    peaks = []
    for p in detected:
        if peaks and p-peaks[-1]<15:
            if x[p]>x[peaks[-1]]:
                peaks[-1] = int(p)
        else:
            peaks.append(int(p))
    peaks = np.array(peaks,dtype=int)
    if len(peaks)<5:
        return {'usable':False,'reason':'INSUFFICIENT_BEATS','amplitude':amplitude,'peak_count':len(peaks)}
    rr = np.diff(peaks)/fs
    if np.any(rr<.3) or np.any(rr>1.5):
        return {'usable':False,'reason':'RR_RANGE','amplitude':amplitude,'peak_count':len(peaks)}
    bpm = float(60*fs*(len(peaks)-1)/(peaks[-1]-peaks[0]))
    recent,_,_ = heart_rate(x[-200:],fs)
    if recent is None or not 40<=bpm<=200 or abs(bpm-recent)>.12*bpm:
        return {'usable':False,'reason':'RECENT_DISAGREEMENT','bpm':bpm,'recent_bpm':recent}
    age = (len(x)-1-peaks[-1])/fs
    if age>min(3,1.5*float(np.median(rr))+.05):
        return {'usable':False,'reason':'STALE_PEAK','bpm':bpm,'age_s':age}
    waves = []
    for left,right in zip(peaks[:-1],peaks[1:]):
        segment = x[left:right+1]
        # Bỏ đường nối hai đầu trước chuẩn hoá pha; không chỉnh biên độ theo HR đúng.
        segment = segment-np.linspace(segment[0],segment[-1],len(segment))
        wave = np.interp(np.linspace(0,1,32),np.linspace(0,1,len(segment)),segment)
        wave -= wave.mean()
        norm = np.linalg.norm(wave)
        if norm<1e-6:
            return {'usable':False,'reason':'FLAT_BEAT','bpm':bpm}
        waves.append(wave/norm)
    waves = np.array(waves)
    # Leave-one-out: mỗi nhịp không góp vào chính template được dùng để chấm nó.
    others = (waves.sum(axis=0)[None,:]-waves)/(len(waves)-1)
    norms = np.linalg.norm(others,axis=1)
    correlations = np.sum(waves*others,axis=1)/np.maximum(norms,1e-12)
    fft = np.abs(np.fft.rfft(clean*np.hanning(len(clean))))**2
    frequencies = np.fft.rfftfreq(len(clean),1/fs)
    band = (frequencies>=.5)&(frequencies<=4)
    pulse_band = np.zeros(len(frequencies),dtype=bool)
    for harmonic in [1,2,3]:
        pulse_band |= np.abs(frequencies-harmonic*bpm/60)<=.15
    total = fft[band].sum()
    spectral = float(fft[band&pulse_band].sum()/total) if total>0 else 0.
    return {'usable':True,'bpm':bpm,'recent_bpm':float(recent),'peak_count':len(peaks),
            'amplitude':amplitude,'rr_cv':float(np.std(rr)/np.mean(rr)),
            'template_median':float(np.median(correlations)),
            'template_p20':float(np.percentile(correlations,20)),
            'spectral_fraction':spectral,'peak_age_s':float(age)}


def qualifies(f,policy):
    return (f.get('usable',False) and f['rr_cv']<=policy.max_rr_cv and
            f['template_median']>=policy.min_template_median and
            f['template_p20']>=policy.min_template_p20 and
            f['spectral_fraction']>=policy.min_spectral_fraction)


class Evaluator:
    def __init__(self):
        self.previous = {}

    def __call__(self,window,now_ms,segment,baseline):
        fs = [features(window[:,i]) for i in [0,1]] if window is not None else []
        predictions,diagnostics = {},{'channels':fs,'policies':{}}
        for policy in POLICIES:
            chosen = None
            source = None
            if fs:
                ir,red = [qualifies(f,policy) for f in fs]
                if ir and red and abs(fs[0]['bpm']-fs[1]['bpm'])>.12*fs[0]['bpm']:
                    pass  # Hai kênh rõ nhưng bất đồng: không chọn theo số trông đẹp.
                elif ir:
                    chosen,source = fs[0]['bpm'],'IR'
                elif red:
                    chosen,source = fs[1]['bpm'],'RED'
            previous = self.previous.get(policy.name)
            confirmed = chosen is not None and previous is not None and previous[2]==segment and (
                0<now_ms-previous[0]<=1500 and abs(chosen-previous[1])<=.12*chosen)
            self.previous[policy.name] = (now_ms,chosen,segment) if chosen is not None else None
            result = chosen if confirmed else None
            predictions[f'quality_{policy.name}'] = result
            predictions[f'hybrid_{policy.name}'] = baseline if baseline is not None else result
            diagnostics['policies'][policy.name] = {'qualified':chosen is not None,'confirmed':bool(confirmed),'source':source}
        return predictions,diagnostics
