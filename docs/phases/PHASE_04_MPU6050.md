# Giai đoạn 04 — MPU6050

## Trạng thái

IN_PROGRESS

## Người phụ trách

Tân — Tự động hoá

## Mục tiêu

Thu gia tốc và vận tốc góc thô, có kiểm tra hiệu chuẩn.

## Lý do

Dùng chuyển động để phân tích nhiễu và cảnh báo sai.

## Phụ thuộc

Giai đoạn 00, Giai đoạn 03

## Đầu vào

Bus I2C và MPU6050 đã được kiểm chứng.

## Công việc

- [ ] Làm đúng phạm vi đã thống nhất.
- [ ] Chạy các kiểm thử và lưu bằng chứng.
- [ ] Cập nhật tài liệu giai đoạn, tiến độ, thay đổi và quyết định liên quan.

## File dự kiến thay đổi

ai/edge_firmware/src/sensors/MPU6050Sensor.cpp

## Lưu ý triển khai

PR #7 (`332f249`) có đọc thanh ghi trên Wire1, dò địa chỉ, đổi đơn vị, EMA và kết nối lại. Gia tốc trước EMA là m/s², gyroscope có degrees/s; raw API dùng g và degrees/s. Có driver chưa chứng minh đã hiệu chuẩn hoặc đúng hướng trục.

## Kiểm thử

Build/nạp firmware; đo khi đứng yên, di chuyển/xoay từng trục và kiểm tra thời gian.

## Điều kiện nghiệm thu

- [ ] Có bằng chứng thật cho mục tiêu.
- [ ] Các kiểm thử bắt buộc đều đạt.
- [ ] Cập nhật tiến độ và rủi ro trước khi chuyển tiếp.

## Đầu ra

Phần triển khai có thể review, kết quả kiểm thử và tiến độ đã cập nhật. Không tự chuyển sang giai đoạn sau khi chưa có yêu cầu.

## Rủi ro

Sai hướng trục, bão hòa thang đo hoặc lỗi bus.

## Xử lý lỗi và khôi phục

Thử cảm biến riêng; kiểm tra địa chỉ, thang đo và dây nối.

## Kết quả

Đã đọc phần triển khai từ PR #7; build trên máy đạt. Chưa có biên bản kiểm thử trên board đáp ứng các mục bên trên.

## Bằng chứng hoàn thành

Cần lưu board, commit, cấu hình, mẫu có thứ tự, số đo thời gian và thử ngắt cảm biến. Chưa đủ để đánh dấu DONE.

## Giai đoạn tiếp theo

Giai đoạn 05 — GSR

