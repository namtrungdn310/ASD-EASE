# Giai đoạn 07 — Kết nối Wi-Fi với backend

## Trạng thái

NOT_STARTED

## Người phụ trách

Trung — IT; Tân hỗ trợ phần cứng, driver và đo tốc độ mẫu.

## Mục tiêu

Gửi telemetry thật từ ESP32 qua broker MQTT cục bộ tới backend; nhận Start/Stop và xác nhận thực thi. Trình duyệt vẫn dùng HTTP/WebSocket.

## Lý do

Thay đường truyền giả lập mà không chuyển suy luận sang laptop.

## Phụ thuộc

Giai đoạn 06, Giai đoạn 02

## Đầu vào

Mạng LAN, địa chỉ laptop và phần cứng đã kiểm chứng.

## Công việc

- [ ] Làm đúng phạm vi đã thống nhất.
- [ ] Chạy các kiểm thử và lưu bằng chứng.
- [ ] Cập nhật tài liệu giai đoạn, tiến độ, thay đổi và quyết định liên quan.

## File dự kiến thay đổi

ai/edge_firmware/src/communication/...; backend/...

## Lưu ý triển khai

Theo [đặc tả API](../API_CONTRACT.md), [MQTT control](../contracts/MQTT_CONTROL.md) và [ánh xạ driver](../contracts/DRIVER_MAPPING.md). Giữ riêng phiên bản telemetry/raw và control; giới hạn hàng đợi, thời gian chờ, chỉ một tiến trình nhận MQTT. Không lưu retained cho telemetry/lệnh; PUBACK không chứng minh thiết bị đã thực thi hoặc DB đã ghi.

## Kiểm thử

ESP32 thật → broker LAN → backend → WebSocket/dashboard. Thử xác nhận lệnh, kết nối lại, khởi động lại broker/backend, lệnh cũ, quyền truy cập và ảnh hưởng tới lấy mẫu/bộ nhớ.

## Điều kiện nghiệm thu

- [ ] Có bằng chứng thật cho mục tiêu.
- [ ] Các kiểm thử bắt buộc đều đạt.
- [ ] Cập nhật tiến độ và rủi ro trước khi chuyển tiếp.
- [ ] MQTT, ACK thực thi và đồng bộ boot/phiên được thử thật; không suy từ PUBACK hoặc presence.
- [ ] Có bằng chứng wiring, tốc độ mẫu và RAM; fixture/build không thay nghiệm thu board.

## Đầu ra

Phần triển khai có thể review, kết quả kiểm thử và tiến độ đã cập nhật. Không tự chuyển sang giai đoạn sau khi chưa có yêu cầu.

## Rủi ro

Tường lửa, DHCP, thông tin truy cập hoặc lệnh mạng chặn.

## Xử lý lỗi và khôi phục

Dùng API health và nhật ký Serial; thử trên LAN riêng.

## Kết quả

Chưa thực hiện.

## Bằng chứng hoàn thành

Chưa có bằng chứng nghiệm thu.

## Kế hoạch chi tiết

Xem [kế hoạch tích hợp](../integration/README.md), [tiến độ](../integration/PROGRESS.md) và [đặc tả API](../API_CONTRACT.md). Tài liệu không thay đổi trạng thái nghiệm thu.

## Giai đoạn tiếp theo

Giai đoạn 08 — Ghi dữ liệu


