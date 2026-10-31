# 06 — Nhận và lưu batch raw không trùng

| Mục | Nội dung |
|---|---|
| Nhánh | `feature/backend-raw-ingestion` |
| Phụ trách | Trung — IT |
| Phụ thuộc |03/04 |
| Ước lượng |1,5–2,5 ngày |
| Tiến độ |[Dòng06](PROGRESS.md) |

## Kết quả và phạm vi

POST /api/v1/raw-batch xác nhận đúng việc đã lưu, không đếm/lưu đôi khi retry và báo thiếu dữ liệu. Raw nằm ở file, SQLite giữ chỉ mục. Giữ HTTP, không thêm topic raw MQTT. Tổng kết điều khiển dùng adapter04; PUBACK không thay ACK lưu. Theo [kiến trúc](MQTT_ARCHITECTURE.md).

File liên quan: api/v1/raw_data.py, schemas/raw_batch.py, services/raw_storage.py, dịch vụ phiên, DB/chuyển dữ liệu, cấu hình, tests và simulator. Đồng bộ đặc tả/giai đoạn08.

## Cách lưu

```text
RAW_STORAGE_DIR/
  DEVICE/<session_id>/<device_id>/batches/<batch_id>.json
  SYNTHETIC/<session_id>/<device_id>/batches/<batch_id>.json
```

Đây là layout đích. ID kiểm tra và đường dẫn phải nằm trong root; client không chọn path. Batch bất biến, file tạm chưa là đã nhận. DB giữ hash/số mẫu/thời gian/nguồn/trạng thái, không chứa mảng mẫu thô.

## Kiểm tra dữ liệu

- [ ] Phiên tồn tại, đúng thiết bị/nguồn/quyền/trạng thái; không tạo phiên từ payload.
- [ ] STOPPING chỉ nhận theo cutoff/hạn gửi nốt; batch muộn hoặc đóng trả đúng đặc tả.
- [ ] Dùng cùng quyền/nguồn với MQTT; body tự khai không chứng minh danh tính.
- [ ] ID có allowlist/độ dài, chặn absolute path, .., /, \\ và kiểm tra đường dẫn sau resolve.
- [ ] Chặn quá byte ngay khi đọc, kể cả thiếu Content-Length; sau parse giới hạn số mẫu.
- [ ] Đúng độ dài PPG/6 trục IMU, null đúng vị trí; không bắt ba cảm biến cùng số mẫu.
- [ ] Từ chối NaN/Infinity, bool/chuỗi giả số, ngoài dải; không âm thầm cắt hoặc ép kiểu làm đổi dữ liệu.
- [ ] Cấu hình/rate/mốc thu/count/cửa sổ/batch cuối đúng; phát hiện chồng lấp/khoảng trống.

## Retry, đồng thời và lỗi khi lưu

- [ ] DB có khoá duy nhất (session_id,device_id,batch_id), nguồn gắn phiên.
- [ ] Hash JSON chuẩn hoá đúng quy tắc, không phụ thuộc khoảng trắng/thứ tự khoá.
- [ ] Cùng khoá/hash trả ACK trùng, không tăng số batch/mẫu lần2.
- [ ] Cùng khoá khác hash trả409 và giữ bản cũ.
- [ ] File tạm→flush/fsync→công bố nguyên tử cùng filesystem; ràng buộc DB bảo vệ nhiều process, không chỉ khoá Python.
- [ ] Thử các điểm lỗi PENDING/file/COMPLETE/ACK; không xác nhận trước khi dữ liệu nhất quán/lưu bền.
- [ ] Đối chiếu file thiếu chỉ mục hoặc ngược lại; không ghi đè bản gốc, không phục hồi được thì báo thiếu.
- [ ] Hết đĩa/quyền/lỗi ghi trả lỗi, file hỏng không xuất hiện như batch hợp lệ.
- [ ] Nhận sai thứ tự theo quy tắc, không dùng latest_batch_id để loại nhầm batch cũ hợp lệ.
- [ ] ACK chứa đúng ID/trùng; chỉ đếm một lần.
- [ ] Gửi nốt chỉ complete sau đối chiếu ID0..final; hết hạn ghi các batch thiếu.
- [ ] Tổng kết MQTT trước/sau raw cuối và tổng kết lặp cho cùng kết quả; ACK Stop chưa chứng minh đủ raw.
- [ ] Broker mất không làm raw/query cho phiên đã cấp quyền ngừng vô lý; không tự mở phiên hoặc coi mất broker là Stop.
- [ ] JSONL cũ giữ đọc được; chuyển đổi chỉ sau sao lưu/đối chiếu số mẫu/hash, không xoá volume.

## Kiểm thử

| Ca | Kết quả |
|---|---|
| Gửi mới/retry/mất ACK | Một bản/một lần đếm, ACK ổn định |
| Trùng ID khác nội dung/đồng thời | Không ghi đè/ghi đôi, xung đột rõ |
| Batch3,1,2 hoặc thiếu batch | Xuất đúng thứ tự, ghi gap |
| Sai quyền/phiên/nguồn/path | Không ghi ngoài root hoặc vào phiên khác |
| Quá cỡ, null, NaN, lệch trục | Mã HTTP đúng, không lưu dở payload |
| Lỗi giữa file/chỉ mục, hết đĩa | Phục hồi có bằng chứng, không accepted giả |
| Stop/tổng kết/raw đến mọi thứ tự | Đủ/thiếu nhất quán |
| Mất riêng broker hoặc HTTP | Không dùng PUBACK/ACKStop thay ACKraw |

## Bàn giao07

- [ ] Tests dùng vùng tạm, có đồng thời và gây lỗi ở điểm lưu chính.
- [ ] Ví dụ ACK/lỗi đủ cho firmware viết retry và tests C++.
- [ ] Không làm hỏng telemetry/phiên/simulator, CI đạt.
- [ ] Kiểm tra số mẫu/hash thực, không chỉ thấy file tồn tại.
- [ ] Commit gợi ý: `feat(backend): lưu raw chống trùng và kiểm tra phiên`.

## Nhật ký

| Ngày/commit | Việc | Bằng chứng | Kết quả |
|---|---|---|---|
|—|—|—|Chưa thực hiện|
