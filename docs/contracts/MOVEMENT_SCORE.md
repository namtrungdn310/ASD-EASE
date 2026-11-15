# Điểm chuyển động từ MPU6050

Ngày2026-11-05. Firmware0.2.1 bổ sung thuật toán **motion-rms-v1** cho `movement.score` của telemetry1.0. Đây là chỉ số chuyển động kỹ thuật từ cảm biến, không phải dự đoán AI hoặc xác suất trạng thái. Không đổi schema/topic, không gán điểm này vào prediction.

Theo yêu cầu tiếp theo, firmware0.3.0 gửi telemetry1.1 và Dashboard hiển thị riêng [gia tốc/tốc độ xoay](IMU_TELEMETRY_V1_1.md). Điểm tổng hợp vẫn có trong payload, không còn thay thế hai nhóm trên giao diện. Bản0.2.1 mới kiểm thử phần mềm, chưa được xác nhận nạp board.

## Dữ liệu và công thức

Dùng từng lần đọc MPU6050 thành công ở nhịp mục tiêu50 Hz: ba trục gia tốc trước EMA, đơn vị m/s², và ba trục con quay trước EMA, đơn vị degrees/s. Giữ phép đổi đơn vị/dấu trục hiện có trong driver.

Với mỗi mẫu, tính:

```text
A = sqrt(ax² + ay² + az²)
W = sqrt(gx² + gy² + gz²)
a = max(0, abs(A - 9.80665) - 0.15) / 2.0
w = max(0, W - 3.0) / 90.0
energy = a² + w²
r = sqrt(mean(energy của 50 mẫu gần nhất))
score = r / (1 + r)
```

- Trừ1g để thiết bị nằm yên không tự có điểm cao vì trọng lực. Chuẩn vector không phụ thuộc hướng đặt tĩnh; con quay bổ sung chuyển động xoay khi độ lớn gia tốc gần1g.
- Vùng bỏ qua0.15 m/s² và3 degrees/s giảm tác động nhiễu/offset nhỏ. Mốc2 m/s² và90 degrees/s là tham số phát triển để quy đổi cường độ, **chưa phải ngưỡng đã hiệu chuẩn trên người**.
- Nếu r=0 thì score=0; r=1 cho0.5; cường độ tăng thì điểm tiến gần1. Không lấy gia tốc m/s² gán thẳng vào điểm0–1.
- Cửa sổ50 mẫu ở50 Hz tương ứng khoảng1 giây. Cộng/trừ năng lượng trên vòng đệm hữu hạn, không giữ mọi mẫu của phiên và không phụ thuộc nhịp MQTT1 Hz. JSON làm tròn đến3 chữ số thập phân.

Đây là phép đo cường độ tương đối: chưa phát hiện hành vi lặp lại, chưa phân biệt nguyên nhân rung/xoay, không tương đương biến motion giả lập hoặc đặc trưng mô hình đã huấn luyện. Di chuyển đều không có gia tốc/không xoay có thể cho điểm thấp. Cần thử thiết bị giữ yên, xoay và rung trước khi dùng số này làm đặc trưng nghiên cứu.

## Hợp lệ và dữ liệu thiếu

- Chưa đủ50 mẫu thì null. Khi đủ, khoảng thời gian từ mẫu đầu tới cuối phải trong800..1200 ms (danh định980 ms).
- Mẫu trùng timestamp không được thêm vào cửa sổ. Đồng hồ đi lùi hoặc khoảng trống hơn100 ms làm khởi động lại cửa sổ.
- Lần đọc I2C lỗi xoá cửa sổ. NaN/Infinity hoặc trục sát thang bão hoà cũng xoá cửa sổ; cần tích luỹ đủ mẫu mới để có điểm trở lại.
- Thang driver hiện ±2g và ±250 degrees/s: từ chối khi bất kỳ trục gia tốc có trị tuyệt đối>=19.60 m/s² hoặc con quay>=249.9 degrees/s. Nếu đổi thang MPU phải đổi quy tắc này và kiểm thử kèm theo.
- Serializer chỉ gửi khi driver VALID, có timestamp mẫu thật và tuổi mẫu IMU không quá1000 ms, kể cả thời gian chờ snapshot trong task mạng. Ngoài ra gửi null, không0 thay lỗi.
- Điểm không đổi `signal_quality` (vẫn0 khi chưa có bộ ước lượng) hoặc `model_version=none`, prediction probability=null. Có chuyển động không tự trở thành ATTENTION.

## Code và kiểm chứng

- `include/processing/movement_score.h`: cửa sổ và công thức, dùng chung trên ESP và harness native C++.
- `MPU6050Sensor.*`: đưa mẫu mới thành công vào bộ tính, reset khi lỗi.
- `telemetry_serializer.cpp`: chụp điểm/validity cùng tuổi mẫu.
- `session_protocol.cpp`: kiểm tra điểm, freshness và tạo JSON.
- `scripts/check_firmware_protocol.py`: native tests cho đứng yên/hướng đặt, xoay/gia tốc, cường độ, quên cửa sổ cũ, lỗi/bão hoà/thiếu mẫu, cache/đồng hồ, nhịp sai và serializer. Gói C++ được kiểm tra bằng schema runtime backend.

Code/build/tests không thay kiểm tra ESP thật. Cần nạp0.2.1, xác nhận firmware_version trên Dashboard, rồi so sánh điểm khi giữ yên và khi xoay/rung nhẹ. Không tháo cảm biến đang cấp nguồn để thử lỗi.
