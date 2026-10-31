# Lịch sử thay đổi

## Chưa phát hành

### Bổ sung

- Nhánh04 (2026-11-01): backend MQTT3.1.1/Paho2.1.0, Mosquitto2.0.22 có ACL; nhận telemetry chung HTTP/MQTT, registry/token/cookie, lệnh Start/Stop bền và ACK/nonce/boot, migration SQLite có sao lưu/khôi phục. Có simulator MQTT/HTTP,55 backend tests và bài tích hợp qua broker thật; chưa commit/PR/CI từ xa/merge hoặc firmware05/raw lưu bền06.

- Đặc tả kết nối nhánh03: MQTT, ACK/kết nối lại, thời gian/đơn vị, raw HTTP chống trùng/lưu bền, quyền/giới hạn, ví dụ và công cụ kiểm tra. Đây là thiết kế và mẫu thử, chưa có MQTT runtime/board.
- Kế hoạch10 nhánh tích hợp có điều kiện nghiệm thu và tracker; IT phụ trách đóng gói/mạng/bộ đệm trong mốc này.
- Khung ba mô-đun, tài liệu và25 kế hoạch giai đoạn.
- Khởi tạo Git; sau đó thống nhất dev tích hợp, main ổn định.
- Quy trình hai người, mẫu PR, CODEOWNERS và CI cho dev/main.
- Khung FastAPI/SQLite, file raw, telemetry/WebSocket và dashboard React có nhãn nguồn giả lập.
- Bộ sinh giả lập đa cảm biến có cấu hình, bản mô tả, kiểm tra và simulator phát lại.
- Khung PlatformIO/HardwareProfiler, cấu hình GPIO chưa được nghiệm thu.
- Docker backend/frontend và profile AI tuỳ chọn.
- Các lần kiểm tra đã ghi: backend/AI tests, frontend/Docker build, HTTP→WS, lưu raw và phục hồi giả lập sau ngắt gửi.
- Firmware khung build bằng PlatformIO6.2.0 với profile ESP32-S3 tạm; không chứng minh board thật.

### Điều chỉnh

- Việt hoá đặc tả, kế hoạch và comment; rút gọn cách diễn đạt, sửa ghi chú GPIO4 đã cũ thành cấu hình7 hiện có. Không đổi logic, trường dữ liệu hoặc lịch sử commit.
- Đồng bộ kế hoạch03–10 cho MQTT telemetry/điều khiển, giữ raw HTTP và browser HTTP/WS. Nghiệm thu phân biệt broker nhận, thiết bị thực thi và đủ dữ liệu; không tự đóng giai đoạn.
- Tách cấu hình local/IDE, thêm kiểm tra dấu conflict và phân biệt code đã có với phần cứng chưa nghiệm thu.
- Gom enum trong common_types.h; pins.h/sensor_config.h dùng board_config.h, CI kiểm tra tổ hợp header. Cleanup không tự đổi GPIO/rate hoặc thuật toán.
- Đổi thư mục AI thành ai và cập nhật đường dẫn liên quan.
- Chuyển Tailwind sang plugin Vite; lần audit production đã ghi nhận0 lỗ hổng.
- PR của Tân cần chủ repo duyệt; PR của Trung có ngoại lệ review sau đủ CI và không xung đột.

### Sửa lỗi

- Sửa hoa/thường Esp.h để build Linux.
- Thay favicon cũ bằng biểu tượng ASD-EASE có phiên bản URL, tránh dùng lại cache dự án localhost cũ.

### Loại bỏ

Chưa ghi nhận thay đổi loại bỏ riêng.
