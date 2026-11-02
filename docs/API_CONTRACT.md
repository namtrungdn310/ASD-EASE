# Đặc tả API và dữ liệu thiết bị

Cập nhật: 2026-11-01. Đây là điểm tra cứu chung cho firmware, backend, simulator, frontend và bộ dữ liệu. Phần **dự kiến** là quy tắc phải triển khai ở nhánh sau, không phải chức năng đã chạy.

**Triển khai nhánh04, 2026-11-01:** đã có Mosquitto2.0.22/Paho2.1.0, xác thực, nhận telemetry chung HTTP/MQTT, Start/Stop202, lệnh bền/ACK/nonce/đồng bộ và migration SQLite1. Xem [cách chạy](integration/04-SETUP.md), [bàn giao](integration/04-HANDOFF.md). Bảng dưới mô tả mốc d80cc0e trước triển khai; raw lưu bền/JCS/đối chiếu đủ dữ liệu vẫn thuộc06, firmware MQTT thuộc05.

## Hiện có và dự kiến

| Thành phần | Hiện có ở d80cc0e | Mục tiêu |
|---|---|---|
| HTTP telemetry | Kiểm tra Pydantic, cập nhật thiết bị/sự kiện và phát WebSocket; không lưu mọi snapshot thành một hàng DB | Nhận HTTP/MQTT qua chung nghiệp vụ, thêm xác thực ở 04 |
| MQTT | Chưa có broker/client/điều khiển | Mosquitto cục bộ, MQTT 3.1.1 ở 04–05 |
| HTTP raw | Thêm batch vào JSONL, chưa bảo đảm chống trùng/quyền sở hữu phiên/lưu bền | Mỗi batch một file và chỉ mục ở 06–07 |
| Start/Stop | Tạo phiên, ghi thời điểm dừng; Start trả 200, ID lặp trả 409 | Lệnh bền trong DB, trạng thái mong muốn/thực tế và ACK ở 04 |
| Chi tiết/xuất bản ghi | Chưa hoàn chỉnh | Đặc tả response trước khi làm 08–09 |

Quy tắc đích nằm trong [nhận dữ liệu](contracts/INGESTION_V1.md) và [điều khiển MQTT](contracts/MQTT_CONTROL.md). Xem thêm [ánh xạ driver](contracts/DRIVER_MAPPING.md), [mẫu JSON](contracts/examples.json), [hướng dẫn đọc](contracts/README.md), [bàn giao 03](integration/03-HANDOFF.md).

Giữ URL /api/v1 và schema_version=1.0 cho telemetry/raw. Control có phiên bản riêng. Đổi giao thức không tự đổi phiên bản; thay đổi làm mất tương thích phải có kế hoạch cập nhật các bên.

JSON dùng UTF-8. Hiện model chỉ cấm trường lạ ở cấp gốc telemetry/raw, chưa cấm đầy đủ ở cấp lồng nhau hoặc chặn mọi trường hợp ép kiểu/sai giới hạn mẫu.

Hai schema telemetry.py/raw_batch.py giữ làm tương thích. Runtime telemetry04 dùng `schemas/ingestion.py`: ID allowlist, nguồn khai rõ, số nguyên JSON chặt, số đo không ép chuỗi/bool, cấm trường lạ mọi cấp và không nhận NaN/Infinity/khoá lặp. Raw mới thêm quyền/phiên/giới hạn byte; kiểm tra mẫu chặt ở06.

## Xác thực ở nhánh04

- Thiết bị HTTP: Bearer token riêng, nguồn/ID từ registry. Mỗi identity chọn transport=http hoặc mqtt; không nhận hai transport cho cùng luồng telemetry.
- Người vận hành: Bearer token riêng hoặc cookie HttpOnly từ POST `/api/v1/auth/login` với body `{ "token": "<nhập từ file local>" }`. Không đưa token vào VITE_*, URL hoặc localStorage. POST cookie/WS kiểm tra Origin; cookie hết hạn1 giờ.
- GET `/health` công khai; GET `/health/mqtt` và API dữ liệu/điều khiển cần quyền người vận hành. WS `/ws/live` dùng cookie hoặc header Bearer cho công cụ kiểm thử.
- Simulator HTTP thêm POST `/devices/sync` (STATE_REQUEST→STATE_RESPONSE), POST `/devices/ack` (ACK→accepted), cùng token thiết bị. Firmware MQTT dùng topic, không poll các đường HTTP này.
- Start/Stop giữ body đã chốt; trả202 khi đang chờ, lặp trả cùng phiên/lệnh; trả200 khi đã giải quyết. Response có vòng đời/mốc giờ/cutoff/đủ dữ liệu như INGESTION_V1. `started_at` có thể null trước STARTED ACK.
- `recording_complete` không được suy từ STOPPED. Simulator telemetry-only báo RAW_RECORDING_DISABLED. Raw có summary nhưng chưa đối chiếu sẽ chờ drain rồi incomplete ở04.

## Thời gian

Trong phiên, timestamp_ms/start_timestamp_ms là mili giây từ mốc bắt đầu thu trên thiết bị, không phải giờ nhận HTTP/MQTT. Telemetry ngoài phiên dùng thời gian từ lúc boot theo quy tắc đồng bộ dự kiến.

Mẫu thứ i có thời gian start_timestamp_ms + i*1000/sample_rate_hz; mẫu đầu các luồng phải cùng mốc. Mẫu thiếu giữ null tại đúng vị trí. Raw 1.0 không giữ được jitter tuỳ ý; file giả lập có thể lưu timestamp riêng. Đây là quy ước, chưa phải số đo board. Xem [thời gian và lấy mẫu](contracts/INGESTION_V1.md#clock-and-sampling).

## Telemetry — POST /api/v1/telemetry

Nhịp gửi phát triển mặc định 1 Hz, có thể cấu hình. Hiện HTTP trả 202 khi kiểm tra schema đạt; gửi MQTT ở nhánh 04–05 sẽ dùng cùng cấu trúc JSON.

| Trường | Kiểu, đơn vị, giới hạn | Khi thiếu/chưa hợp lệ |
|---|---|---|
| schema_version | Chuỗi đúng 1.0 | Bắt buộc |
| device_id | Chuỗi ID, tối đa 64 ký tự | Bắt buộc |
| session_id | Chuỗi ID tối đa 64 hoặc null | Null khi không có phiên |
| timestamp_ms | Số nguyên ms >=0 | Theo mốc phiên hoặc boot |
| data_origin | DEVICE/SYNTHETIC | Phải khai rõ; giá trị khai báo không thay xác thực nguồn |
| hr_bpm | Số 20–240 bpm hoặc null | Chưa đo, lỗi hoặc cũ thì null |
| gsr.raw | Số nguyên ADC 0–4095 hoặc null | Chưa có thì null; không phải độ dẫn |
| gsr.delta | Tỷ lệ so với mức nền hoặc null | Null khi chưa có mức nền đáng tin |
| movement.score | Số 0–1 hoặc null | Chưa có thuật toán thì null |
| signal_quality.ppg/gsr/imu | Số 0–1 | Chỉ số kỹ thuật, không mặc định là chất lượng đã đo |
| prediction.probability | Số 0–1 hoặc null | Chưa có mô hình hoặc không đủ chất lượng thì null |
| prediction.state | NORMAL/ATTENTION/UNCERTAIN/CALIBRATING | Chỉ trạng thái kỹ thuật |
| firmware_version | Chuỗi phiên bản | Simulator dùng simulator-* |
| model_version | Chuỗi phiên bản hoặc none | none nghĩa chưa có mô hình trên thiết bị |

Ví dụ giả lập cũ dưới đây có điểm/trạng thái được gán để thử phần mềm, không phải suy luận thật. Với DEVICE chưa có mô hình, quy tắc đích yêu cầu probability=null và CALIBRATING/UNCERTAIN.

```json
{"schema_version":"1.0","device_id":"SIM-001","session_id":"SYN-SESSION001","timestamp_ms":0,"data_origin":"SYNTHETIC","hr_bpm":78.4,"gsr":{"raw":1842,"delta":0.13},"movement":{"score":0.42},"signal_quality":{"ppg":0.91,"gsr":0.87,"imu":1.0},"prediction":{"probability":0.74,"state":"ATTENTION"},"firmware_version":"simulator-0.1.0","model_version":"none"}
```

## Raw — POST /api/v1/raw-batch

Raw vẫn đi HTTP. Simulator mặc định PPG100/IMU50/GSR20 Hz. Firmware hiện cấu hình PPG chip100, averaging2 → FIFO50 Hz danh định, IMU50/GSR20; chưa có phép đo xác nhận.

Hiện append JSONL thành công trả 202, chưa chứng minh đã lưu bền và chống trùng. ACK đích nằm trong [quy tắc nhận dữ liệu](contracts/INGESTION_V1.md).

| Trường | Kiểu, đơn vị, giới hạn đích | Ghi chú |
|---|---|---|
| schema_version/device_id/session_id | Chuỗi, như trên | session_id bắt buộc; kiểm tra phiên/quyền còn phải triển khai |
| batch_id | Số nguyên >=0 | Tăng trong phiên |
| start_timestamp_ms | Số nguyên ms >=0 | Thời gian mẫu đầu của mọi luồng |
| data_origin | DEVICE/SYNTHETIC | Nguồn phải khớp phiên/thiết bị |
| ppg.sample_rate_hz | Số Hz >0 | Tốc độ dùng để dựng lại thời gian |
| ppg.red/ir | Mảng số đếm nguyên 0–262143 hoặc null | Hai mảng cùng độ dài |
| imu.sample_rate_hz | Số Hz >0 | Tốc độ IMU |
| imu.ax/ay/az | Mảng gia tốc, g hoặc null | Cùng độ dài cả sáu trục |
| imu.gx/gy/gz | Mảng vận tốc góc, degrees/s hoặc null | Cùng quy tắc mẫu thiếu |
| gsr.sample_rate_hz | Số Hz >0 | Tốc độ GSR |
| gsr.adc | Mảng ADC nguyên 0–4095 hoặc null | Không phải độ dẫn đã hiệu chuẩn |

Bảng nêu đơn vị/giới hạn cần đạt. Sample=int|float|None hiện chưa kiểm tra đầy đủ giới hạn và kiểu theo từng cảm biến; không nhầm đặc tả với kiểm tra đã có.

## API hiện có khác

| Phương thức | Đường dẫn | Vai trò |
|---|---|---|
| GET | /api/v1/health | Kiểm tra backend |
| GET | /api/v1/devices | Thông tin thiết bị và lần nhận gần nhất |
| POST | /api/v1/sessions/start | Yêu cầu bắt đầu phiên |
| POST | /api/v1/sessions/stop | Yêu cầu dừng phiên |
| GET | /api/v1/sessions | Danh sách phiên |
| POST | /api/v1/annotations | Lưu chú thích nghiên cứu |
| GET | /api/v1/events | Danh sách sự kiện kỹ thuật |
| WS | /api/v1/ws/live | Phát telemetry được chấp nhận |

Khi triển khai, cập nhật đặc tả, Pydantic, TypeScript, C++ và simulator liên quan. Không tự sửa payload 1.0 để nhét thêm trường hoặc phá khả năng phát lại dữ liệu cũ.

