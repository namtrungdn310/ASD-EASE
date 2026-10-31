# Giai đoạn 00 — Kiểm chứng phần cứng

## Trạng thái

NOT_STARTED

## Người phụ trách

Tân — Tự động hoá

## Mục tiêu

Kiểm tra board ESP32-S3 Super Mini đã mua; ghi nhận chip, bộ nhớ, chân kết nối, USB và nguồn.

## Lý do

Tránh cấu hình phần cứng dựa trên phỏng đoán.

## Phụ thuộc

Không.

## Đầu vào

Board thật, cáp, đồng hồ đo và PlatformIO trên máy.

## Công việc

- [ ] Làm đúng phạm vi đã thống nhất.
- [ ] Chạy các kiểm thử và lưu bằng chứng.
- [ ] Cập nhật tài liệu giai đoạn, tiến độ, thay đổi và quyết định liên quan.

## File dự kiến thay đổi

ai/edge_firmware/include/pins.h; docs/HARDWARE_PROFILE.md

## Lưu ý triển khai

Chạy HardwareProfiler trên board; kiểm tra chân bằng phép đo và lưu kết quả.

## Kiểm thử

Kiểm tra nhận dạng chip, bộ nhớ, I2C, ADC, USB và nguồn; lưu lệnh cùng kết quả.

## Điều kiện nghiệm thu

- [ ] Có bằng chứng thật cho mục tiêu.
- [ ] Các kiểm thử bắt buộc đều đạt.
- [ ] Cập nhật tiến độ và rủi ro trước khi chuyển tiếp.

## Đầu ra

Phần triển khai có thể review, kết quả kiểm thử và tiến độ đã cập nhật. Không tự chuyển sang giai đoạn sau khi chưa có yêu cầu.

## Rủi ro

Board hoặc sơ đồ chân có thể khác thông tin người bán.

## Xử lý lỗi và khôi phục

Đánh dấu cấu hình chưa xác minh; kiểm tra ký hiệu board, nhật ký khởi động và dây nối.

## Kết quả

Chưa thực hiện.

## Bằng chứng hoàn thành

Chưa có bằng chứng nghiệm thu.

## Giai đoạn tiếp theo

Giai đoạn 01 — Khung dự án

