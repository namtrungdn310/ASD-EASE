# Bàn giao nhánh04 — backend MQTT và quản lý phiên

Ngày2026-11-01, Asia/Saigon. Nhánh `feature/backend-session-lifecycle`, tách từ dev752bd5d sau [PR #12](https://github.com/namtrungdn310/ASD-EASE/pull/12).

**Đã triển khai và kiểm tra trên máy, READY_FOR_REVIEW. Chưa commit/push/PR/CI từ xa/merge.** Không tự đánh giai đoạn phần cứng DONE. Hướng dẫn chạy ở [04-SETUP](04-SETUP.md).

## Phần đã làm

- Mosquitto2.0.22 pin cả digest, Paho2.1.0/MQTT3.1.1. Tài khoản/ACL riêng, cổng demo loopback, không anonymous; có mẫu listener TLS.
- Settings kiểm tra secret/TLS; registry ràng buộc ID/nguồn/tài khoản/profile/transport. Bearer thiết bị khác người vận hành; browser dùng cookie HttpOnly có hạn và kiểm tra Origin, không secret trong bundle.
- Callback MQTT chỉ đưa vào hàng đợi giới hạn256 gói/1MiB, mỗi gói4KiB. Consumer tạo DB session riêng trên event loop, có bộ đếm lỗi/quá tải. Khoá receiver chống hai tiến trình; dùng1 worker, không reload.
- HTTP và MQTT qua cùng kiểm tra telemetry/nghiệp vụ; loại chuỗi/bool giả số, khoá lặp, NaN/Infinity, ID sai, nguồn sai, gói lặp/xung đột/cũ. Gói trùng không cập nhật last_seen, sự kiện hoặc WS lần2.
- Start/Stop lưu phiên+lệnh trước202, generation tăng theo thiết bị; DB khoá ghi và index chặn hai phiên mở. Lặp request giữ command ID, không reset epoch.
- Command có boot/connection/request/lease; chỉ STARTED ACK hợp lệ mới RECORDING. ACK lưu bền trước state confirmation, ACK lặp/cutoff xung đột được đối chiếu; Stop thay Start, ACK Start muộn không đảo về RECORDING.
- Backend/broker restart phải đồng bộ lại; reboot thiết bị làm gián đoạn phiên cũ. Timeout lệnh là ABORTED/UNKNOWN và chặn Start tới khi sync IDLE/STOPPED hoặc boot mới, không giả đã dừng.
- Lưu riêng tổng kết Stop/cutoff/final batch và drain deadline; chưa có đối chiếu raw thì không báo đủ. Raw API thêm quyền/phiên/giới hạn byte, vẫn JSONL đến06.
- Migration SQLite0→1 có bản sao trước sửa, transaction và khôi phục sang DB mới. Dữ liệu cũ giữ LEGACY/UNKNOWN, không suy DEVICE từ ID hoặc bịa complete.
- Simulator MQTT telemetry-only và simulator HTTP cập nhật Start/ACK/Stop/xác thực, ID mới; không gửi đôi hai transport. Hai bài tích hợp chạy trong check Backend tests của CI, giữ nguyên6 tên check.

## File chính làm gì?

| File | Vai trò |
|---|---|
| backend/app/core/config.py, security.py, wire.py | Cấu hình, danh tính/quyền và đọc JSON có giới hạn |
| backend/app/schemas/control.py | Kiểm tra các gói command/ACK/state/presence/tổng kết |
| backend/app/schemas/ingestion.py | Kiểm tra telemetry chặt ở mọi cấp, giữ schema tương thích của Trung |
| backend/app/db/models.py | Phiên, lệnh chờ, lease/nonce/kết nối, cursor chống lặp và phiên bản DB |
| backend/app/db/migrations.py | Sao lưu/chuyển DB cũ và công cụ khôi phục |
| backend/app/services/session_service.py | Start/Stop, lưu ý định/lệnh, timeout và response phiên |
| backend/app/services/control_service.py | Đối chiếu boot/connection/nonce/ACK, trạng thái đã xác nhận |
| backend/app/services/mqtt_runtime.py | Kết nối broker, hàng đợi, nhận/phát lệnh sau commit, reconnect và shutdown |
| backend/app/services/telemetry_service.py | Nghiệp vụ nhận chung, chống lặp, DB và WS |
| backend/app/api/v1/auth.py, device_control.py, sessions.py | Đăng nhập cookie, tương thích HTTP simulator và API Start/Stop |
| backend/app/main.py | Migration và vòng đời consumer khi backend khởi động/dừng |
| infra/mosquitto/, compose.yaml | Broker, ACL, listener và khởi động các service |
| scripts/setup_local_mqtt.py | Sinh credential/registry local, không in secret hoặc ghi đè file đang dùng |
| ai/simulator/mqtt_device.py | Thiết bị MQTT SYNTHETIC, ACK và giữ epoch qua reconnect |
| ai/simulator/mock_device.py | Giả lập HTTP có quyền/phiên mới và handshake tương thích |
| backend/tests/, scripts/check_mqtt_integration.py | Kiểm thử trạng thái/lỗi/DB và Mosquitto thật trên dữ liệu tạm |

Hai file telemetry.py/raw_batch.py Trung đã sửa định dạng trước khi tạo nhánh vẫn được giữ nguyên. Kiểm tra runtime mới nằm trong ingestion.py/control.py; không ghi đè phần code tay đó.

## Bằng chứng kiểm tra local

| Mục | Kết quả | Giới hạn |
|---|---|---|
| Backend |56 tests PASS sau rà soát trước PR |1 cảnh báo Starlette/anyio cũ |
| AI |15 tests PASS |14 cảnh báo matplotlib/pyparsing cũ |
| Frontend |26 tests và build PASS |Bundle>500kB là cảnh báo; không sửa UI/đã quan sát browser |
| Mẫu03 |17 ca schema tương thích,11 mẫu control và9 biến thể sai PASS |Schema mẫu cũ khác bộ kiểm tra runtime; không phải E2E phần cứng |
| HTTP thật |3 kịch bản,18 frame và1 frame sau reconnect khớp WS |DB/raw/port riêng; nguồn SYNTHETIC |
| Mosquitto thật |7 nhóm kiểm tra PASS |Container/DB/credential tạm, không phải ESP32 |
| Compose |config --quiet PASS |Không thay dịch vụ/volume đang dùng của nhóm; TLS thực tế chưa nghiệm thu |
| DB |Migration/backup/restore/idempotent/rollback lỗi PASS trong backend tests |Không thử mất điện máy/file system thật |

7 nhóm MQTT: (1) chặn anonymous/sai password; (2) Start→MQTT→ACK→DB→WS; (3) Start lặp không đổi generation/epoch; (4) chặn publish chéo thiết bị; (5) backend restart giữ phiên/ACK; (6) broker restart và HTTP vẫn tra cứu; (7) Stop ACK đúng, raw-disabled không báo complete.

Các bài lỗi bổ sung: Start đồng thời, command chưa phát phục hồi với cùng ID, ACK sai/cũ/lặp/xung đột, ACK bọc lại sau reconnect, Stop thay Start/timeout, reboot, nonce cũ, presence retained cũ, giới hạn JSON/hàng đợi, raw trước ACK/path traversal và migration hỏng không làm mất bảng cũ.

Lệnh chạy trong [04-SETUP](04-SETUP.md). Không chép kết quả local thành CI PASS trên SHA chưa push.

## Phần còn lại và bàn giao05/06

- Review diff, chọn các file của04 để commit theo nhóm, giữ thay đổi định dạng schema riêng; push/PR vào dev khi Trung yêu cầu. Chờ đủ6 CI trên head cuối, không xung đột rồi merge theo quyền.
- 05: Tân/IT đăng ký thiết bị DEVICE và credential riêng; chọn thư viện Arduino thực sự publish QoS1, thêm ACK/nonce/LWT, đo board/rate/tuổi cache/RAM. Không dùng số demo làm nghiệm thu.
- 06: thay JSONL bằng lưu bền/JCS/chống trùng, đối chiếu summary với raw trước/sau Stop, tính complete thật. 04 chỉ có cổng quyền/vòng đời và điểm nối, chưa nghiệm thu lưu raw.
- TLS mẫu và cookie Secure mặc định đã có; kiểm tra chứng chỉ/listener khi triển khai ngoài LAN phát triển là việc vận hành còn phải thử. Demo hiện dùng ngoại lệ loopback/LAN được ghi rõ, không gọi TCP1883 là mã hoá.
- Login browser hiện qua API/cookie theo hướng dẫn, chưa có màn hình đăng nhập; UI09 hoàn thiện luồng người vận hành. Quan sát Dashboard/browser của02 vẫn chưa được nghiệm thu trong04.
- Rà soát trước PR ngày2026-11-01: đã sửa ACK nhận nonce chưa đồng bộ và lỗi500 khi credential có Unicode; có kiểm thử hồi quy. Firmware build và4 tổ hợp header đều PASS, npm audit runtime không có lỗ hổng được báo. Chờ đủ6 CI từ xa trên head cuối trước merge vào dev; không merge vào main.

Thư viện và cấu hình được đối chiếu với [Paho Client](https://eclipse.dev/paho/files/paho.mqtt.python/html/client.html) và [Mosquitto configuration](https://mosquitto.org/man/mosquitto-conf-5.html), rồi kiểm tra thực tế bằng phiên bản đã pin.
