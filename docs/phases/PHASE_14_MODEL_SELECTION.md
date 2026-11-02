# Giai đoạn 14 — Chọn mô hình

## Trạng thái

NOT_STARTED

## Người phụ trách

Trung và Tân

## Mục tiêu

Chọn hoặc loại mô hình dựa trên kết quả đo và giới hạn triển khai.

## Lý do

Mô hình phức tạp nhất hoặc F1 cao nhất chưa chắc phù hợp trên thiết bị.

## Phụ thuộc

Giai đoạn 13

## Đầu vào

Kết quả đối chứng/ML, dung lượng, độ trễ và mức dễ giải thích.

## Công việc

- [ ] Làm đúng phạm vi đã thống nhất.
- [ ] Chạy các kiểm thử và lưu bằng chứng.
- [ ] Cập nhật tài liệu giai đoạn, tiến độ, thay đổi và quyết định liên quan.

## File dự kiến thay đổi

ai/src/evaluation/...; docs/PROGRESS.md

## Lưu ý triển khai

So precision, recall, F1, cảnh báo sai, dung lượng, độ trễ, bộ nhớ và ổn định khi có phép đo. Kết quả chỉ từ giả lập không đủ chọn mô hình cuối cho dữ liệu thật.

## Kiểm thử

Chạy lại trên tập thật giữ riêng; rà soát lỗi, cách tách người/phiên/lần đo và nguồn huấn luyện.

## Điều kiện nghiệm thu

- [ ] Có bằng chứng thật cho mục tiêu.
- [ ] Các kiểm thử bắt buộc đều đạt.
- [ ] Cập nhật tiến độ và rủi ro trước khi chuyển tiếp.

## Đầu ra

Phần triển khai có thể review, kết quả kiểm thử và tiến độ đã cập nhật. Không tự chuyển sang giai đoạn sau khi chưa có yêu cầu.

## Rủi ro

Chỉ chọn chỉ số đẹp hoặc chọn mô hình hoàn toàn từ giả lập.

## Xử lý lỗi và khôi phục

Quay lại danh sách thử nghiệm và tiêu chí đã đặt trước.

## Kết quả

Chưa thực hiện.

## Bằng chứng hoàn thành

Chưa có bằng chứng nghiệm thu.

## Giai đoạn tiếp theo

Giai đoạn 15 — Xuất mô hình
