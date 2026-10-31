# Giai đoạn 20 — Trình diễn không dây

## Trạng thái

NOT_STARTED

## Người phụ trách

Trung và Tân

## Mục tiêu

Trình diễn ESP32 dùng pin cùng dashboard laptop trên Wi-Fi cục bộ không Internet.

## Lý do

Kiểm chứng mô hình kết nối dùng khi thi đấu.

## Phụ thuộc

Giai đoạn 19, Giai đoạn 07

## Đầu vào

Router/LAN cục bộ, thiết bị dùng pin và phần mềm trên laptop.

## Công việc

- [ ] Làm đúng phạm vi đã thống nhất.
- [ ] Chạy các kiểm thử và lưu bằng chứng.
- [ ] Cập nhật tài liệu giai đoạn, tiến độ, thay đổi và quyết định liên quan.

## File dự kiến thay đổi

docs/COMPETITION_MODE_TEST.md

## Lưu ý triển khai

Ngắt Internet và USB; laptop chỉ nhận/lưu/hiển thị, không suy luận cuối.

## Kiểm thử

Thực hiện các mục phù hợp của danh sách kiểm tra thi đấu.

## Điều kiện nghiệm thu

- [ ] Có bằng chứng thật cho mục tiêu.
- [ ] Các kiểm thử bắt buộc đều đạt.
- [ ] Cập nhật tiến độ và rủi ro trước khi chuyển tiếp.

## Đầu ra

Phần triển khai có thể review, kết quả kiểm thử và tiến độ đã cập nhật. Không tự chuyển sang giai đoạn sau khi chưa có yêu cầu.

## Rủi ro

Tường lửa, chặn các máy trong router, IP đổi hoặc phụ thuộc USB.

## Xử lý lỗi và khôi phục

Dùng cấu hình LAN trình diễn đã ghi và kiểm tra từng thành phần.

## Kết quả

Chưa thực hiện.

## Bằng chứng hoàn thành

Chưa có bằng chứng nghiệm thu.

## Giai đoạn tiếp theo

Giai đoạn 21 — Khả năng phục hồi kết nối

