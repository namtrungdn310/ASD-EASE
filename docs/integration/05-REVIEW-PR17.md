# Rà soát PR #17 và chuẩn bị thử ESP trên máy Trung

Ngày 2026-11-05. Base: dev `46d4e2d` sau PR #17. Nhánh sửa: `fix/esp32-local-mqtt-integration`.

## Tân vừa thay đổi gì?

PR #17 có lịch sử nhiều commit cũ do nhánh tồn tại lâu. Phần chênh so với dev trước đó là 19 file, chủ yếu ở hai commit `670a672` và `d14b111`:

| Phần | Thay đổi | Đánh giá |
|---|---|---|
| Wi-Fi | Thêm log IP/RSSI/lỗi, tăng thời gian chờ kết nối lên 15 giây | Giữ log và timeout để chẩn đoán trên board. Dùng một vòng reconnect do worker quản lý. |
| Firmware | Thêm snapshot cảm biến thứ hai và 3 topic `sensors/ppg`, `sensors/imu`, `sensors/gsr` | Không nằm trong đặc tả/ACL đã thống nhất. Payload còn thiếu `data_origin`, nên receiver thật từ chối. Bỏ đường gửi phụ, giữ đầy đủ log cảm biến qua Serial. |
| Telemetry | Khi protocol chưa cho phép thì vẫn gửi frame ngoài phiên | Không giải quyết được thiếu sync; có thể sai phiên/thời gian khi START chưa xác nhận. Bỏ fallback, chỉ gửi sau xác nhận backend. |
| Backend MQTT | Thêm aggregator, nhận wildcard và nhiều tên topic khác nhau, broadcast trực tiếp | Bỏ qua schema runtime, phiên, chống trùng và lưu DB. Có chỗ suy quality=1 hoặc score từ gia tốc chưa có thuật toán được duyệt. Quay lại receiver thống nhất. |
| Subscriber phụ | Thêm `mqtt_subscriber.py`, aiomqtt và tests mock | App không khởi động subscriber này; cấu hình còn dùng tên trường không có trong Settings. Tests mock của lớp phụ chưa chứng minh receiver đang chạy đúng. Bỏ module phụ và thay bằng hồi quy trực tiếp trên MQTTRuntime. |
| Quyền browser | Cho qua khi Origin là localhost, hoặc nhận token qua URL | Localhost không thay bước đăng nhập. Khôi phục Bearer/cookie; WebSocket browser dùng cookie HttpOnly. |
| Mạng local | Chọn cổng broker, bind backend/frontend loopback | Giữ. ESP dùng IP LAN của laptop, browser dùng localhost. |
| Device ID | Board đổi thành ESP32-001 nhưng cấu hình mạng mẫu còn ID cũ | Đồng bộ mặc định/mẫu thành ESP32-001; file cấu hình thật vẫn phải khớp registry. |

Vì vậy đây không chỉ là việc sửa WebSocket/frontend. Các phép thử cần đi qua receiver production và kiểm tra cả sync, DB, cookie và dữ liệu đến WS.

## Code hiện đã sửa

- Gói 3 cảm biến đi chung trong `.../telemetry`; tổng cộng vẫn 6 topic/thiết bị theo MQTT_CONTROL.md.
- Sensing và mạng tách task, snapshot length 1; không gửi backlog và không lách xác nhận phiên.
- Thời gian kiểm tra freshness được lấy sau khi copy snapshot, tránh xem mẫu vừa đọc là mẫu ở tương lai do hai task chạy xen nhau.
- Chỉ receiver MQTTRuntime nhận dữ liệu, kiểm tra schema/identity/sync/phiên, commit DB rồi broadcast.
- Bộ đếm gửi thành công/thất bại được cập nhật lại; giữ log Wi-Fi/địa chỉ broker để chẩn đoán.
- Bổ sung tests cho sensor topics ngoài hợp đồng, subscribe đúng quyền, thiếu sync, trùng/cũ, DB lỗi, auth local và cookie WS.
- Bài broker thật đăng nhập HTTP rồi mở WS bằng cookie như browser, thay vì chỉ thử WS với Bearer.

## Thiết bị và môi trường hiện có

Trung xác nhận đang giữ ESP32-S3 Super Mini, MPU6050, MAX30102 và Grove GSR. Board đã cắm USB để cấp nguồn. Máy có Python/PlatformIO, Node và Docker Desktop; lần dò hiện chưa thấy cổng COM hoặc thiết bị USB ESP.

Đang dùng Wi-Fi quán cà phê, Windows nhận là Public. Chưa mở broker ra mạng này, chưa đổi firewall, chưa đặt mạng quán thành Private. Cần kiểm tra client isolation/captive portal; ưu tiên hotspot/router riêng 2.4 GHz cho buổi thử. Không dùng public broker để bỏ qua vấn đề LAN.

USB dữ liệu phục vụ nạp/log, không làm đường đưa số đo vào Dashboard. Chưa nạp vì chưa nhận COM; chưa đọc flash/chưa đo wiring và nhịp mẫu thật. Nghiệm thu nhánh 05 chưa hoàn tất.

Tiếp tục từng phần tại [05-LOCAL-BRINGUP.md](05-LOCAL-BRINGUP.md).
