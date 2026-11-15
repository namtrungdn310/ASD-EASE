# Phiên theo dõi tự động

Phiên tự động của ESP và thao tác theo dõi Dashboard là hai luồng riêng. Khi ESP đồng bộ, backend tự mở/tiếp tục phiên theo boot. Người dùng vẫn chọn thiết bị và bấm **Kết nối** trên Dashboard để mở WebSocket xem telemetry. Bấm **Ngắt kết nối** chỉ đóng WebSocket của trang, không dừng phiên hoặc MQTT.

## Cách dùng

Mở Docker Desktop, bật ESP cùng LAN và chạy `npm run dev`. Launcher cấu hình backend để tự mở phiên cho đúng `device_id` trong `network_config.h`. Chọn thiết bị và bấm **Kết nối** để xem dữ liệu. Không cần API/DevTools/nút Start. Mở web hằng ngày không cần USB hoặc nạp lại firmware.

Backend chờ ESP đồng bộ đúng boot/connection, tạo phiên AUTO-… ở trạng thái STARTING, phát START qua MQTT. Chỉ sau ACK STARTED thật mới chuyển RECORDING. ESP đồng bộ xác nhận backend rồi gửi telemetry có session_id. Dashboard chỉ báo phiên đang hoạt động khi còn live và gói mới thuộc phiên tương ứng.

Browser chỉ tra cứu GET /api/v1/sessions và đọc telemetry qua WS. Không tự tạo mã phiên, không gửi Start/Stop, không tự kết thúc phiên khi đóng tab. Poll1 giây khi đang có phiên,4 giây khi chờ; có timeout/abort/renew cookie và dọn khi đổi thiết bị/unmount.

## Mốc phiên

- Mỗi lần ESP khởi động (boot_id) tạo tối đa một phiên tự động. Chạy lại npm, F5, nhiều tab hoặc reconnect Wi-Fi/broker không tạo phiên mới cho cùng boot đang hoạt động.
- Backend restart dùng phiên/lệnh bền đang có, không tạo thêm phiên. Ctrl+C vẫn chỉ dừng frontend như cách chạy đã chốt; broker/backend và phiên tiếp tục.
- Khi ESP reboot, cơ chế đồng bộ đánh dấu phiên trước bị gián đoạn, tạo phiên mới cho boot mới. Không nối timestamp về0 vào phiên cũ.
- Mất mạng tạm không tự coi là Stop; chờ đồng bộ lại để giữ timeline đúng. Dashboard có thể báo phiên chờ dữ liệu, thiết bị chưa kết nối.
- Stop chủ động qua API hoặc Start bị từ chối/quá hạn không được tự tạo Start lặp mãi trên cùng boot. Cần đối chiếu nguyên nhân; khởi động lại ESP khi đã sẵn sàng để có boot/phiên mới. Phiên legacy chưa giải quyết hoặc thiết bị unresolved cũng không bị tự ghi đè.

## Cấu hình và giới hạn

`local_dev.py` ghi AUTO_SESSION_ENABLED=true, AUTO_SESSION_DEVICE_ID=<device_id> vào backend.env local được Git bỏ qua. Cấu hình chạy riêng mặc định false. Backend kiểm tra identity phải là DEVICE/MQTT; không tự mở phiên giả lập hoặc thiết bị khác. Giao thức/nhịp truyền/six topics và schema1.1 giữ nguyên.

Auto session tạo mã/lệnh và nhóm telemetry theo lần chạy, **chưa là chức năng lưu dữ liệu thô đầy đủ để train**. Raw bền/batching/export vẫn ở nhánh06–09. Không đánh recording_complete chỉ vì RECORDING hoặc vì Dashboard có số. Không gắn participant_id thật hoặc nhãn nghiên cứu tự động.

Tính năng này được bổ sung theo yêu cầu trong nhánh đang làm, không đánh nhánh09 hoàn tất: giao diện danh sách/chi tiết/xuất dữ liệu và nghiệm thu raw vẫn còn.

## Bằng chứng

- Backend111 tests, frontend60 tests và build TypeScript/Vite đạt. Các test dữ liệu mô phỏng được giữ trong test, không gắn nhãn DEVICE cho luồng giả.
- Đã thử trên máy Trung: launcher chuẩn bị cấu hình mà không đổi Wi-Fi/header firmware; backend rebuilt/healthy. Từ trạng thái chưa có phiên DEVICE, hệ thống tự tạo AUTO-… và nhận ACK thật để RECORDING, không gửi Start từ browser/công cụ kiểm thử.
- DB có cursor theo ESP32-001:session:AUTO-…, timestamp tăng; sau khi cấp cookie và mở WebSocket, probe nhận3 frame DEVICE mới. Không lưu số sinh học thật vào Git.
- Backend có tests bật/tắt, chưa sync, đúng target/source/boot, ACK chờ/thực thi, concurrent creation, refresh/reconnect/restart, reboot và không lặp Start sau Stop/timeout.
- Frontend có tests hook thật cho STARTING→ACK nhưng chưa có telemetry→live cùng session, stale, đổi thiết bị và chỉ GET; không có nút hoặc POST Start/Stop.
- Browser tool chưa khả dụng, không tuyên bố đã chạy kiểm thử pixel hoặc phần cứng trên máy Tân. Tân cần lấy cùng code và giữ cấu hình local riêng.
