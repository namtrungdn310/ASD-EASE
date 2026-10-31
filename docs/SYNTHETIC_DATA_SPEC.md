# Đặc tả dữ liệu giả lập đa cảm biến

## Mục đích và giới hạn

Bộ sinh giúp thử nhận dữ liệu, xử lý, chất lượng, mức nền, đặc trưng và tích hợp trước khi có bộ dữ liệu phần cứng. Đây là xấp xỉ kỹ thuật có cấu hình: không phải dữ liệu sinh lý ASD thật, bộ mô phỏng PPG/EDA được chứng nhận hay bằng chứng nhận diện lo âu.

## Thời gian và đơn vị

Mỗi phiên dùng chung các biến giả lập về hoạt động, kích hoạt tự chủ, tiếp xúc, chuyển động lặp và thời gian. Các cảm biến lấy mẫu những biến đó ở tốc độ riêng: mặc định PPG100/IMU50/GSR20/telemetry1 Hz, chỉ là cấu hình phát triển.

Giữ thứ tự mẫu. Jitter có timestamp riêng trong file; batch raw API dùng khoảng thời gian đều theo rate và null cho mẫu thiếu, không bảo toàn jitter tuỳ ý.

- PPG red/IR: sóng gần đúng có đỉnh mạch, thành phần nhỏ phụ, trôi nền, nhiễu và ảnh hưởng tiếp xúc/chuyển động. Đơn vị số đếm0–262143, không đơn vị quang học/lâm sàng.
- HR: mức nghỉ cá nhân, biến thiên chậm và ảnh hưởng hoạt động; dùng cùng pha PPG, không là chuỗi ngẫu nhiên độc lập.
- GSR: ADC giả0–4095 với mức nền, trôi chậm, đáp ứng có độ trễ, nhiễu và mất tiếp xúc; không phải µS đã hiệu chuẩn hoặc thước đo lo âu.
- IMU: gia tốc g và vận tốc góc degrees/s, có trọng lực, đổi hướng, chuyển động thường/lặp và nhiễu. Chuyển động lặp không mặc định là căng thẳng.

Chuyển động ảnh hưởng chất lượng PPG; đáp ứng GSR có thời điểm/độ trễ riêng. artifact_frequency gần đúng là số lần bắt đầu nhiễu mỗi giây; dropout là xác suất theo mẫu. Các kịch bản thường/kích hoạt cao có vùng chồng lấp có chủ đích.

## Kịch bản

| Mã giữ nguyên | Ý nghĩa |
|---|---|
| NORMAL_REST | Hoạt động thấp, dao động tự nhiên |
| NORMAL_ACTIVITY | Chuyển động thường, HR có thể tăng; thử cảnh báo sai |
| REPETITIVE_MOVEMENT | Cổ tay lặp theo chu kỳ, không ép GSR tăng; không mô hình stimming đã xác nhận |
| ELEVATED_AROUSAL_PROXY | Xu hướng HR/GSR có tương quan không hoàn hảo, không phải lo âu đã xác nhận |
| POOR_SIGNAL | Tiếp xúc thấp, nhiễu/mất mẫu tăng để thử kiểm tra chất lượng |
| TRANSITION | Thay đổi từ từ, không nhảy đồng loạt |
| DISCONNECT_RECONNECT | Mốc thu liên tục trong lúc tạm dừng đường gửi |

## Cá nhân, nhãn và nguồn

Hồ sơ SYN-P### thay đổi HR nghỉ/dao động, GSR nền/độ đáp ứng, chuyển động, tiếp xúc, nhiễu và độ trễ. Mỗi lần đo có seed riêng; đổi tên cùng tín hiệu không tạo phiên độc lập.

Nhãn kịch bản khác trạng thái triển khai. synthetic/labeling.py chứa ánh xạ thử nghiệm; chất lượng thấp có thể chuyển UNCERTAIN. Không dùng ID, kịch bản, seed, điểm/trạng thái sinh ra làm đầu vào mô hình. Không tạo nhãn bằng đúng ngưỡng sau đó dùng làm đối chứng.

File JSON có metadata, streams, telemetry. Bản mô tả giữ data_origin=SYNTHETIC, phiên bản/cấu hình bộ sinh, seed, schema, người/phiên, kịch bản, tốc độ, thời lượng, giờ UTC tạo và giới hạn sử dụng. File sinh ở ai/data/synthetic, không đưa dữ liệu người tham gia lên Git.

## Tái lập và kiểm tra

Cùng cấu hình/hồ sơ/seed tạo lại cùng mảng tín hiệu; created_at không cần giống từng byte. Kiểm tra timestamp, số mẫu, phạm vi, schema, mất mẫu, chất lượng theo chuyển động, khác biệt phiên, chuyển tiếp, lưu/tải và giao diện xử lý. Biểu đồ chỉ để quan sát, không chứng nhận sinh lý.

## Chạy thử

Các lệnh dưới dùng PowerShell từ thư mục gốc, sau khi cài dependencies:

```powershell
$env:PYTHONPATH="ai"
python -m simulator.mock_device --scenario repetitive_movement --duration 30 --save
python -m simulator.mock_device --generate-dataset --duration 30
python -m simulator.mock_device --replay ai/data/synthetic/raw/SYN-SESSION001.json --send-raw --speed 5
python -m pytest ai/tests
```

Trong Docker, dùng tiền tố docker compose --profile ai run --rm ai. Thử huấn luyện bằng giả lập thuộc giai đoạn ML sau; mô hình phải ghi SYNTHETIC_ONLY và không tự được chọn triển khai thật.
