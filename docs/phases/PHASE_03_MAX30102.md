# Giai đoạn 03 — MAX30102

## Trạng thái

IN_PROGRESS

## Người phụ trách

Tân — Tự động hoá

## Mục tiêu

Thu và kiểm chứng mẫu PPG red/IR của MAX30102 trên board thật.

## Lý do

Cung cấp tín hiệu PPG cho các bước xử lý và tích hợp.

## Phụ thuộc

Giai đoạn 00, Giai đoạn 02

## Đầu vào

Board, chân I2C và dây nối MAX30102 đã được kiểm chứng.

## Công việc

- [ ] Làm đúng phạm vi đã thống nhất.
- [ ] Chạy các kiểm thử và lưu bằng chứng.
- [ ] Cập nhật tài liệu giai đoạn, tiến độ, thay đổi và quyết định liên quan.

## File dự kiến thay đổi

ai/edge_firmware/src/sensors/MAX30102Sensor.cpp

## Lưu ý triển khai

Đã có đọc FIFO, phát hiện tiếp xúc, ước tính nhịp tim, lọc trung vị/EMA và SpO2 trong PR #7 (`332f249`), sau đó được cập nhật ở PR #11. Chưa có bằng chứng nghiệm thu mẫu thô, mất kết nối, tốc độ sau averaging hoặc độ chính xác trên phần cứng.

## Kiểm thử

Build/nạp firmware, quét I2C, thu mẫu có thứ tự, thử ngắt cảm biến và thay đổi tiếp xúc.

## Điều kiện nghiệm thu

- [ ] Có bằng chứng thật cho mục tiêu.
- [ ] Các kiểm thử bắt buộc đều đạt.
- [ ] Cập nhật tiến độ và rủi ro trước khi chuyển tiếp.

## Đầu ra

Phần triển khai có thể review, kết quả kiểm thử và tiến độ đã cập nhật. Không tự chuyển sang giai đoạn sau khi chưa có yêu cầu.

## Rủi ro

Sai địa chỉ I2C, điện áp, tiếp xúc hoặc thời gian lấy mẫu.

## Xử lý lỗi và khôi phục

Kiểm tra riêng I2C tối thiểu, nguồn và điện trở kéo lên.

## Kết quả

Đã đọc phần triển khai từ PR #7; build trên máy đạt. Chưa có biên bản kiểm thử trên board đáp ứng các mục bên trên.

## Bằng chứng hoàn thành

Cần lưu board, commit, cấu hình, mẫu có thứ tự, số đo thời gian và thử ngắt cảm biến. Chưa đủ để đánh dấu DONE.

## Giai đoạn tiếp theo

Giai đoạn 04 — MPU6050

