# Ánh xạ driver sang dữ liệu gửi

Đọc code tại dev d80cc0e, ngày2026-10-31. **Đã đối chiếu mã nguồn, chưa kiểm chứng board.** Không đổi chân hoặc driver từ tài liệu này.

| Dữ liệu trong code | Cách dùng | Lưu ý |
|---|---|---|
| MAX30102Data.heartRate | hr_bpm khi valid, đúng dải, còn mới; còn lại null | Đã qua trung vị/EMA, không phải sóng PPG thô; 05 cần tuổi từ nhịp thật |
| redValue/irValue | Snapshot để chẩn đoán | read() lấy FIFO nhưng chỉ trả cặp cuối; 07 phải lấy từng cặp/timing, không nhân bản snapshot |
| Cặp red/IR trong FIFO | ppg.red/ir | Sau trung bình trên chip2, trước bộ lọc phần mềm; chip100 → danh định50 Hz, cần đo số mẫu thật |
| rawSpO2/spO2 | Chỉ debug | Không thêm vào telemetry1.0 |
| GSRData.rawADC | gsr.raw và gsr.adc | Trung bình8 lần analogRead, làm tròn nguyên, trước EMA |
| percentChange | gsr.delta=percentChange/100 | valid, còn mới, baselineConductance>0.05; không thay bằng deltaConductance_uS |
| rawConductance_uS | Không đưa vào raw ADC1.0 | Code còn dùng điện áp đã lọc và giả thiết mạch; tên raw không chứng minh chưa xử lý/đã hiệu chuẩn |
| rawAx/rawAy/rawAz | Chia9.80665 để raw imu.a* có đơn vị g | Driver đã đảo Y/Z, không đảo lại |
| rawGx_deg/rawGy_deg/rawGz_deg | Raw imu.g*, degrees/s | Đã đảo Y/Z, không dùng rawGx rad/s trực tiếp |
| ax/ay/az và gx* sau lọc | Chẩn đoán/tóm tắt khi có định nghĩa | Không thay mảng raw bằng số EMA |
| accelMagnitude | Không đưa thẳng vào movement.score | m/s² khác score0..1; chưa thuật toán thì null |
| VALID/READY | Trạng thái driver | Chưa mô hình: probability=null, CALIBRATING/UNCERTAIN |

## Cấu hình và giới hạn

board_config.h hiện: PPG SDA8/SCL9, MPU SDA10/SCL11, GSR ADC7 (không còn4), loop10 ms, IMU50 Hz, GSR20 Hz, PPG100/average2 → danh định50 Hz.

platformio.ini dùng Arduino với profile esp32-s3-devkitc-1/flash4 MB. Đó là cấu hình build, không nhận dạng board/PSRAM thực.

MAX30102Sensor.cpp giữ mảng FIFO cục bộ và ước lượng sampleTime từ now/period; đầu ra chưa đủ cờ mẫu mới/bộ đếm/timestamp. IMU đã đổi đơn vị và dấu trục; GSR có giả thiết mạch chưa hiệu chuẩn. Lịch gọi millis() không chứng minh rate/jitter/đồng bộ.

## Bằng chứng còn cần

| Việc | Người/nhánh | Cần cung cấp | Trạng thái |
|---|---|---|---|
| Wiring, GPIO7, board/flash/PSRAM | Tân trước nghiệm thu05 | Ảnh/log nhận dạng và sơ đồ dây được xác nhận | PENDING |
| Rate/loss FIFO PPG | Tân+IT trước07 | Cấu hình, số mẫu theo thời gian nhiều phút và bộ đếm mất | PENDING |
| Rate/cùng epoch/jitter IMU/GSR | Tân+IT/07 | Log timestamp, số mẫu và vị trí null | PENDING |
| Tuổi HR, mạch/mức nền GSR | Tân+IT/05 | Mốc cập nhật, thử lỗi/ngắt/hiệu chuẩn | PENDING |
| RAM/stack khi MQTT+HTTP/raw | IT+Tân/05/07 | Bộ nhớ đỉnh, byte hàng đợi và ảnh hưởng lấy mẫu; không giả PSRAM | PENDING |

Đây là cổng nghiệm thu thật của05/07, không phải lý do bịa số đo để hoàn tất tài liệu03. Backend04 được thử bằng SYNTHETIC. Nếu profile thực không đáp ứng clock1.0, đổi đặc tả/phiên bản trước khi nhận bản ghi thật.
