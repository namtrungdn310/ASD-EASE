# Bước 2 — Kiểm tra dữ liệu WESAD và dữ liệu thiết bị

Ngày kiểm tra: 2026-11-16. Nền code: `8a81f88`; nhánh làm việc `chore/ai-dataset-storage`.

## Kết luận và phạm vi

Có thể tiếp tục xây quy trình xử lý/train thử với WESAD. Dữ liệu thiết bị hiện tại chưa phải bộ raw đồng bộ có nhãn để train/test stress hoặc xác nhận khả năng áp dụng model WESAD.

Bước này chỉ đọc dataset, mã nguồn và dữ liệu lưu hiện có. Không thay thuật toán HR, không nạp firmware, không thu lượt đo mới, không tạo nhãn stress bằng số HR/GSR và không train model.

## 1. Cách kiểm tra WESAD

Nguồn và checksum: [README WESAD](../../ai/data/external/wesad/README.md). Công cụ: [audit_wesad.py](../../scripts/audit_wesad.py).

```powershell
.\.venv\Scripts\python.exe scripts/audit_wesad.py
```

- Kiểm tra SHA-256 đúng bản ZIP chính thức đã tải trước khi mở pickle.
- Đọc từng người trực tiếp trong ZIP; không giải nén thêm khoảng 17,58 GB hoặc nạp 15 người cùng lúc vào RAM.
- Kiểm tra ID, cấu trúc, số cột, tần số danh định, độ dài, NaN/Infinity, độ biến thiên và giá trị 0.
- Đếm mã nhãn, giữ các khoảng `[start, end)` và tổng thời gian của mỗi mã; không đổi nhãn chuyển tiếp thành không stress.
- Đối chiếu chuỗi 128 mẫu ACC đầu trong `.pkl` với `ACC.csv` E4 gốc để xác minh scale, không đoán từ biên độ.
- Báo số mẫu chạm biên ACC và EDA âm để xem xét, không tự loại mẫu hoặc chọn ngưỡng theo nhãn.

Báo cáo chi tiết lưu local tại `ai/data/interim/wesad/audit-v1.json`, được `.gitignore` bảo vệ. Các kiểm tra này chưa phải bộ đánh giá chất lượng sinh lý đầy đủ của bước 3.

### Kết quả WESAD

Đã kiểm tra đủ **15/15 người**. Công cụ kết thúc với exit code 0, không có lỗi cấu trúc, NaN/Infinity, kênh hằng trên toàn phiên hoặc chênh độ dài vượt dung sai một mẫu.

| Nội dung | Kết quả |
|---|---:|
| Toàn bộ thời gian bản ghi, gồm chuyển tiếp/nhãn bỏ qua | 86.868 giây = 24,13 giờ |
| Thời lượng mỗi người | 5.223–7.071 giây |
| BVP cổ tay, 64 Hz | 5.559.552 mẫu |
| ACC cổ tay, 32 Hz | 2.779.776 mẫu vector ba trục |
| EDA cổ tay, 4 Hz | 347.472 mẫu |
| TEMP cổ tay, 4 Hz — không đưa vào model đầu | 347.472 mẫu |
| ACC `.pkl` khớp chuỗi 128 mẫu với E4 raw | 15/15 người |
| NaN/Infinity trong các kênh cổ tay đã đọc | 0 |
| Mẫu EDA âm | 0 |

Các kênh có cùng thời lượng suy từ số mẫu/tần số. Đây không phải phép đo độc lập tốc độ thật hoặc bằng chứng không mất gói; `.pkl` không cung cấp timestamp riêng từng mẫu để kiểm tra điều đó.

**Scale ACC đã xác minh:** `.pkl` vẫn là 1/64 g. Đổi bằng `ACC / 64 * 9.80665`, sau đó mới tính độ lớn m/s². Median độ lớn sau chia 64 nằm khoảng 0,982–1,011 g theo người, phù hợp với tín hiệu gồm trọng lực. Không chia 64 thêm lần nữa khi dữ liệu đã chuyển sang g/m/s².

Có **599 mẫu vector ACC chạm ít nhất một biên -128/127** trên toàn dữ liệu. Đây là dấu hiệu cần kiểm tra đoạn tín hiệu/giới hạn đo; chưa tự loại chúng và chưa coi mọi mẫu chạm biên đều hỏng.

| Nhãn dùng trong bài đầu | Thời lượng trước lọc chất lượng/cắt cửa sổ |
|---|---:|
| Baseline (1) | 4,892 giờ |
| Stress (2) | 2,768 giờ |
| Amusement (3) | 1,549 giờ |
| `NON_STRESS` = baseline + amusement | 6,441 giờ |
| Tổng dùng cho bài nhị phân | 9,209 giờ |

Cả 15 người đều có mã 1/2/3. Mã 0/4/5/6/7 có xuất hiện và được giữ riêng trong báo cáo; không đưa vào bài nhị phân đã chốt. Những số trên chưa phải số cửa sổ train hoặc thời lượng còn lại sau kiểm tra chất lượng; chưa có phép chia train/validation/test.

Không có HR độc lập trong `signal.wrist` của cả 15 người. Cần tính HR từ BVP ở bước tiếp theo. Kiểm tra này chưa đánh giá BVP có đủ rõ nhịp trong từng cửa sổ hay chưa.

## 2. Dữ liệu thiết bị hiện có

Đã đọc mã nguồn và kiểm tra thư mục local cùng storage của **backend ASD-EASE đang chạy trên laptop**. Không coi thư mục `backend/storage/raw` trên host là toàn bộ dữ liệu, vì Compose sử dụng volume riêng `/app/storage` trong container.

| Nguồn | Bằng chứng tại thời điểm kiểm tra | Dùng được cho việc gì |
|---|---|---|
| Raw batch trong backend đang chạy | 0 file JSONL, 0 batch | Chưa có dữ liệu từ đường raw HTTP |
| Nhãn trong DB đang chạy | 0 annotation | Chưa có nhãn stress tự thu |
| Phiên thiết bị | 74 ABORTED, 1 RECORDING; chưa phiên nào `recording_complete=true` | Trạng thái phiên, không chứng minh đã ghi đủ raw |
| Event trong DB | 88.580 bản ghi trạng thái/xác suất/thời gian | Không chứa toàn bộ HR/GSR/IMU để thay dữ liệu ML |
| PPG trace local | 54 file có tên timestamp, 112.933 hàng RED/IR | Kiểm tra thu mẫu và thuật toán HR; chưa có nhãn stress |
| PPG trace kèm motion | 2 lượt có file motion | Đối chiếu nhiễu PPG/IMU; nhiều hàng dùng chung timestamp IMU |
| WS capture còn lưu đủ frame | 7 file, tổng 205 hàng frame | Kiểm tra snapshot/luồng hiển thị; không phải raw đầy đủ |

Số file/hàng là kiểm kê phạm vi trên, không phải số mẫu độc lập hoặc thời lượng nghiên cứu độc lập. Một số thử nghiệm/summary có thể mô tả cùng lượt; không tự cộng chúng thành dữ liệu mới. Chưa kiểm tra các volume cũ/ngừng chạy hoặc máy Tân.

54 lượt PPG không có timestamp lùi/trùng trong CSV đã kiểm tra. Tuy nhiên, 33 lượt không có trường `capture_status` theo định dạng metadata mới, 21 lượt ghi `complete`; thiếu trường không đồng nghĩa lượt hỏng hoặc hoàn chỉnh.

Hai lượt mới nhất:

| File PPG local | Mẫu PPG | Khoảng thời gian mẫu | Motion / timestamp IMU phân biệt | Giới hạn |
|---|---:|---:|---:|---|
| `ppg-20261114-230300-6e429d.csv` | 2.251 | 44,978 giây | 2.251 / 2.194 | Có một khoảng PPG 40 ms |
| `ppg-20261115-001935-876672.csv` | 2.250 | 44,966 giây | 2.250 / 2.183 | Có một khoảng PPG 40 ms |

Khoảng 40 ms cần giữ để phân tích gián đoạn/jitter, không tự coi CSV là lịch 20 ms hoàn hảo hoặc kết luận chính xác số mẫu mất chỉ từ một khoảng. Số timestamp IMU phân biệt cũng chưa chứng minh đủ mọi mẫu IMU độc lập.

Các file motion ghi gia tốc bằng g, tốc độ xoay theo thang `90 degrees/s`; khác telemetry m/s² và °/s. Không ghép theo hàng rồi coi mọi hàng là một mẫu IMU mới. File trace hiện không có GSR raw đồng bộ.

Chẩn đoán local được lưu tại `backend/storage/local/ml-device-data-audit-20261116.json`; không commit dữ liệu đo hoặc thông tin cá nhân.

Các con số trong bảng DB là snapshot lúc kiểm tra; hệ thống đang chạy có thể tiếp tục cập nhật sau đó.

## 3. Vì sao Dashboard chạy nhưng chưa có bộ dữ liệu ML

- [Telemetry service](../../backend/app/services/telemetry_service.py) cập nhật thiết bị/cursor, ghi event và broadcast WebSocket; không lưu lịch sử đầy đủ của mọi kênh cảm biến.
- [Mô hình DB](../../backend/app/db/models.py) không có bảng chứa đầy đủ chuỗi RED/IR, IMU và GSR.
- [Raw API](../../backend/app/api/v1/raw_data.py) và [storage](../../backend/app/services/raw_storage.py) có đường append JSONL. Chưa có cơ chế lưu bền/chống trùng/đối chiếu đầy đủ theo kế hoạch nhánh 6.
- [Firmware interfaces](../../ai/edge_firmware/include/interfaces.h): `RawBatchClient` còn `NOT_IMPLEMENTED`. [Stop summary](../../ai/edge_firmware/src/communication/session_protocol.cpp) khai `raw_recording_enabled=false`.
- [Công cụ trace PPG](../../scripts/capture_ppg_trace.py) chạy theo yêu cầu qua USB `p/q` để chẩn đoán; không thay đường raw HTTP tự động của hệ thống.
- Các raw batch giả lập/test có thể tồn tại ở thư mục khác, nhưng không phải phép đo DEVICE có nhãn.

Mã phiên và trạng thái RECORDING chưa đồng nghĩa đã thu đủ dữ liệu để xuất/train. Đường nét đứt HR trên frontend vẫn chỉ để hiển thị, không đưa vào dataset như số đo mới.

## 4. Những phần chưa tương thích với model triển khai

| Thành phần | Quyết định |
|---|---|
| HR | WESAD cần tính từ BVP cổ tay; không dùng HR.csv bị README yêu cầu bỏ qua hoặc ECG ngực làm feature thay HR cổ tay |
| Điện da | WESAD µS, thiết bị ADC chưa hiệu chuẩn; chưa có phép đổi được kiểm chứng. Min-max/z-score không tự khắc phục khác biệt phần cứng/vị trí đo |
| Gia tốc | Đổi scale và thống nhất đơn vị trước khi tính độ lớn; vẫn cần xét khác hướng đeo và xử lý trước/sau EMA |
| Tần số | Ghép theo thời gian; BVP/EDA/ACC và nhãn có tần số riêng, không ép tất cả về 1 Hz theo MQTT |
| Nhãn | WESAD cung cấp điều kiện thí nghiệm; bản tự thu chưa có nhãn stress độc lập |
| Chất lượng | Không có NaN không có nghĩa PPG không nhiễu; chưa có bằng chứng cho điểm chất lượng 100% của dataset |

## 5. Bước tiếp theo

1. Hoàn thiện bộ đọc/chuẩn hóa WESAD: tách đúng thời gian và nhãn, giữ đơn vị/giá trị thiếu, không cắt cửa sổ qua ranh giới nhãn.
2. Chọn và kiểm tra phương pháp tính HR từ BVP, có timestamp kết quả và thời gian cần khởi tạo. Chưa đưa HRV vào feature mặc định.
3. Chốt cửa sổ/hop và feature trên train/validation theo người; không dùng test để chỉnh bộ lọc/ngưỡng.
4. Muốn đánh giá trên phần cứng thật: hoàn thành [nhánh 6 lưu raw](../integration/06-backend-raw-ingestion.md) và [nhánh 7 gửi raw](../integration/07-firmware-raw-batching.md), sau đó mới thu dữ liệu có nhãn độc lập để đánh giá khả năng chuyển model sang thiết bị.

Có thể tiến hành phần WESAD trước trong lúc hoàn thiện đường raw thiết bị. Chưa được gọi model train trên WESAD là đã nghiệm thu trên MAX30102/Grove GSR/MPU6050.

## 6. Kiểm chứng công cụ

```powershell
.\.venv\Scripts\python.exe -m pytest ai/tests/test_wesad_audit.py -q
git diff --check
```

Kết quả: 8 tests đạt; kiểm tra khoảng nhãn nửa mở, giữ mã chuyển tiếp/bỏ qua, từ chối mã lạ/nhãn không nguyên, phân biệt thiếu với số 0, kiểm tra chuỗi chứng minh đơn vị ACC và số cột sai. Fixture chỉ kiểm tra logic công cụ; bằng chứng dataset là lượt chạy thật trên ZIP đủ 15 người, không phải fixture.
