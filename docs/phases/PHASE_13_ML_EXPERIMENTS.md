# Giai đoạn 13 — Thử nghiệm học máy

## Trạng thái

NOT_STARTED

## Người phụ trách

Trung — IT

## Mục tiêu

Thử các mô hình nhỏ và ghi rõ nguồn dữ liệu.

## Lý do

Kiểm tra học máy có cải thiện so với quy tắc hay không.

## Phụ thuộc

Giai đoạn 12

## Đầu vào

Đặc trưng và cách chia tập tránh lộ dữ liệu.

## Công việc

- [ ] Làm đúng phạm vi đã thống nhất.
- [ ] Chạy các kiểm thử và lưu bằng chứng.
- [ ] Cập nhật tài liệu giai đoạn, tiến độ, thay đổi và quyết định liên quan.

## File dự kiến thay đổi

ai/src/training/...; ai/models/experiments/...

## Lưu ý triển khai

Thử hồi quy logistic, cây quyết định và rừng ngẫu nhiên nhỏ. Mô hình chỉ học dữ liệu giả lập phải ghi SYNTHETIC_ONLY.

## Kiểm thử

Kiểm tra chạy lại, rà soát chia tập và đánh giá riêng từng nguồn.

## Điều kiện nghiệm thu

- [ ] Có bằng chứng thật cho mục tiêu.
- [ ] Các kiểm thử bắt buộc đều đạt.
- [ ] Cập nhật tiến độ và rủi ro trước khi chuyển tiếp.

## Đầu ra

Phần triển khai có thể review, kết quả kiểm thử và tiến độ đã cập nhật. Không tự chuyển sang giai đoạn sau khi chưa có yêu cầu.

## Rủi ro

Dữ liệu giả lập có thể làm nhãn dễ đoán hoặc khiến chọn mô hình thiên lệch.

## Xử lý lỗi và khôi phục

Bỏ cột lộ đáp án; tăng sự chồng lấp kịch bản và giữ tập đánh giá thật riêng.

## Kết quả

Chưa thực hiện.

## Bằng chứng hoàn thành

Chưa có bằng chứng nghiệm thu.

## Giai đoạn tiếp theo

Giai đoạn 14 — Chọn mô hình

