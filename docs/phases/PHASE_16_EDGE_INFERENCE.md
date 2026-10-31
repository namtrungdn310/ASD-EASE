# Giai đoạn 16 — Suy luận trên thiết bị

## Trạng thái

NOT_STARTED

## Người phụ trách

Trung và Tân

## Mục tiêu

Chạy mô hình trên ESP32; laptop không quyết định trạng thái.

## Lý do

Thực hiện kiến trúc xử lý tại thiết bị đã thống nhất.

## Phụ thuộc

Giai đoạn 15, Giai đoạn 00

## Đầu vào

Giới hạn board đã xác minh, mô hình xuất và đặc trưng C++.

## Công việc

- [ ] Làm đúng phạm vi đã thống nhất.
- [ ] Chạy các kiểm thử và lưu bằng chứng.
- [ ] Cập nhật tài liệu giai đoạn, tiến độ, thay đổi và quyết định liên quan.

## File dự kiến thay đổi

ai/edge_firmware/src/inference/...

## Lưu ý triển khai

Giới hạn bộ nhớ, kiểm tra chất lượng; không giả định có PSRAM khi chưa đo.

## Kiểm thử

Build; chạy đầu vào cố định trên board; đo bộ nhớ và độ trễ.

## Điều kiện nghiệm thu

- [ ] Có bằng chứng thật cho mục tiêu.
- [ ] Các kiểm thử bắt buộc đều đạt.
- [ ] Cập nhật tiến độ và rủi ro trước khi chuyển tiếp.

## Đầu ra

Phần triển khai có thể review, kết quả kiểm thử và tiến độ đã cập nhật. Không tự chuyển sang giai đoạn sau khi chưa có yêu cầu.

## Rủi ro

Thiếu RAM/flash, sai lệch số hoặc watchdog khởi động lại.

## Xử lý lỗi và khôi phục

Tắt nhánh mô hình, kiểm tra từng bước bằng mẫu chuẩn.

## Kết quả

Chưa thực hiện.

## Bằng chứng hoàn thành

Chưa có bằng chứng nghiệm thu.

## Giai đoạn tiếp theo

Giai đoạn 17 — Đối chiếu Python và C++

