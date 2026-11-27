# Bước 4A — Notebook đối chiếu HR với ECG

Ngày: 2026-11-17. Đây là kiểm tra kỹ thuật HR trước bước tạo feature/train stress.

## Đã triển khai

- [Notebook tiếng Việt](../../ai/notebooks/02-wesad-hr-ecg-review.ipynb): gồm giải thích ngắn gọn, bảng độ phủ/sai lệch theo nhãn/người, sóng ECG/QRS/BVP và HR trên recording.
- [Công cụ chạy đủ người](../../scripts/compare_wesad_hr.py): kiểm checksum archive/CSV, đọc từng người, tính đối chiếu và xuất báo cáo local.
- [Logic đánh giá](../../ai/src/evaluation/wesad_hr.py): nguồn ECG, ghép đúng cửa sổ, tính độ phủ/MAE/bias/P90, giữ riêng trường hợp không so được.
- [Tests](../../ai/tests/test_wesad_hr_comparison.py): cửa sổ nửa mở, gap/biên, số thiếu, mẫu số độ phủ, ghép sai thời gian và sai lệch theo nhãn.

## Mở và chạy trong VS Code

```powershell
.\.venv\Scripts\python.exe -m pip install -r ai/requirements-notebooks.txt
```

Mở notebook, chọn kernel Python của `.venv`, chạy từng cell từ trên xuống. Notebook đọc kết quả đã tính; không cần ESP, không nạp firmware. Đổi `SUBJECT="S2"` tại cell xem sóng để kiểm tra người khác.

Nếu cần tái hiện từ dataset gốc:

```powershell
.\.venv\Scripts\python.exe scripts/compare_wesad_hr.py --output ai/data/interim/wesad/hr-ecg-review-v1-repeat
```

Thư mục output phải mới. Khi dùng output khác, sửa biến `REVIEW` trong notebook cho khớp. Công cụ không ghi đè dữ liệu nguồn hay lượt trước.

## Nguồn đối chiếu và cách tính

ECG ngực đồng bộ trong `.pkl` có tần số danh định 700 Hz. Dùng XQRS của WFDB 4.2.0 với cấu hình mặc định, `learn=True`; ghi nhận bộ phát hiện có học được khởi tạo hay dùng giá trị mặc định. Tài liệu/mã nguồn chính thức: [WFDB QRS](https://github.com/MIT-LCP/wfdb-python/blob/v4.2.0/wfdb/processing/qrs.py), [WFDB](https://wfdb.readthedocs.io/en/v4.1.1/processing.html).

XQRS có lọc hai chiều và backsearch: **chỉ là nguồn đối chiếu offline**, không phải thuật toán realtime hoặc đầu vào model thiết bị. Nhãn stress và HR PPG không được dùng để tìm QRS.

Mỗi giá trị ECG được tổng hợp trên cùng cửa sổ `[start_ms,end_ms)` 10 giây của PPG. Cần ít nhất 3 khoảng QRS, khoảng RR trong dải phương pháp 30–220 bpm, CV ≤0,25, không qua gap và cách biên đoạn hữu hạn ít nhất 1 giây. HR = 60 / trung vị RR. Các ngưỡng này là cổng kỹ thuật cố định, không phải tiêu chuẩn nhịp tim bình thường hoặc chất lượng y khoa.

Không dịch lag theo người hoặc tối ưu sai lệch, không dùng ECG điền HR PPG bị thiếu. Khoảng QRS/nhãn đều nửa mở; không ghép theo số thứ tự hàng giữa hai tần số khác nhau.

**ECG tự động chưa phải ground truth chuyên gia.** Cổng RR đều chưa chứng minh bộ phát hiện không đếm nhầm nửa/gấp đôi nhịp. Cần xem sóng/đối chiếu bổ sung trước các kết luận độ chính xác. Một vài đoạn sóng nhìn hợp lý không xác nhận toàn bộ ECG đúng.

## Đọc kết quả đúng cách

- MAE chỉ tính trên các cửa sổ có cả HR PPG và ECG được chấp nhận; thiếu HR không thành sai số 0.
- Báo riêng độ phủ ECG và độ phủ PPG trong các cửa sổ ECG dùng được.
- Báo theo baseline/stress/amusement và theo người; không chỉ số gộp. Có MAE gộp theo cửa sổ và trung bình MAE đều theo người.
- Các cửa sổ chồng lấp, không phải các phép đo độc lập. Không lấy số hàng làm cỡ mẫu để khẳng định độ tin cậy thống kê.
- So thêm ứng viên trước cổng PPG chỉ để chẩn đoán, không đưa số bị từ chối vào train hoặc sửa kết quả đã xuất.
- Đoạn xem sóng cố định 30 giây sau đầu khoảng nhãn đầu tiên đủ dài; không chọn theo sai lệch đẹp nhất.

Đã khảo sát đủ dataset trong các bước này. Nếu dùng kết quả để chọn/chỉnh bộ HR, coi đây là phát triển phương pháp, không gọi kết quả hiện tại là test chưa từng xem. Trước so model stress phải thiết lập quy trình theo người, không chia ngẫu nhiên cửa sổ chồng lấp.

## Kết quả thực

Đã chạy đủ **15/15 người**, trạng thái `COMPLETE`. Notebook chạy đủ **14 cell (7 cell code)** bằng kernel `.venv`, không cell lỗi; đã xem ba hình xuất. Bản chạy có outputs nằm local tại `01-wesad-hr-ecg-review.executed.ipynb` trong thư mục kết quả.

Trên các cửa sổ 10 giây nằm hoàn toàn trong nhãn 1/2/3:

| Nhóm | Cửa sổ | ECG qua cổng kỹ thuật | Cặp được so | Độ phủ PPG / ECG dùng được | MAE (bpm) | P90 sai lệch tuyệt đối (bpm) |
|---|---:|---:|---:|---:|---:|---:|
| Baseline | 17.461 | 17.452 | 10.962 | 62,81% | 1,57 | 3,46 |
| Stress | 9.816 | 9.724 | 1.595 | 16,40% | 3,34 | 5,54 |
| Amusement | 5.425 | 5.409 | 3.738 | 69,11% | 1,64 | 3,77 |
| Gộp ba nhóm | 32.702 | 32.585 | 16.295 | 50,01% | 1,76 | 3,71 |

Độ phủ ECG gộp 99,64%. Trung bình MAE đều theo người: 1,79 bpm. Các con số sai lệch đều **có điều kiện trên cặp được so với ECG tự động**, không phải hiệu quả y khoa, điểm test stress hoặc bằng chứng cho các cửa sổ PPG thiếu.

Ứng viên PPG trước cổng kỹ thuật có MAE khoảng 7,04 bpm gộp, 14,06 bpm ở stress, trên tập cặp khác với tập được chấp nhận. Đây là chẩn đoán cho thấy không nên đơn giản bỏ mọi cổng để tăng độ phủ; không phải phép so hai phương pháp trên cùng tập kiểm thử độc lập.

Quan sát hình cố định S2: các đoạn ECG/BVP có mức nhiễu khác nhau; QRS tự động không mặc định nằm đúng đỉnh dương của ECG raw. Cần đánh giá thêm các đoạn khó/nhãn từng nhịp trước khi tin tuyệt đối nguồn đối chiếu. Không chỉnh tham chiếu theo PPG hoặc số HR mong muốn.

**Quyết định:** chưa chốt `bvp-causal-peaks-v1-experimental` làm feature HR cuối. Hạn chế chính là độ phủ thấp/lệch theo nhãn; chưa đủ cơ sở loại hàng thiếu rồi train và gọi tập còn lại đại diện. Bước sau cần đối chiếu phương pháp PPG đã công bố trên cùng quy trình, đồng thời kiểm tra chất lượng tham chiếu, với phân chia người/phạm vi phát triển rõ ràng. Không đổi firmware từ kết quả offline này.

Kiểm chứng: **44 tests AI đạt**, `pip check` và kiểm tra notebook UTF-8/cú pháp đạt. Có 14 cảnh báo deprecation Matplotlib/Pyparsing từ trước; không có test lỗi. Tests kiểm logic, không thay lần chạy dataset thật. Kết quả 15 người và bảng/biểu đồ notebook đã thực sự được chạy, không suy từ fixture.

## Dữ liệu và notebook đã chạy

`ai/data/interim/wesad/hr-ecg-review-v1/` chứa `report.json` và từng thư mục người:

- `comparison.csv`: HR PPG, ECG đối chiếu, nhãn, sai lệch/lý do thiếu từng cửa sổ.
- `ecg_qrs.csv`: chỉ số QRS ở 700 Hz và thời gian tương ứng.
- `summary.json`: độ phủ/sai lệch theo người và nhãn.
- `review_snippets.npz`: đoạn ECG/BVP/QRS cố định phục vụ xem sóng.

Toàn bộ dữ liệu và outputs notebook để trong vùng local bị Git ignore. Notebook nguồn trên Git không có kết quả cell. Không đưa HR ECG vào `normalized-v1/signals` hoặc danh sách feature của model.

**Bước sau:** quyết định phương pháp HR dựa trên độ phủ lẫn sai lệch và chất lượng tham chiếu; chưa train model đủ HR/EDA/ACC nếu còn lệch chọn mẫu hoặc HR thiếu ở stress. Chênh EDA µS với ADC Grove vẫn là điểm chặn áp dụng model trên thiết bị.
