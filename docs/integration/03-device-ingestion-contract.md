# 03 — Chốt contract thiết bị, session và raw batch

| Thuộc tính | Giá trị |
|---|---|
| Nhánh | `docs/device-ingestion-contract` |
| Chủ trì | Trung — IT; Tân xác nhận ngữ nghĩa dữ liệu driver |
| Phụ thuộc | 01 |
| Ước lượng | 1–2 ngày, gồm trao đổi/log sampling |
| Theo dõi | [PROGRESS.md](PROGRESS.md), dòng 03 |

## Kết quả cần đạt

Một đặc tả đủ rõ để viết backend và firmware độc lập: JSON hợp lệ, lifecycle, đơn vị, timestamp, lỗi/retry và tiêu chí dữ liệu đầy đủ. Nhánh này sửa tài liệu và ví dụ dưới docs; implementation/fixture executable nằm ở các nhánh sau.

## Tài liệu cần cập nhật

- `docs/API_CONTRACT.md`: nguồn chính cho endpoint, wire schema, version và error semantics.
- `docs/DECISIONS.md`: lý do chọn polling session-control, file-per-batch và chính sách retry.
- `docs/DATASET_PROTOCOL.md`: metadata đo, đơn vị và provenance.
- Đề xuất `docs/contracts/`: JSON examples, sequence lifecycle và mapping driver -> API; các ví dụ minh hoạ không phải dữ liệu người thật.
- Các phase 07/08 và changelog khi bổ sung acceptance criteria; không sửa code trong PR `docs/*` này.

## Checklist: mapping dữ liệu

- [ ] Giữ schema `1.0` khi ý nghĩa dữ liệu không đổi. Nếu bắt buộc breaking change, ghi version mới và lộ trình hỗ trợ/di chuyển trước khi code; không âm thầm đổi `1.0`.
- [ ] `MAX30102Data.heartRate` -> `hr_bpm` khi có kết quả còn mới/hợp lệ; giá trị sentinel 0 phải thành `null`.
- [ ] SpO2 để debug ở scope này vì contract v1.0 không có trường; không lén thêm field vào payload strict.
- [ ] `rawADC` trước EMA -> `gsr.raw`; ghi rằng driver đang averaging 8 lần đọc ADC, không gọi đó là mẫu ADC đơn chưa xử lý.
- [ ] `gsr.delta` là tỷ lệ baseline: nếu dùng `percentChange` thì chia 100; không gửi `deltaConductance_uS` trực tiếp. Baseline chưa có/không tin cậy -> `null`.
- [ ] Raw IMU lấy `rawAx/rawAy/rawAz` chia `9.80665` để ra g; gyro lấy `rawGx_deg/rawGy_deg/rawGz_deg`.
- [ ] `movement.score=null` trước khi có thuật toán và định nghĩa chuẩn; không gửi accel magnitude vào trường 0–1.
- [ ] Quality là chỉ số kỹ thuật theo quy tắc có ghi rõ. Nếu chưa có quality estimator, quy định cách biểu diễn bảo thủ trong schema hiện có hoặc version cần thiết; không bịa 0.9/1.0 là chất lượng đã đo.
- [ ] Không model -> `model_version=none`, probability null; `CALIBRATING` khi calibration cần thiết, còn chưa kết luận -> `UNCERTAIN`. Sensor `VALID` không tự thành `NORMAL`.

## Checklist: session-control

- [ ] Chốt request/response của `POST /sessions/start`, `/sessions/stop` và status trả về; tách desired state với actual state.
- [ ] Đặc tả endpoint đề xuất `GET /devices/{device_id}/session-control` cho ESP32 poll. Khác với endpoint đã tồn tại phải ghi rõ là planned API.
- [ ] Đặc tả endpoint ACK đề xuất `POST /sessions/{session_id}/device-status` cho bắt đầu, dừng và báo reboot; chốt payload, idempotency, command generation, retry/timeout.
- [ ] Lifecycle: STARTING -> RECORDING -> STOPPING -> STOPPED; ABORTED khi không khép phiên được. Command lặp lại không reset mốc thu hay tạo phiên mới.
- [ ] Ràng buộc session với device + origin; chỉ một phiên active cho một device. Boot ID/command generation là metadata control, không nhét field vào raw v1.0 nếu chưa version.
- [ ] Đặt mốc session khi firmware thực sự bắt đầu thu; timestamp tính từ đó. UTC backend chỉ phục vụ metadata wall-clock.
- [ ] Reboot trong phiên: kết thúc/đánh dấu gián đoạn, tạo phiên mới cho clock mới; payload cũ không bị nhập nhầm vào clock mới.
- [ ] STOPPING chốt mốc thu và final batch ID, drain giới hạn thời gian; thiếu batch phải đánh dấu incomplete. Phân biệt STOPPED với dữ liệu đầy đủ.

## Checklist: sampling, raw, retry và lưu trữ

- [ ] Đo rate sau FIFO averaging của PPG; không suy 100 Hz đầu ra chỉ từ biến cấu hình. Ghi config và log có thể tái kiểm tra.
- [ ] Với v1.0, mọi stream phải có sample 0 tương ứng cùng `start_timestamp_ms` và bước thời gian theo rate của nó. Nếu không căn được, cần đề xuất per-stream start/timestamps có version thay vì báo timestamp sai.
- [ ] Chốt nominal batch window, cách xử lý batch cuối ngắn hơn, clock wrap, jitter và mẫu thiếu. Dùng null giữ vị trí khi mất mẫu; dữ liệu vẫn ghi nhận loss/gaps.
- [ ] Giới hạn request/samples/queue dựa trên RAM board và payload đo thật. Khởi điểm thử nghiệm: cửa sổ 1 giây; dung lượng queue chưa đóng đinh trước khi tính bộ nhớ.
- [ ] Idempotency key `(session_id, device_id, batch_id)`; hash theo representation chuẩn hoá, null/kiểu số có quy tắc nhất quán.
- [ ] Bảng HTTP outcomes: 202 lần đầu/duplicate cùng nội dung, 409 cùng ID khác nội dung hoặc session không nhận dữ liệu, 404 session không có, 422 schema sai, 413 quá giới hạn, lỗi storage không trả accepted.
- [ ] Phân biệt request malformed JSON với schema validation; document error body đủ để firmware quyết định retry.
- [ ] Chốt nhận batch đến muộn trong STOPPING và out-of-order hợp lệ; manifest báo gap, export theo thời gian/ID đúng, không biến sự thiếu dữ liệu thành đủ.
- [ ] File-per-batch + index SQLite; commit/ACK/recovery, concurrent requests và crash window được mô tả. Không tuyên bố exactly-once toàn hệ thống nếu chưa chứng minh.
- [ ] Tách DEVICE/SYNTHETIC trong session, storage và manifest; không dựa riêng vào prefix tên.

## Ví dụ bắt buộc và review

- [ ] Telemetry khi đang calibration, có HR, mất PPG, không model, không active session.
- [ ] Raw batch đầy đủ, chứa null, final partial batch, duplicate và payload conflict.
- [ ] Start ACK thành công, retry command cũ, stop/drain timeout và reboot.
- [ ] Expected status/body cho từng ví dụ; tập examples được nhánh 04/05/06 đưa vào tests.
- [ ] Tân xác nhận GPIO, rate, đơn vị/raw-vs-filtered; ghi kết luận, không chỉ lời nhắn không lưu.
- [ ] Có quyết định cho mọi mục ảnh hưởng wire format trước khi nhánh phụ thuộc triển khai.

## Điều kiện merge / bàn giao

- [ ] Không còn TODO mơ hồ về units, clock, ACK, duplicate, stop/drain hoặc version.
- [ ] Ví dụ không trái schema/backend hiện tại; khác biệt planned được chỉ rõ kèm nhánh sẽ triển khai.
- [ ] Không làm mất compatibility simulator mà thiếu phương án cập nhật.
- [ ] Commit gợi ý: `docs: specify device ingestion and session control contract`.

## Nhật ký / quyết định thực tế

| Ngày / commit | Quyết định / đầu vào | Bằng chứng / người xác nhận | Kết quả / blocker |
|---|---|---|---|
| — | — | — | Chưa thực hiện |

Nhánh kế tiếp: [04](04-backend-session-lifecycle.md); thông số phần cứng chưa đo vẫn phải ghi rõ giới hạn của chúng.
