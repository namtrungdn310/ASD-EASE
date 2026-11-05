# 05 — Firmware gửi telemetry và nhận lệnh MQTT

| Mục | Nội dung |
|---|---|
| Nhánh kế hoạch | `feature/firmware-telemetry-client` |
| Nhánh hoàn thiện | `feature/firmware-telemetry-client-completion` từ dev1e73aea |
| Phụ trách | Tân triển khai đầu và thử board; Trung hoàn thiện code sau PR #14, review |
| Phụ thuộc |03/04;02 cho Dashboard |
| Trạng thái |IN_PROGRESS: đã nạp và nhận live DEVICE qua WS; còn Serial/Dashboard/StartStop/lỗi/tài nguyên thật |
| Tài liệu |[Setup](05-SETUP.md), [kiểm tra](05-VERIFICATION.md), [bàn giao](05-HANDOFF.md), [nhật ký](05-IMPLEMENTATION-LOG.md), [tracker](PROGRESS.md) |

Cập nhật 2026-11-05. Trung đã nạp COM7 thành công. Sau sửa PR #17 trên `fix/esp32-local-mqtt-integration`, backend sync1 và WS nhận3 frame DEVICE/ESP32-001 thật qua hotspot iPhone. Đang kiểm tra Serial, còn Dashboard/StartStop/lỗi/tài nguyên. Theo [rà soát](05-REVIEW-PR17.md) và [từng bước](05-LOCAL-BRINGUP.md); các kết quả 2026-11-03 dưới đây là lịch sử phần mềm.

## Mục tiêu và phạm vi

Cảm biến thật ESP32 → Wi-Fi LAN → broker MQTT → backend04 → WebSocket → Dashboard hiện có. Start/Stop từ API → MQTT command → ESP32 thực thi → ACK → backend xác nhận trạng thái.

Giữ Serial để nạp/chẩn đoán, không thay kênh MQTT bằng USB. Nhánh05 chưa ghi raw; raw HTTP/batching thuộc06/07, UI điều khiển đầy đủ thuộc09. Không thay thuật toán lọc, tự tạo prediction hoặc nới schema để chấp nhận dữ liệu sai.

## Phần code đã triển khai

- [x] Core C++ portable dùng chung production/tests: serializer, epoch, lease, nonce, generation và chống thực thi lặp.
- [x] Payload telemetry1.0 đúng mapping; null khi thiếu/cũ, GSR delta là tỷ lệ, quality0/modelnone/probabilitynull; chưa có movement score.
- [x] Metadata thời điểm mẫu và nhịp HR hợp lệ từ driver; dùng đồng hồ64 bit để kiểm tra freshness qua millis rollover.
- [x] Snapshot copy qua queue1; chỉ gửi bản mới nhất mỗi1000 ms, không gom backlog sau reconnect.
- [x] ESP-MQTT có publishQoS1, pin platform7.1.3/ArduinoJson7.4.3; giữ sensor libraries hiện có.
- [x] Task mạng riêng; callback xếp tối đa8 gói, control/outbox gửi8 gói/32 KiB, timeout/backoff hữu hạn.
- [x] Connection nonce/LWT trước CONNECT, clean session, đợi SUBACK rồi sync; xác nhận nghiệp vụ khác PUBACK.
- [x] Start/Stop/ACK/confirmation, lệnh lặp/cũ/sai profile, Stop thay Start, giữ epoch khi reconnect; reboot không tự Start.
- [x] Đồng bộ mỗi15 s, chặn telemetry theo phiên khi backend chưa xác nhận; timeout authorization30 s.
- [x] Build thiếu secret vẫn được; mặc định mạng tắt, env riêng compile/link nhánh mạng/TLS và không tự kết nối.
- [x] Helper tạo DEVICE riêng nguồn/profile/credential/ACL, không thay tài khoản simulator.
- [x] Compose chọn IP LAN/thư mục credential qua biến; mặc định broker loopback.
- [x] Dùng receiver04 có registry/phiên; bỏ subscriber thử topic cũ chưa dùng và kiểm tra chặn topic sai.
- [x] Ghi số mẫu, loop gap, heap thấp nhất, stack watermark và outbox; chưa có số đo board.
- [x] Native C++ → Pydantic runtime, broker/backend/DB/WS thật và hồi quy local.
- [x] Hướng dẫn nạp/LAN/login/API và ma trận F01–F19.

## Phần nghiệm thu còn lại

- [ ] Tân xác nhận board/flash/PSRAM/dây; code giữ MPU SDA5/SCL11, PPG8/9, GSR7.
- [ ] Nạp firmware networking-enabled thật, SUBACK/sync/ACL trên broker LAN.
- [ ] Dữ liệu cảm biến thật đến Dashboard với nguồn DEVICE; null/stale khi ngắt cảm biến.
- [ ] Start/Stop/lệnh lặp/Stop thay Start/reboot/mất Wi-Fi/restart broker/backend trên ESP32 thật.
- [ ] So số mẫu/rate/gap/độ trễ/heap/stack trước và sau mạng/Serial; profile50/50/20 chưa là số đo.
- [ ] Kiểm tra TLS/chứng chỉ trên board khi dùng ngoài LAN phát triển riêng.
- [x] Commit/push phần completion và mở [PR #15 vào dev](https://github.com/namtrungdn310/ASD-EASE/pull/15) theo yêu cầu Trung; CI/review/merge xác nhận tại PR, chỉ merge sau đủ6 check và không xung đột.
- [ ] Cập nhật F01–F19 và trạng thái theo bằng chứng; chưa đóng phase07 hoặc nhánh05.

## Kết quả đúng khi chưa có raw

Stop trả summary zero-batch, cutoff0, raw_recording_enabled=false. Backend STOPPED nhưng recording_complete=false/RAW_RECORDING_DISABLED là dự kiến; không giả complete=true. Thu mới phải dùng session_id mới.

Có thể tiếp tục06 trên nền04 song song lúc chờ board.07 chỉ nghiệm thu được khi05/06 và số đo phần cứng đủ.

## Khôi phục

Đặt ASD_NETWORK_ENABLED=0 rồi build/nạp env esp32s3_supermini để về sensing/Serial-only. Giữ credential/DB/log để đối chiếu; không xoá DB, đổi generation hoặc dùng public broker để né lỗi.
