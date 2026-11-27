# Bước 3 — Chuẩn hóa WESAD và tính HR thử nghiệm

Ngày: 2026-11-17. Phiên bản: `wesad-normalization-v1`.

## Kết quả và giới hạn

Bộ chuyển đổi đọc dữ liệu cổ tay đã đồng bộ của WESAD, xuất từng kênh với đúng đơn vị/tần số và giữ nhãn riêng. Có bộ tính HR từ BVP để thử quy trình ML, **chưa được kiểm chứng sai số với nhịp tham chiếu**. Không thay firmware, thuật toán HR trên ESP hoặc dữ liệu hiển thị trên web.

Đây là phần chuẩn bị dữ liệu. Không có model stress, số accuracy/F1 hoặc khẳng định đã áp dụng được trên thiết bị. Tỷ lệ tính được HR khác với tỷ lệ HR đúng; bộ phát hiện đỉnh vẫn có thể nhận nhiễu hoặc nhầm nửa/gấp đôi nhịp.

## 1. Chạy công cụ

Tại root repo:

```powershell
.\.venv\Scripts\python.exe -m pip install -r ai/requirements.txt
.\.venv\Scripts\python.exe scripts/prepare_wesad.py
```

- Kiểm tra hash bản ZIP chính thức trước khi đọc pickle.
- Xử lý từng người để giới hạn RAM, không giải nén toàn bộ dataset.
- Chỉ tạo thư mục kết quả mới. Nếu thư mục đã tồn tại, lệnh báo lỗi, không xóa/ghi đè lượt trước. Muốn thử lại, chọn tên `--output` mới trong vùng dữ liệu local được ignore.
- Khi lỗi/ngắt, ghi trạng thái `INTERRUPTED_OR_FAILED` vào `run.json`; chưa có `COMPLETE` thì không dùng lượt đó như dữ liệu hoàn chỉnh.
- Không cần ESP, Docker, tài khoản Zenodo hoặc notebook để chạy bước này.

Ví dụ chạy riêng S2, giữ kết quả tách biệt:

```powershell
.\.venv\Scripts\python.exe scripts/prepare_wesad.py --subjects S2 --output ai/data/interim/wesad/smoke-s2-v1
```

Không đổi tham số HR theo kết quả nhãn hoặc điểm test. Nếu đổi phương pháp, phải có version/kết quả mới và đánh giá riêng.

## 2. Những file được tạo

```text
ai/data/interim/wesad/normalized-v1/
    run.json
    recordings.jsonl
    signals/S2/                      Tương tự với 14 người còn lại
        metadata.json
        bvp.csv
        eda_us.csv
        acc_x_ms2.csv
        acc_y_ms2.csv
        acc_z_ms2.csv
        acc_norm_ms2.csv
        hr_bpm.csv
        labels.csv
        hr_window_labels.csv
        acc_flags.csv
        window_quality.csv
```

Tất cả dữ liệu này giữ local, không đưa lên Git. Metadata ghi đơn vị, số mẫu, số thiếu, tần số danh định, nguồn archive member và hash từng CSV. `run.json` ghi SHA-256 archive, cấu hình HR, phiên bản NumPy/SciPy và trạng thái lượt xử lý. Không dùng timestamp máy tính để thay mốc đồng bộ của dataset.

Đặc tả bước 1 là khung ban đầu; cấu trúc cụ thể ở bước này đặt nhãn/metadata theo từng recording để tránh lẫn người. `recordings.jsonl` trỏ tới metadata từng người; không nối các người thành một recording dài.

## 3. Đơn vị và thời gian

| Kênh | Quy tắc |
|---|---|
| BVP | Giữ đơn vị tùy nguồn, 64 Hz; không giả thành RED/IR của MAX30102 |
| EDA | Giữ µS, 4 Hz; không đổi nhãn thành ADC Grove |
| Ax/Ay/Az | `raw / 64 * 9.80665`, 32 Hz, m/s²; giữ hướng trục nguồn |
| Độ lớn gia tốc | `sqrt(Ax² + Ay² + Az²)`, 32 Hz, vẫn gồm trọng lực |
| TEMP | Không đưa vào đầu vào model đầu; file gốc vẫn còn trong ZIP |
| HR | Kết quả tính trên cửa sổ BVP 10 giây, xuất 1 giây/lần; các cửa sổ chồng lấp nên không phải mẫu độc lập |

CSV tín hiệu gốc có `time_ms,value`. Mẫu thứ i ở `i * 1000 / fs`, thời gian tương đối từ đầu recording tác giả đã đồng bộ. Giữ phần thập phân, không ép EDA/ACC/BVP về 1 Hz hoặc ghép theo chỉ số hàng.

NaN/Infinity được biểu diễn thành ô trống; giữ số 0 nếu thực sự là 0 và giữ nguyên vị trí thời gian, không dồn mẫu. ACC chạm biên được đánh dấu ở `acc_flags.csv`, chưa âm thầm xóa hoặc kẹp số.

Timestamp tái dựng từ lịch danh định không chứng minh không mất mẫu thật ở thiết bị nguồn. Không gắn `sample_rate_measured_hz` bằng tần số danh định.

## 4. HR từ BVP đang được tính thế nào

Mã: [wesad.py](../../ai/src/preprocessing/wesad.py), phương pháp `bvp-causal-peaks-v1-experimental`.

1. Lọc Butterworth dạng SOS, prototype order 2, bandpass 0,5–5 Hz, một chiều theo thời gian. Không dùng lọc hai chiều nhìn vào dữ liệu tương lai.
2. Sau mỗi gap không hữu hạn, reset bộ lọc; dành 2 giây khởi tạo trước cửa sổ tính HR đầy đủ 10 giây. Kết quả đầu tiên có thể có ở giây 12. Không nội suy qua gap.
3. Mỗi giây tìm đỉnh trên 10 giây đã thu, khoảng cách tối thiểu theo trần 200 bpm, prominence tối thiểu bằng 0,5 lần độ lệch chuẩn của chính cửa sổ.
4. HR ứng viên = 60 / trung vị khoảng cách các đỉnh. Đòi ít nhất 3 khoảng, các khoảng trong dải phương pháp 40–200 bpm, CV khoảng nhịp ≤0,30 và tương quan tại chu kỳ ứng viên ≥0,25.
5. Đạt điều kiện kỹ thuật thì ghi `value`; chưa đạt giữ trống và ghi `reason`. `candidate_bpm` chỉ để chẩn đoán, không được lấy thay `value` khi bị từ chối.

Các hằng số trên được cố định trước lượt chạy đầy đủ, là cấu hình baseline kỹ thuật, **không phải ngưỡng tối ưu đã được nghiên cứu/hiệu chuẩn trên WESAD**. Dải phương pháp cũng không phải khoảng HR bình thường hoặc tiêu chuẩn phân loại stress.

Mỗi dòng có `window_start_ms`, `window_end_ms`, `time_ms=window_end_ms`, số đỉnh, CV và tương quan. Giá trị tóm tắt 10 giây quá khứ chỉ khả dụng cuối cửa sổ; không gán ngược về đầu hoặc tâm cửa sổ. Không thêm điểm chất lượng sinh lý % và không kéo dài HR cũ để tăng độ phủ.

HR chưa có sai số MAE hoặc độ đúng từng nhịp. Trước khi dùng HR này để kết luận model triển khai tốt, cần đánh giá phép tính với tham chiếu đủ tin cậy; ECG ngực có thể phục vụ **đánh giá riêng**, không được thay BVP thành feature đầu vào mà thiết bị cổ tay không có. Không dùng HR.csv/IBI.csv mà README WESAD yêu cầu bỏ qua làm đầu vào chính.

## 5. Nhãn và chất lượng không được trộn với đầu vào

- Detector HR không nhận nhãn stress, không reset theo task và không chọn đỉnh theo mức HR mong muốn.
- Sau khi tính xong, mới gắn mã/nhãn vào cửa sổ có cùng một mã nguồn trên toàn `[start, end)`. Cửa sổ cắt ranh giới nhãn giữ nhãn trống, không lấy đa số.
- Kết quả nhãn cửa sổ nằm riêng trong `hr_window_labels.csv`, không nằm trong CSV tín hiệu HR. Khi tạo X vẫn dùng danh sách feature cho phép rõ ràng, không tự đưa `time_ms`, `candidate_bpm` bị từ chối hoặc cờ chẩn đoán vào model.
- `wesad-binary-v1`: 1/3 → không stress (0), 2 → stress (1); 0/4/5/6/7 giữ mã gốc nhưng không đưa vào bài đầu.
- `labels.csv` giữ cả mã gốc, khoảng nhãn và phương pháp `study_protocol`. Nhãn không phải số đo stress liên tục hoặc mức nghiêm trọng.
- `window_quality.csv` đếm mẫu EDA/ACC, số thiếu, số âm/0/đoạn hằng EDA và mẫu ACC chạm biên trong cùng cửa sổ. Đây là chẩn đoán kỹ thuật, không phải feature stress mặc định hoặc % chất lượng sinh lý.
- Chưa tạo cửa sổ feature ML cuối cùng, split train/validation/test hoặc fit scaler. Cửa sổ 10 giây này dành riêng tính HR; không tự khóa cửa sổ model bằng 10 giây.

## 6. Kiểm chứng và kết quả thực

Đã chạy đủ **15/15 người**, `run.json` ghi `COMPLETE`. File xuất khoảng 581 MB, nằm trong thư mục local bị ignore. Đã kiểm tra lại 165 hash CSV, số mẫu/thời gian, quy đổi gia tốc và độ lớn, khoảng nhãn, nhãn của cửa sổ HR, giá trị trống và các điều kiện chấp nhận HR.

| Kết quả | Số lượng |
|---|---:|
| Dòng kết quả HR xuất mỗi giây | 86.868 |
| Dòng có HR ứng viên đạt cổng kỹ thuật | 41.717 (48,02%) |
| Dòng HR giữ trống | 45.151 |
| Tham chiếu HR/đánh giá sai số | Chưa thực hiện |
| Model stress | Chưa train |

Độ phủ HR trên những cửa sổ 10 giây nằm hoàn toàn trong một mã nhãn:

| Nhãn | Cửa sổ | Có HR ứng viên | Độ phủ |
|---|---:|---:|---:|
| Baseline (1) | 17.461 | 10.962 | 62,78% |
| Stress (2) | 9.816 | 1.602 | 16,32% |
| Amusement (3) | 5.425 | 3.739 | 68,92% |

**Chưa chấp nhận bộ HR này làm đầu vào cuối cùng.** Độ phủ lệch mạnh giữa các nhãn; bỏ mọi đoạn không có HR có thể làm tập train thiên lệch. Chưa có bằng chứng HR còn lại đúng; số đo đều/đẹp hoặc vượt cổng kỹ thuật không thay phép đối chiếu tham chiếu. Các tỉ lệ này là chẩn đoán sau chạy, không được dùng để điều chỉnh ngưỡng theo đáp án hoặc biến nhãn thành feature.

Ba lý do thiếu phổ biến: khoảng đỉnh ngoài dải phương pháp, khoảng nhịp không đều, tương quan chu kỳ yếu. Chưa tách được bao nhiêu do chuyển động, lỗi đỉnh, họa âm hoặc ngưỡng baseline; không kết luận nguyên nhân chỉ từ tên lý do.

Kết quả chi tiết: `run.json`, `verification.json` và `review-S2.png` trong thư mục lượt chạy. Biểu đồ S2 chỉ là đoạn xem thử có ghi rõ HR thử nghiệm; chưa thay notebook đánh giá đại diện tất cả người/nhãn.

Kiểm thử: **39 tests AI đạt**, gồm 24 tests kiểm kê/chuẩn hóa WESAD và 15 tests sẵn có. Có 14 cảnh báo deprecation từ dependency Matplotlib/Pyparsing; không có test lỗi. `pip check` và `git diff --check` đạt. Tests sóng giả xác minh logic cơ bản, không chứng minh độ chính xác trên người.

```powershell
Push-Location ai
..\.venv\Scripts\python.exe -m pytest -q
Pop-Location
```

## 7. File code chính để đọc

- [wesad.py](../../ai/src/preprocessing/wesad.py): đổi đơn vị, giữ timeline/nhãn, tính HR ứng viên, xuất tín hiệu và metadata.
- [prepare_wesad.py](../../scripts/prepare_wesad.py): kiểm hash, đọc từng người, chạy chuyển đổi và ghi trạng thái lượt chạy.
- [test_wesad_preprocessing.py](../../ai/tests/test_wesad_preprocessing.py): kiểm đơn vị, thiếu dữ liệu, ranh giới nhãn, tính nhân quả, reset sau gap và xuất file.

Chọn SciPy `1.15.3` để pin phép xử lý tương thích NumPy `2.2.1`/Python 3.12 hiện tại, không tự nâng các dependency khác. Tài liệu API chính thức: [Butterworth](https://docs.scipy.org/doc/scipy-1.15.3/reference/generated/scipy.signal.butter.html), [SOS một chiều](https://docs.scipy.org/doc/scipy-1.15.3/reference/generated/scipy.signal.sosfilt.html), [tìm đỉnh](https://docs.scipy.org/doc/scipy-1.15.3/reference/generated/scipy.signal.find_peaks.html). Các API này cung cấp phép xử lý, không bảo đảm baseline HR của dự án đạt độ chính xác sinh lý.

**Ưu tiên tiếp theo:** notebook kiểm tra BVP/HR trên các đoạn đại diện và đối chiếu tham chiếu ECG ngực được kiểm tra riêng, trước khi chốt phương pháp tính HR để tạo feature. ECG chỉ phục vụ đánh giá, không làm đầu vào model thiết bị. Không vội loại hàng thiếu HR rồi train model đủ 5 biến. Khi HR đạt yêu cầu kiểm chứng mới chốt feature/đánh giá theo người. Chưa cho phép coi model WESAD sẵn sàng chạy trên Grove GSR ADC; chênh đơn vị/vị trí đo vẫn cần giải quyết riêng.
