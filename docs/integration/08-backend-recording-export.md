# 08 — Tra cứu, kiểm tra và export recording

| Thuộc tính | Giá trị |
|---|---|
| Nhánh | `feature/backend-recording-export` |
| Chủ trì | Trung — IT |
| Phụ thuộc | 06; 07 trước nghiệm thu dataset từ thiết bị |
| Ước lượng | 1–2 ngày |
| Theo dõi | [PROGRESS.md](PROGRESS.md), dòng 08 |

## Kết quả cần đạt

Đọc lại một phiên đã ghi, xác định dữ liệu đầy đủ/thiếu và xuất recording + manifest để xử lý offline sau này. Không gộp việc train model hay xây feature pipeline vào PR này.

## File / API đề xuất

- Backend service đọc recording/manifest và API session detail/recording/export; schema response có version rõ.
- Endpoint dự kiến: `GET /sessions/{session_id}`, `/sessions/{session_id}/recording`, `/sessions/{session_id}/export`; chốt shape cụ thể trong contract trước khi frontend dùng.
- DB index từ 06, tests round-trip/streaming export, `docs/DATASET_PROTOCOL.md` và Phase 08.
- Format xuất đề xuất: raw JSONL theo contract + manifest JSON, có thể đóng gói ZIP khi tải. Không đổi file gốc sau khi xuất.

## Checklist query/validation

- [ ] List/detail trả device, origin, state, acquisition time, receiving time, counts và complete/incomplete reason; không trả toàn bộ raw array trong list sessions.
- [ ] Phân trang list; chọn device/origin để query; không trộn data giữa phiên.
- [ ] Xây recording reader theo index, hỗ trợ phát hiện missing file/hash mismatch, không tự bỏ file hỏng rồi báo complete.
- [ ] Ghép batch theo thứ tự contract; detect overlap/gap/reset timestamp và duplicate key.
- [ ] Giữ null/missing samples ở vị trí đúng. Nếu có lựa chọn resample/fill thì thuộc bước xử lý riêng, không sửa raw export.
- [ ] Đối chiếu count/index/file và cutoff/final batch; phân biệt STOPPED với recording complete.
- [ ] Dữ liệu legacy từ JSONL cũ có đường đọc/migration được mô tả; không xoá file không nhận dạng.

## Checklist manifest/export

- [ ] Manifest có export-format version, wire schema, session/device/origin, firmware/config và metadata nguồn đo có thực.
- [ ] Lưu đơn vị, measured/nominal rate phân biệt, FIFO averaging/filtering ở driver, timestamp epoch và null semantics.
- [ ] Ghi counts, batch ID range, gap/drop/retry counters đã xác minh, trạng thái complete/incomplete và lý do.
- [ ] Metadata người tham gia giả danh khi có, không yêu cầu tên thật để export; thiếu thông tin không tự điền giả.
- [ ] Export SYNTHETIC giữ generator/seed nếu thực có; field không có nguồn trả unknown/null thay vì đoán.
- [ ] Ghi hash file/manifest và commit/config tham chiếu khi biết; không tự tuyên bố hash chứng minh tính đúng của phép đo.
- [ ] Default chỉ export phiên đã đóng hoặc tạo snapshot cutoff rõ ràng nếu cho phép export phiên đang chạy.
- [ ] Streaming/chunked hoặc file tạm hữu hạn để không load cả dataset vào RAM; cleanup file export tạm, không xoá raw.
- [ ] Kiểm soát đường tải theo ID đã validate, không cho request chọn filesystem path tuỳ ý.
- [ ] Cung cấp loader/script kiểm tra recording offline để đối chiếu samples/order. Chưa nối train/evaluation.

## Ma trận kiểm thử

| Test | Kết quả mong đợi |
|---|---|
| Ingest fixture -> export -> load | Count, order, value, null và units giữ nguyên |
| Out-of-order arrival / retry | Export không nhân đôi và đúng order |
| Mất batch / file hỏng / hash sai | Incomplete và danh sách vấn đề rõ, không false success |
| Session DEVICE và SYNTHETIC | Chọn/export riêng, manifest provenance đúng |
| Backend restart | Index/recording vẫn đọc được |
| Phiên lớn hơn RAM giả lập nhỏ | Export không đọc nguyên bộ vào memory |
| Phiên đang chạy/stop chưa drain | Snapshot policy hoặc từ chối rõ theo contract |

## Điều kiện merge

- [ ] Round-trip test có dữ liệu biết trước và failure cases, không chỉ test HTTP 200.
- [ ] API và response types được document cho nhánh 09.
- [ ] Giữ tương thích với recordings đang có hoặc có migration đã kiểm thử.
- [ ] Required checks pass; real-recording verification ghi riêng nếu còn chờ board.
- [ ] Commit gợi ý: `feat(backend): inspect and export sensor recordings with manifests`.

## Rollback

Export là sản phẩm dẫn xuất; tắt endpoint/lùi reader không thay đổi batch gốc. Nếu phát hiện file hỏng, giữ lại và ghi trạng thái để điều tra, không silently delete.

## Nhật ký / kết quả thực hiện

| Ngày / commit | Task | Command / bằng chứng | Kết quả / blocker |
|---|---|---|---|
| — | — | — | Chưa thực hiện |
