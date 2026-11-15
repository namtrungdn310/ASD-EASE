"""Bản chuyển NumPy để đối chiếu offline MSPTDfast v2; không phải firmware.

Nguồn: Peter H. Charlton, ppg-beats, source/msptdfastv2_beat_detector.m,
commit c397be7afc0d8a1601a85cd673718372e40f1f59. Giữ cấu hình6s, overlap20%,
downsample bằng hệ số nguyên để fs>=20Hz, LMS cho HR>=30bpm và chỉnh đỉnh50ms.
Không thêm bộ đánh giá chất lượng hoặc sửa nhịp theo đáp án.

Adapted from code Copyright (c) 2022, 2024 Peter H. Charlton.
MIT License:
Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:
The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""
import numpy as np

UPSTREAM_COMMIT = "c397be7afc0d8a1601a85cd673718372e40f1f59"
UPSTREAM_URL = f"https://github.com/peterhcharlton/ppg-beats/blob/{UPSTREAM_COMMIT}/source/msptdfastv2_beat_detector.m"


def scalogram_extrema(values, fs, *, literal=False):
    """literal dùng đúng hai vòng lặp như nguồn để kiểm bản vector hoá."""
    values = np.asarray(values, dtype=float)
    n = len(values)
    if n < 6:
        return np.array([], dtype=int), np.array([], dtype=int)
    axis = np.arange(n, dtype=float) - (n-1)/2
    x = values-values.mean()-axis*np.dot(axis, values)/np.dot(axis, axis)
    length = int(np.ceil(n/2)-1)
    scales = np.arange(1, length+1)
    keep = (length/scales)/(n/fs) >= .5  # 30bpm: mặc định nguồn.
    if not keep.any():
        return np.array([], dtype=int), np.array([], dtype=int)
    max_scale = int(scales[keep][-1])
    maxima = np.zeros((max_scale, n), dtype=bool)
    minima = np.zeros_like(maxima)
    for k in range(1, max_scale+1):
        # MATLAB i=k+2:N-k+1 và chỉ số cột i-1 -> Python j=k:N-k-1.
        if literal:
            for j in range(k, n-k):
                maxima[k-1, j] = x[j] > x[j-k] and x[j] > x[j+k]
                minima[k-1, j] = x[j] < x[j-k] and x[j] < x[j+k]
        else:
            center = x[k:n-k]
            maxima[k-1, k:n-k] = (center > x[:n-2*k]) & (center > x[2*k:])
            minima[k-1, k:n-k] = (center < x[:n-2*k]) & (center < x[2*k:])
    peak_scale = int(np.argmax(maxima.sum(axis=1)))
    onset_scale = int(np.argmax(minima.sum(axis=1)))
    return (np.flatnonzero(maxima[:peak_scale+1].all(axis=0)),
            np.flatnonzero(minima[:onset_scale+1].all(axis=0)))


def detect(values, fs=50, *, literal=False):
    """Nhận sóng đã lọc. Chỉ số0-based; dùng phần dữ liệu hiện có, không nhìn tương lai."""
    values = np.asarray(values, dtype=float)
    if values.ndim != 1 or not np.isfinite(values).all():
        raise ValueError("MSPTD yêu cầu một đoạn liên tục, hữu hạn")
    if fs <= 0:
        raise ValueError("Sampling frequency must be positive")
    n = len(values)
    window = int(round(6*fs))
    if n <= window:
        spans = [(0, n)]
    else:
        offset = int(np.floor(window*.8+.5))
        # Giữ cửa sổ inclusive301 mẫu như MATLAB ở50Hz; không âm thầm sửa thành300.
        starts = list(range(0, n-window, offset))
        spans = [(start, start+window+1) for start in starts]
        if spans[-1][1] < n:
            spans.append((n-window-1, n))
    factor = max(1, int(np.floor(fs/20)))
    tolerance = int(np.ceil(fs*(.2 if fs/factor < 10 else .1 if fs/factor < 20 else .05)))
    peaks, onsets = [], []
    for start, end in spans:
        signal = values[start:end]
        p, t = scalogram_extrema(signal[::factor], fs/factor, literal=literal)
        for indices, output, maximum in [(p, peaks, True), (t, onsets, False)]:
            # Nguồn MATLAB nhân chỉ số1-based với factor rồi mới tìm cực trị.
            # Giữ đúng phép đổi sang0-based (khác mapping vật lý k*factor).
            for index in indices*factor+(factor-1):
                left, right = int(index)-tolerance, int(index)+tolerance+1
                if left < 0 or right > len(signal):
                    # Nguồn MATLAB không chặn biên; không tự clip sinh đỉnh giả.
                    continue
                chunk = signal[left:right]
                refined = np.argmax(chunk) if maximum else np.argmin(chunk)
                output.append(start+left+int(refined))
    return np.unique(peaks).astype(int), np.unique(onsets).astype(int)


def heart_rate(values, fs=50):
    """Ứng viên HR từ số đỉnh và khoảng đầu-cuối; CHƯA có cổng chất lượng.

    Không phải phép đo F1 từng nhịp hoặc tương đương cờ valid của driver.
    Chỉ chấm cùng dải40..200bpm để đối chiếu backend hiện tại.
    """
    peaks, onsets = detect(values, fs)
    if len(peaks) < 2:
        return None, len(peaks), len(onsets)
    bpm = 60*fs*(len(peaks)-1)/(peaks[-1]-peaks[0])
    return (float(bpm) if 40 <= bpm <= 200 else None), len(peaks), len(onsets)
