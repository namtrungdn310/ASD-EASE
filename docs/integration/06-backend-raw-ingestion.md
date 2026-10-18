# 06 — Raw ingestion nhất quán, giới hạn và không ghi trùng

| Thuộc tính | Giá trị |
|---|---|
| Nhánh | `feature/backend-raw-ingestion` |
| Chủ trì | Trung — IT |
| Phụ thuộc | 03, 04 |
| Ước lượng | 1,5–2,5 ngày |
| Theo dõi | [PROGRESS.md](PROGRESS.md), dòng 06 |

## Kết quả cần đạt

`POST /api/v1/raw-batch` xác nhận đúng việc lưu dữ liệu, không ghi trùng khi firmware retry, giữ thứ tự và báo thiếu dữ liệu. Raw nằm ở file, SQLite chỉ chứa metadata/index.

## File dự kiến

`backend/app/api/v1/raw_data.py`, `schemas/raw_batch.py`, `services/raw_storage.py`, session service, DB models/migrations, config, raw tests. Cập nhật simulator/fixtures để đi qua session lifecycle, contract lỗi và Phase 08.

## Thiết kế lưu đề xuất

```text
RAW_STORAGE_DIR/
  DEVICE/<session_id>/<device_id>/batches/<batch_id>.json
  SYNTHETIC/<session_id>/<device_id>/batches/<batch_id>.json
```

Chốt layout ở implementation theo contract. Tên thư mục là ID đã validate và resolve dưới root; client không gửi path. File batch bất biến, file tạm không được coi là batch đã nhận. Dùng metadata index cho hash, counts, khoảng thời gian, origin và trạng thái lưu, không lưu raw arrays vào SQLite.

## Checklist validation và session

- [ ] Kiểm tra session tồn tại, đúng device/origin, state nhận dữ liệu hợp lệ; không tự tạo session từ payload.
- [ ] STOPPING chỉ nhận batch nằm trước cutoff và trong drain policy; batch đến muộn sau khi đóng có kết quả đúng contract.
- [ ] ID có allowlist/độ dài, chặn absolute path, `..`, `/`, `\` và resolve containment; không chỉ nối string.
- [ ] Giới hạn byte request trước khi đọc body không giới hạn, có cách xử lý request không có Content-Length; giới hạn samples trong Pydantic sau parse.
- [ ] Kiểm tra equal-length theo từng stream; cho null đúng vị trí. Không bắt PPG/IMU/GSR có số mẫu bằng nhau vì rate khác nhau.
- [ ] Reject NaN/Infinity, bool giả số, giá trị ngoài phạm vi đã chốt; không silently truncate/coerce làm đổi dữ liệu.
- [ ] Rate, thời gian bắt đầu, final partial batch và nominal window khớp policy; phát hiện batch chồng lấn/gap theo contract.

## Checklist retry, concurrency và crash recovery

- [ ] Unique key DB `(session_id, device_id, batch_id)` kèm origin đã ràng buộc session.
- [ ] Canonical hash có quy tắc rõ cho JSON field order/number/null; duplicate là cùng payload theo contract, không phụ thuộc whitespace HTTP body.
- [ ] Cùng key/hash: trả ACK đã nhận, không append hoặc tăng sample count lần hai.
- [ ] Cùng key/hash khác: 409, giữ nguyên bản cũ, log metadata conflict.
- [ ] Ghi tạm -> flush/đóng -> publish atomic trên cùng filesystem; bảo vệ key khi concurrent workers, không chỉ dùng lock trong một Python process.
- [ ] Chốt crash windows DB/file: pending index, file publish, complete index, ACK. Không ACK trước khi trạng thái durable nhất quán.
- [ ] Có reconcile file đã ghi nhưng thiếu index và index thiếu file; phục hồi không ghi đè recording gốc, trạng thái không thể phục hồi được báo incomplete.
- [ ] Disk full/permission error/JSON write error trả lỗi rõ, không để file hỏng xuất hiện như batch hợp lệ.
- [ ] Chấp nhận out-of-order theo policy và giữ nhận diện gap; không dùng `latest_batch_id` để loại nhầm retry/late batch hợp lệ.
- [ ] Đếm batch/mẫu một lần; ACK bao gồm ID và duplicate status theo contract.
- [ ] Stop/drain chỉ complete khi final batch ID và tập batch cần có được đối chiếu; timeout -> incomplete có danh sách gap.
- [ ] Dữ liệu JSONL legacy vẫn đọc/được giữ; migration chỉ khi có backup và đối chiếu sample count/hash. Không xoá volume cũ.

## Ma trận kiểm thử

| Test | Kết quả mong đợi |
|---|---|
| First submit + retry nhiều lần | Một batch, một lần sample count; ACK ổn định |
| Cùng ID khác payload; hai request đồng thời | Không overwrite hoặc ghi đôi; conflict rõ |
| Batch đến 3,1,2; batch bị thiếu | Order export xác định, gap được ghi đúng |
| Sai session/device/origin, path traversal | Không ghi ra ngoài root hoặc vào phiên khác |
| Payload quá lớn, null, NaN, axes lệch độ dài | HTTP đúng contract; không lưu partial payload |
| Mất ACK sau khi ghi file | Retry nhận duplicate, dữ liệu không tăng |
| Crash giữa các bước ghi/index; disk full | Recovery và lỗi có kiểm chứng, không false accepted |
| STOPPING: final batch đến/không đến | Complete/incomplete được phân biệt |

## Điều kiện merge / bàn giao nhánh 07

- [ ] Backend tests có fixtures tạm, concurrency và failure injection cho các cửa sổ lỗi chính.
- [ ] Tài liệu ACK/errors đủ để firmware xử lý retry; ví dụ dùng trong C++ tests.
- [ ] Không regression telemetry/session/simulator; required checks pass.
- [ ] Raw storage thực tế có thể kiểm tra bằng sample count/hash; không chỉ thấy file tồn tại.
- [ ] Commit gợi ý: `feat(backend): persist raw batches idempotently with session validation`.

## Nhật ký / kết quả thực hiện

| Ngày / commit | Task | Command / bằng chứng | Kết quả / blocker |
|---|---|---|---|
| — | — | — | Chưa thực hiện |
