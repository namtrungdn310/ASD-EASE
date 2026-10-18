# 07 — IT triển khai raw buffer và gửi batch trên ESP32

| Thuộc tính | Giá trị |
|---|---|
| Nhánh | `feature/firmware-raw-batching` |
| Chủ trì | Trung — IT; Tân xác nhận sampling/driver |
| Phụ thuộc | 05, 06 và đo được rate/timestamp từ cảm biến |
| Ước lượng | 1,5–3 ngày, chưa tính chờ phần cứng |
| Theo dõi | [PROGRESS.md](PROGRESS.md), dòng 07 |

## Kết quả cần đạt

ESP32 lưu được chuỗi mẫu trước EMA, gửi batch đúng raw contract, retry không làm biến đổi batch và sensing tiếp tục khi mạng tạm mất. Queue có giới hạn và mọi phần mất dữ liệu được khai báo.

## File / phạm vi

- Module raw buffer/batcher/serializer mới dưới `ai/edge_firmware/include/` và `src/communication/` hoặc thư mục `src/acquisition/` rõ ràng.
- Hook dữ liệu từ sensor layer và `main.cpp`; ưu tiên thêm interface drain samples thay vì sửa thuật toán đo.
- Config queue/window/timeouts, counter sampling/loss và tests.
- Metadata cấu hình đo, Phase 07/08 và runbook mất mạng.
- Không truyền USB làm đường thu chính; không lưu dataset trên laptop bằng cách parse Pretty JSON để thay thế raw stream.

## Cổng đầu vào: phải giải quyết trước khi viết batcher

- [ ] Tân/IT đo số mẫu thực nhận mỗi stream theo clock; phân biệt PPG sample rate chip với rate FIFO sau averaging.
- [ ] Driver MAX30102 hiện dùng FIFO nội bộ tính HR nhưng `read()` chỉ trả một snapshot cuối. Bổ sung đường lấy từng cặp red/IR có thứ tự, không chỉ gọi snapshot 100 lần rồi nhân bản giá trị cũ.
- [ ] Không lấy mẫu PPG chỉ vì loop timer tới hạn; chỉ thêm khi thật có sample mới, theo contract về null/gap khi bỏ lỡ.
- [ ] Raw IMU dùng trước EMA, đơn vị g và degrees/s; GSR dùng ADC đã averaging ở driver nhưng trước EMA, metadata nêu rõ processing này.
- [ ] Ghi measurement rate/jitter/loss và cách căn sample 0 cho cả ba stream. Nếu không đáp ứng clock model v1.0, quay lại contract với đề xuất version; không làm giả alignment.

## Checklist thiết kế buffer

- [ ] Một session epoch dùng chung, reset batch ID có chủ đích khi session mới, không reset khi reconnect Wi-Fi.
- [ ] Định nghĩa slot/index theo timestamp và rate; missing sample giữ null, không nén trục thời gian.
- [ ] Batch window ban đầu 1 giây là giả thuyết dev; tính số mẫu, JSON bytes, RAM peak và queue depth theo rate đã đo trước khi chọn cấu hình cuối.
- [ ] Không phụ thuộc PSRAM chưa xác minh; bounded queue, tránh copy toàn bộ lớn/cấp phát heap vô hạn.
- [ ] Dùng double buffer/ring buffer hoặc handoff có quyền sở hữu rõ; network task không sửa vùng sampling đang ghi.
- [ ] Batch đã đóng có payload bất biến: timestamp, samples, ID không thay trong mọi lần retry.
- [ ] Network task nhận ACK đúng ID mới giải phóng queue; response HTTP lỗi/không parse được không coi là accepted.
- [ ] Khi queue đầy, chốt drop policy/counter/gap theo contract; không đợi mạng trong sampling loop và không xoá mẫu âm thầm.
- [ ] Overflow trong outage dài vẫn giữ đúng timeline, ghi rõ batch/mẫu đã bỏ; duplicate không được làm tăng loss counter.
- [ ] Chính sách reboot không giả định RAM queue còn tồn tại. Báo phần chưa ACK đã mất và tạo phiên mới khi epoch đổi; không thêm flash spool khi chưa có thiết kế riêng.
- [ ] Ưu tiên telemetry/control hợp lý nhưng raw không bị starvation; lưu counters gửi thành công/retry/drop và thời gian gửi.

## Checklist stop/drain

- [ ] Stop command chốt cutoff thu; đóng final partial batch với sample count thực, không padding bằng 0.
- [ ] ACK stop gửi final batch ID và loss counters theo contract; command lặp không tạo batch cuối lần hai.
- [ ] Drain backlog trong deadline hữu hạn; không yêu cầu Wi-Fi mãi mới được ngừng một phiên.
- [ ] Backend hoàn tất khi đủ batch hoặc đánh incomplete khi thiếu/timeout; firmware không báo full success trước raw ACK.
- [ ] Test mở phiên mới khi phiên trước còn drain: không nhầm ID/epoch/buffer; tuân thủ policy một session active.

## Kiểm thử bắt buộc

| Tình huống | Đối chiếu cần có |
|---|---|
| Mẫu số thứ tự có thể dự đoán trong host test | Mọi stream đúng count/order/units, batch không duplicate boundary |
| Final partial batch | Timestamp và độ dài đúng, không lấp bằng 0 |
| Mất ACK sau backend đã ghi | Cùng payload retry, backend trả duplicate, queue được giải phóng đúng |
| Wi-Fi mất ngắn trong sức chứa queue | Gửi bù đúng thứ tự/policy, không trùng |
| Wi-Fi mất dài quá queue capacity | Drop/gap có số liệu, RAM hữu hạn, sensing tiếp tục |
| Thiết bị thật có mạng / không mạng | Đo rate/jitter/heap/queue để so ảnh hưởng transport |
| Mất cảm biến / reboot / stop timeout | Null/gap/aborted đúng, không biến số cũ thành mẫu mới |

Không dùng raw waveform synthetic chạy trên ESP32 rồi gắn nhãn DEVICE như dữ liệu cảm biến. Test pattern phải được lưu riêng là fixture/synthetic; DEVICE chỉ dùng khi nguồn là cảm biến thật.

## Điều kiện merge / nghiệm thu

- [ ] Serializer raw fixture pass schema tests; firmware build và required checks pass.
- [ ] Có bảng cấu hình rate/window/queue/RAM và test retry/overflow.
- [ ] Log board đối chiếu raw lưu được với counter firmware, có kiểm chứng stop/drain.
- [ ] Thiếu board/rate evidence -> `WAITING_HARDWARE`, không đóng Phase 08.
- [ ] Commit gợi ý: `feat(firmware): buffer and upload ordered raw sensor batches`.

## Rollback

Có thể tắt raw upload để giữ telemetry/Serial debug. Giữ recording đã lưu để đối chiếu; không reset sequence giữa phiên để chữa lỗi server.

## Nhật ký / kết quả thực hiện

| Ngày / commit | Task | Command / bằng chứng | Kết quả / blocker |
|---|---|---|---|
| — | — | — | Chưa thực hiện |
