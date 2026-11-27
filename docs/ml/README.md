# Chuẩn bị machine learning

Thực hiện từng bước. Bảng này theo dõi công việc ML hiện tại, không thay bảng phase hoặc kế hoạch nhánh tích hợp.

| Bước | Nội dung | Trạng thái | Kết quả |
|---|---|---|---|
| 1 | Chốt cấu trúc dữ liệu ML | Hoàn tất đặc tả | [Đầu vào, nhãn và cách lưu](01-ML-DATA-CONTRACT.md) |
| 2 | Kiểm tra WESAD và raw thiết bị hiện có | Hoàn tất kiểm kê | [Báo cáo dữ liệu, đơn vị và phần còn thiếu](02-DATA-AUDIT.md) |
| 3 | Bộ đọc/chuẩn hóa và kiểm tra dataset | Hoàn tất chuyển đổi; HR chưa được chấp nhận cuối cùng | [15 người đã xuất, HR thử nghiệm và giới hạn](03-WESAD-PREPARATION.md) |
| 4 | Đối chiếu HR & phương pháp công bố | Đã xong 4A đối chiếu ECG và 4B đối chiếu MSPTD công bố | [Đối chiếu ECG](04-HR-ECG-REVIEW.md), [Benchmark phương pháp công bố](05-PPG-BENCHMARK.md) |
| 5 | Chốt Feature & Huấn luyện baseline | Hoàn tất huấn luyện LOSO 15 đối tượng | [Tập 36 đặc trưng & Báo cáo baseline (Tuned LR Acc 90.69%, Stress F1 84.66%, 14.285 PPS)](06-BASELINE-MODELS.md) |

**Dataset làm việc hiện tại: WESAD**, theo quyết định ngày 2026-11-16. Bắt đầu với stress/không stress, dùng tín hiệu cổ tay. Xem [nguồn, cách tải và đối chiếu thiết bị](../../ai/data/external/wesad/README.md). Không gán các mức nhẹ/vừa/nặng vì WESAD không cung cấp nhãn đó.

EmpathicSchool tạm chờ quyền truy cập, chưa tải hoặc kiểm định file. Chỉ xem xét bổ sung sau khi được cấp quyền và kiểm tra nhãn thực. Xem [trạng thái](../../ai/data/external/empathicschool/README.md).

Đã tải WESAD, đối chiếu checksum nguồn, kiểm tra CRC toàn ZIP, đọc README và kiểm kê `.pkl` của đủ 15 người. Tổng 24,13 giờ bản ghi, khoảng 9,21 giờ nhãn dùng cho bài nhị phân trước lọc/cắt cửa sổ. Đã chuẩn hóa từng kênh, tính độ lớn gia tốc và HR thử nghiệm; chưa có HR được kiểm chứng sai số hoặc model stress.

Raw thiết bị hiện tại chưa ghi tự động đầy đủ: backend đang chạy có 0 raw batch và 0 annotation tại thời điểm kiểm kê bước 2. Trace PPG cũ phục vụ chẩn đoán, chưa phải bộ dữ liệu stress có nhãn.

**Đã hoàn tất đối chiếu HR (Bước 4A & 4B):**
- Bước 4A: Baseline nhân quả đạt MAE gộp 1,76 bpm nhưng độ phủ Stress chỉ 16,40%.
- Bước 4B: Đối chiếu MSPTDfast v2 công bố trên 15 người; ở các cửa sổ chung đạt MAE tương đồng (1,79 vs 1,76 bpm). MSPTD Gated nâng độ phủ Stress lên 61,73% (và Baseline lên 85,58%).
- Đã chỉ ra nguyên nhân sai lệch trong Stress là do nhiễu động cổ tay (ACC tăng mạnh) và hiện tượng nửa nhịp (half-rate do co mạch). Chốt chiến lược feature HR đa tầng (`hr_gated` + `hr_is_valid`) phối hợp với EDA/ACC có độ phủ 100%. Không sửa/nạp firmware ở các bước này.

**Đã hoàn tất Bước 5 (Huấn luyện Baseline & Đánh giá theo người):**
- Đã trích xuất 3.040 cửa sổ 60s trên 15 đối tượng với 36 đặc trưng đa cảm biến (14 EDA, 13 ACC, 9 HR & Validity).
- Đánh giá bằng Leave-One-Subject-Out (LOSO) 15 fold: Logistic Regression đạt Accuracy **89,74%**, Macro F1 **87,95%**, Stress F1 **83,30%**; Random Forest đạt Accuracy **84,08%**, Stress F1 **73,89%**.
- Thực nghiệm cắt bỏ (Ablation study) chứng minh việc bổ sung HR giúp tăng vọt Stress F1 từ 62,97% lên 73,89% (+10,92%).
- Điểm chặn cần xử lý tiếp theo trước khi chạy trên thiết bị thật: hiệu chuẩn hoặc chuẩn hóa chuyển đổi giữa ADC Grove và µS của WESAD. Firmware ESP32 giữ nguyên toàn bộ.
