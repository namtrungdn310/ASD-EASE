# 05 — IT triển khai firmware gửi telemetry qua LAN

| Thuộc tính | Giá trị |
|---|---|
| Nhánh | `feature/firmware-telemetry-client` |
| Chủ trì | Trung — IT; Tân hỗ trợ board/driver |
| Phụ thuộc | 03, 04; 02 trước nghiệm thu dashboard |
| Ước lượng | 1,5–3 ngày, chưa tính chờ phần cứng |
| Theo dõi | [PROGRESS.md](PROGRESS.md), dòng 05 |

## Kết quả cần đạt

ESP32 nhận lệnh phiên, đóng gói telemetry chuẩn v1.0 và POST tới FastAPI bằng Wi-Fi LAN. Sensing tiếp tục trong lúc mạng chậm/mất. USB chỉ dùng flash/debug, không dùng làm transport chính hay bridge laptop thay thế networking.

## File dự kiến / ranh giới với driver

- Module mới `include/communication/`, `src/communication/` cho config, Wi-Fi, session-control, HTTP và serializer.
- Thay tối thiểu `src/main.cpp` để đưa snapshot cảm biến vào transport.
- `include/network_config.example.h` có placeholder; file local `network_config.h` vẫn gitignored.
- Firmware tests (host serializer khi khả thi, test transport/fake backend); `docs/phases/PHASE_07_WIFI_BACKEND.md` và LAN runbook.
- Không chỉnh thuật toán HR/GSR/IMU chỉ để payload đẹp. Mâu thuẫn driver hoặc clock ghi issue/blocker để phối hợp Tân.

## Checklist serializer

- [ ] Viết serializer riêng, không tái dùng Pretty JSON tiếng Việt; Serial debug vẫn là kênh diagnostic.
- [ ] Mapping đúng contract 03: null khi invalid/stale, schema/device/session/version, data_origin DEVICE cho board thật.
- [ ] GSR delta đúng tỷ lệ, movement chưa có thuật toán để null; không tự tính prediction giả trên laptop.
- [ ] Không có model -> probability null, model_version none; state/quality theo quy tắc đã chốt, không biến sensor VALID thành NORMAL.
- [ ] Sensor snapshot cần validity + tuổi dữ liệu; lỗi kết nối không gửi lại số cũ như một mẫu mới hợp lệ.
- [ ] Tạo snapshot nhất quán khi data đọc và network task khác nhau; copy giá trị, không giữ pointer vào buffer bị sửa.
- [ ] Capture JSON do C++ tạo bằng fixtures; kiểm tra qua Pydantic trong tests, không chỉ eyeball JSON trên Serial.

## Checklist networking và session

- [ ] Build CI không cần credential thật: template/default tắt networking hoặc config placeholder có kiểm soát; thiếu file local không làm compilation fail.
- [ ] SSID/password local, backend host là IP LAN laptop + port 8000; `localhost` trên ESP32 không phải laptop, tên service Docker không phải DNS LAN.
- [ ] Kiểm tra health từ một máy/thiết bị trong cùng LAN; ghi cấu hình cần mở port 8000 theo phạm vi cần thiết, không tự tắt firewall.
- [ ] Wi-Fi reconnect có backoff và giới hạn log; không while-loop chờ kết nối làm dừng sensing.
- [ ] HTTP/poll có timeout hữu hạn và retry; chạy trong task riêng/transport state machine để timeout không chặn loop lấy mẫu. Tính RAM/stack, tránh cấp phát vô hạn.
- [ ] Không chờ POST trong vòng đọc 10 ms; đo ảnh hưởng của transport/Serial output đến sensing.
- [ ] Poll session-control, ACK start đúng command và thiết lập epoch thu một lần; retry ACK không reset clock.
- [ ] `timestamp_ms` tính theo session epoch; xử lý rollover `millis()` và boot ID theo contract.
- [ ] Chưa có raw queue ở nhánh này: telemetry có thể giữ snapshot mới nhất, không cần gửi backlog vô hạn; báo dữ liệu mất theo policy và không chặn nhánh 07.
- [ ] Stop làm theo state machine; không tuyên bố đã drain raw trước khi nhánh 07 triển khai. Ghi rõ giới hạn hiện tại trong runbook.
- [ ] Retry timeout/5xx/connection error có giới hạn; 4xx do contract không retry mù. Parse status/body đủ để phân biệt và log lý do.
- [ ] Log thiết bị, version, HTTP status, counters/timing; không in Wi-Fi password.
- [ ] Ghi board/firmware/commit/network setup và kết quả thực vào Phase 07, giữ trạng thái chưa xong raw/khả năng khác.

## Ma trận kiểm thử

| Tình huống | Kết quả mong đợi |
|---|---|
| Serializer fixture hợp lệ/invalid/null | Pydantic chấp nhận đúng, không có extra field debug |
| Build không có network_config.h thật | CI compile pass, không credential trong image/source |
| ESP32 + backend cùng LAN | POST 202, DB metadata đúng, WebSocket/dashboard hiển thị DEVICE |
| Wi-Fi sai/mất; backend treo/chậm | Sensing không bị dừng theo thời gian HTTP; reconnect hữu hạn |
| Backend 422 / 409 / 500 | Xử lý khác nhau, không retry payload sai vô hạn |
| Start ACK lặp, stop, reboot | Không reset timestamp hoặc nhập nhầm phiên |
| Mất cảm biến trong lúc mạng vẫn tốt | Không gửi HR/GSR cũ như valid; null/state đúng |

## Điều kiện merge / nghiệm thu

- [ ] Firmware build trên Windows/Linux, serializer contract test và required checks pass.
- [ ] Có log sensing trước/sau bật network và đo gaps/rate; không chỉ ghi 'non-blocking' trong comment.
- [ ] Nếu chưa có board: có thể merge phần mềm với `WAITING_HARDWARE`, tuyệt đối không đóng Phase 07.
- [ ] Khi có board: ghi request 202 + frame WebSocket + ảnh dashboard + commit/điều kiện đo.
- [ ] Commit gợi ý: `feat(firmware): send contract telemetry over local Wi-Fi`.

## Rollback

Giữ chế độ Serial-only để debug, chọn qua config build/runtime rõ ràng. Không xoá driver của Tân. Nếu transport ảnh hưởng sampling, tắt transport và giữ log để sửa riêng scheduling.

## Nhật ký / kết quả thực hiện

| Ngày / commit | Task | Command / bằng chứng | Kết quả / blocker |
|---|---|---|---|
| — | — | — | Chưa thực hiện |
