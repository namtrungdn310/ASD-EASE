# Giai đoạn 10 — Xử lý tín hiệu

## Trạng thái

NOT_STARTED

## Người phụ trách

Trung — IT

## Mục tiêu

Viết xử lý tín hiệu và kiểm tra chất lượng dùng chung cho raw thật/giả lập.

## Lý do

Đặc trưng phía sau cần tín hiệu nhất quán và được kiểm tra chất lượng.

## Phụ thuộc

Giai đoạn 09

## Đầu vào

Dữ liệu thô có phiên bản và thông tin tốc độ/thời gian.

## Công việc

- [ ] Làm đúng phạm vi đã thống nhất.
- [ ] Chạy các kiểm thử và lưu bằng chứng.
- [ ] Cập nhật tài liệu giai đoạn, tiến độ, thay đổi và quyết định liên quan.

## File dự kiến thay đổi

ai/src/preprocessing/...; ai/src/signal_quality/...

## Lưu ý triển khai

Dùng cùng giao diện cho hai nguồn; giữ thứ tự, thời gian và vị trí mẫu thiếu.

## Kiểm thử

Kiểm thử hàm, tình huống biên giả lập và quan sát tín hiệu thật; không kết luận thực tế chỉ từ giả lập.

## Điều kiện nghiệm thu

- [ ] Có bằng chứng thật cho mục tiêu.
- [ ] Các kiểm thử bắt buộc đều đạt.
- [ ] Cập nhật tiến độ và rủi ro trước khi chuyển tiếp.

## Đầu ra

Phần triển khai có thể review, kết quả kiểm thử và tiến độ đã cập nhật. Không tự chuyển sang giai đoạn sau khi chưa có yêu cầu.

## Rủi ro

Bộ lọc làm méo tín hiệu, mất mẫu, lộ dữ liệu hoặc tách logic theo nguồn.

## Xử lý lỗi và khôi phục

So biểu đồ trước/sau xử lý, tắt phép biến đổi nghi gây lỗi.

## Kết quả

Chưa thực hiện.

## Bằng chứng hoàn thành

Chưa có bằng chứng nghiệm thu.

## Giai đoạn tiếp theo

Giai đoạn 11 — Mức nền và đặc trưng

