# 08 — Tra cứu, kiểm tra và xuất bản ghi

| Mục | Nội dung |
|---|---|
| Nhánh | `feature/backend-recording-export` |
| Phụ trách | Trung — IT |
| Phụ thuộc |06;07 trước nghiệm thu dữ liệu thật |
| Ước lượng |1–2 ngày |
| Tiến độ |[Dòng08](PROGRESS.md) |

## Kết quả và phạm vi

Đọc lại phiên, xác định đủ/thiếu và xuất raw kèm bản mô tả để xử lý sau. Chưa train mô hình hoặc xây pipeline đặc trưng. Theo [kiến trúc](MQTT_ARCHITECTURE.md), query/export vẫn HTTP và đọc file/chỉ mục, không cần broker online.

API dự kiến: GET /sessions/{session_id}, /sessions/{session_id}/recording, /sessions/{session_id}/export. Chốt response trước frontend09. Thêm dịch vụ đọc/kiểm tra, schema có version, tests, hướng dẫn dataset/giai đoạn08. Có thể xuất JSONL+JSON trong ZIP, không sửa file gốc.

## Tra cứu và kiểm tra

- [ ] List/detail có device, nguồn, trạng thái, thời gian thu/nhận, số mẫu và lý do thiếu; không trả toàn raw trong danh sách.
- [ ] Có phân trang/lọc device/nguồn, không trộn phiên.
- [ ] Đọc theo chỉ mục; file thiếu/hash sai phải báo, không bỏ rồi gọi đủ.
- [ ] Ghép đúng thứ tự, phát hiện chồng lấp, khoảng trống, clock reset và khoá trùng.
- [ ] Giữ null/vị trí thiếu; nội suy/lấy mẫu lại là bước dẫn xuất riêng.
- [ ] Đối chiếu DB/file/count với cutoff/final batch; STOPPED chưa chắc đủ.
- [ ] Tổng kết MQTT trước/sau raw HTTP/lặp cho cùng kết quả; presence/PUBACK/chartlive không chứng minh raw đủ.
- [ ] Có đường đọc/chuyển JSONL cũ rõ, không xoá file chưa nhận dạng.

## Bản mô tả và xuất

- [ ] Có phiên bản định dạng/schema, phiên/thiết bị/nguồn, firmware/cấu hình và nguồn đo thật.
- [ ] Ghi transport/phiên bản client/broker khi biết; thiếu thì unknown/null, không token/key hoặc thông tin riêng.
- [ ] Ghi đơn vị, tốc độ danh định/đã đo, trung bình/lọc tại driver, mốc thời gian và ý nghĩa null.
- [ ] Ghi số mẫu/batch, khoảng ID, mất/thử lại đã đối chiếu và trạng thái đủ/thiếu.
- [ ] Dùng ID người giả danh nếu có, không đòi tên thật và không điền giả.
- [ ] SYNTHETIC giữ bộ sinh/seed khi có thật, không đoán.
- [ ] Hash/commit/cấu hình có căn cứ; hash không chứng minh phép đo đúng.
- [ ] Mặc định xuất phiên đã đóng; nếu hỗ trợ phiên đang chạy phải có cutoff rõ.
- [ ] Ghi/chuyển từng phần hoặc file tạm có hạn, không nạp cả dataset vào RAM; chỉ dọn file xuất tạm.
- [ ] Tải theo ID hợp lệ, không cho client chọn filesystem path.
- [ ] Có loader/kiểm tra offline đối chiếu mẫu/thứ tự; chưa nối train/evaluation.

## Kiểm thử và nghiệm thu

| Ca | Kết quả |
|---|---|
| Nhận mẫu→xuất→đọc lại | Số, thứ tự, giá trị, null, đơn vị giữ nguyên |
| Retry/đến sai thứ tự | Không nhân đôi, đúng thứ tự |
| Mất/hỏng file/hash sai | Báo thiếu và vấn đề rõ |
| DEVICE/SYNTHETIC | Lọc/xuất riêng, nguồn đúng |
| Backend restart/broker offline | Đọc được dữ liệu đã lưu |
| Phiên lớn hơn RAM thử | Không nạp nguyên bộ |
| Phiên chạy/Stop chưa gửi nốt | Từ chối hoặc snapshot theo quy tắc, không ngầm gọi đủ |

- [ ] Tests có đối chiếu thật và ca lỗi, không chỉ HTTP200.
- [ ] Tài liệu API/types đủ cho09, dữ liệu cũ đọc được hoặc chuyển đổi đã thử.
- [ ] CI đạt, nghiệm thu bản ghi thật ghi riêng khi còn chờ board.
- [ ] Commit gợi ý: `feat(backend): kiểm tra và xuất bản ghi kèm mô tả`.

Xuất là sản phẩm dẫn xuất; tắt API/khôi phục reader không đổi raw. Giữ file hỏng và trạng thái để điều tra, không xoá âm thầm.

## Nhật ký

| Ngày/commit | Việc | Bằng chứng | Kết quả |
|---|---|---|---|
|—|—|—|Chưa thực hiện|
