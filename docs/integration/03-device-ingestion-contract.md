# 03 — Đặc tả thiết bị, phiên và batch raw

| Mục | Nội dung |
|---|---|
| Nhánh | docs/device-ingestion-contract |
| Chủ trì | Trung — IT; Codex hoàn thiện tài liệu theo yêu cầu2026-10-31, Tân xác nhận phần cứng sau |
| Phụ thuộc |01 |
| Bắt đầu/bàn giao |2026-10-22 /2026-10-31 |
| Trạng thái |READY_FOR_REVIEW — đã xong phần tài liệu trên máy, chưa commit/push/PR/merge |
| Theo dõi |[Tiến độ](PROGRESS.md), dòng03; [bàn giao](03-HANDOFF.md) |

## Mục tiêu và phạm vi

Thống nhất dữ liệu, đơn vị, thời gian, lệnh và cách xác nhận để backend04/firmware05 triển khai độc lập. Đây là **nhánh tài liệu**, chưa có broker/client MQTT chạy thực tế.

Theo yêu cầu mới, Codex làm nốt phần tài liệu thay cho đọc từng file. Giữ nguyên hai schema Trung đã gõ; không tự ghi Trung đã hiểu hoặc phần cứng đã nghiệm thu.

## File bàn giao

| File | Dùng để làm gì |
|---|---|
| [API](../API_CONTRACT.md) | Tra trường dữ liệu và phân biệt hiện có/dự kiến |
| [Nhận dữ liệu](../contracts/INGESTION_V1.md) | Danh tính, thời gian, cấu hình, giới hạn, phiên, raw HTTP và lưu |
| [MQTT](../contracts/MQTT_CONTROL.md) | Topic, lệnh, ACK, boot/kết nối, thời hạn và phục hồi |
| [Driver](../contracts/DRIVER_MAPPING.md) | Ánh xạ trường/đơn vị và việc cần đo trên board |
| [Ví dụ](../contracts/examples.json) |28 gói/biến thể SYNTHETIC và16 kịch bản để viết tests |
| [Công cụ kiểm tra](../contracts/check_examples.py) | Kiểm tra mẫu, không chạy mạng/DB |
| [Hướng dẫn](../contracts/README.md) | Thứ tự đọc và lệnh chạy |
| [Quyết định](../DECISIONS.md) | ADR016–019, lý do chọn và giới hạn |
| [Bộ dữ liệu](../DATASET_PROTOCOL.md) | Nguồn, đơn vị, số mẫu thiếu và xuất dữ liệu |
| [Giai đoạn07](../phases/PHASE_07_WIFI_BACKEND.md), [08](../phases/PHASE_08_DATA_LOGGER.md), [thay đổi](../CHANGELOG.md) | Đồng bộ điều kiện nghiệm thu, không tự đánh DONE |

## Đặc tả đã hoàn thiện

- [x] Telemetry/raw giữ cấu trúc1.0, control phiên bản riêng; không thêm trường debug/boot sai schema.
- [x] HR lỗi/cũ/0 dùng null; SpO2 chỉ debug.
- [x] GSR ADC trung bình8 trước EMA; delta=percentChange/100 khi mức nền đáng tin.
- [x] IMU trước EMA đổi m/s² sang g, gyro degrees/s; không đảo Y/Z lần2.
- [x] Chưa thuật toán movement dùng null; chưa ước lượng chất lượng dùng0 bảo thủ; chưa mô hình thì probabilitynull và CALIBRATING/UNCERTAIN.
- [x] Mốc thu chung, thời gian boot ngoài phiên, tràn clock, mẫu thiếu, ranh batch cuối và giới hạn raw1.0.
- [x] Tách tốc độ danh định/đã đo, profile simulator và cổng phần cứng05/07.
- [x] Topic, chiều gửi, QoS, retain; presence không chứng minh mẫu mới.
- [x] Danh tính/ACL, trường gói, ID, TLS và ngoại lệ LAN phát triển; không secret trong browser.
- [x] Command ID/generation bền; boot/connection/request và thời hạn, không phát lại lệnh cũ.
- [x] HTTPStartStop giữ request; lưu ý định/lệnh trước202, ACK thực thi khác PUBACK.
- [x] Lặp lệnh/ACK, Stop thay Start, ACK muộn, reboot/restart không trộn epoch.
- [x] Mã lỗi ứng dụng MQTT, giới hạn gói/hàng đợi/thời gian chờ và thử lại.
- [x] Giữ HTTP simulator qua nghiệp vụ nhận chung, cập nhật tương thích ở04/06.
- [x] Raw chỉ HTTP; kiểm tra byte trước parse, số mẫu/kiểu/dải/trục/null/thời gian/cấu hình.
- [x] Khoá batch bất biến, JCS/SHA256, trùng202/xung đột409, đến sai thứ tự và trùng sau đóng.
- [x] Đủ mã HTTP400/401/403/404/409/413/415/422/429/503/507; timeout thử lại cùng ID/nội dung.
- [x] Mỗi batch một file +chỉ mục SQLite, PENDING→file tạm→lưu bền→COMPLETE→ACK; phục hồi sau lỗi và giữ JSONL cũ.
- [x] Hàng đợi giới hạn số/byte, bỏ batch mới khi đầy và khai báo mất, không tự ghi flash.
- [x] Tổng kết MQTT trước/sau raw HTTP; zero-batch, cutoff và thời hạn gửi nốt.
- [x] STOPPED khác đủ dữ liệu; broker lỗi khác HTTP lỗi; không tuyên bố “đúng một lần toàn hệ thống”.

## Kiểm tra local và merge

- [x] Đọc đối chiếu schema/router/service/driver; ghi rõ thiếu sót hiện có và phần dự kiến.
- [x] Công cụ mẫu đạt17 ca schema,11 mẫu control,9 biến thể sai bị từ chối; thời gian/số mẫu và16 tham chiếu kịch bản đúng.
- [x] Backend13/AI15 tests PASS, cảnh báo/commands ghi trong bàn giao.
- [x] Không nới kiểm tra hoặc sửa logic để mẫu đạt; ca hiện nhận nhưng đích từ chối có nhãn rõ.
- [ ] Chủ repo review, commit/push, mở PRbase dev; đủ CI/cập nhật/không xung đột.
- [ ] Merge03 rồi tạo04 từ dev mới; không tự merge hoặc push nhánh bảo vệ.

Các mục đã tick xác nhận **tài liệu và kiểm tra trên máy**, không xác nhận broker/board đã chạy.

## Việc còn chờ, giao nhánh sau

| Việc | Nơi nhận | Trạng thái |
|---|---|---|
| Wiring/GPIO7/board/flash/PSRAM, tuổi HR và hiệu chuẩn GSR |Tân+IT, nghiệm thu05 |PENDING_HARDWARE |
| Rate FIFO, jitter/đồng bộ, gửi raw và RAM khi MQTT+HTTP |07 |PENDING_HARDWARE |
| Chốt phiên bản client/broker, thử QoS1/ACL, chuyển DB/lệnh chờ |04/05 |NOT_IMPLEMENTED |
| Lưu raw bền, JCS, đồng thời và gây lỗi có kiểm soát |06/07 |NOT_IMPLEMENTED |
| Quan sát dashboard thật |02/10 |PENDING |
| Response chi tiết/phân trang/xuất cho UI |08 trước09 |Chưa chặn đặc tả cốt lõi04 |

Nếu board không đáp ứng quy tắc thời gian, đổi đặc tả/phiên bản trước khi nhận dữ liệu thật. Backend04 dùng mẫu SYNTHETIC, không cần bịa số đo để hoàn tất03.

## Nhật ký

- 2026-10-22: tạo từ dev d80cc0e sau PR #11, bắt đầu giải thích telemetry.py.
- 2026-10-22: Trung chọn MQTT telemetry/điều khiển, giữ raw HTTP và browser HTTP/WS.
- 2026-10-31: Trung yêu cầu hoàn thiện/bàn giao; hoàn tất đặc tả, ví dụ, kiểm tra và tài liệu liên quan, giữ thay đổi schema của Trung.

Sau review/merge: [nhánh04 — backend MQTT và quản lý phiên](04-backend-session-lifecycle.md). Nhánh03 hoàn tất tài liệu không có nghĩa giai đoạn03 MAX30102 hoặc07/08 đã DONE.
