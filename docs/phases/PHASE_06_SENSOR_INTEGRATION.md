# Giai đoạn 06 — Tích hợp cảm biến

## Trạng thái

IN_PROGRESS

## Người phụ trách

Tân — Tự động hoá

## Mục tiêu

Chạy ba cảm biến với thời gian thu được kiểm soát và đồng bộ.

## Lý do

Ghi dữ liệu và trích đặc trưng cần các luồng cùng mốc thời gian.

## Phụ thuộc

Giai đoạn 03–05

## Đầu vào

Driver đã kiểm chứng và mục tiêu thời gian lấy mẫu.

## Công việc

- [ ] Làm đúng phạm vi đã thống nhất.
- [ ] Chạy các kiểm thử và lưu bằng chứng.
- [ ] Cập nhật tài liệu giai đoạn, tiến độ, thay đổi và quyết định liên quan.

## File dự kiến thay đổi

ai/edge_firmware/src/sensors/...; ai/edge_firmware/src/processing/...

## Lưu ý triển khai

PR #7 (`332f249`) có vòng đọc chung, hai bus I2C, ADC và báo Serial mỗi giây. Nhịp cấu hình không chứng minh nhịp đo, đồng bộ hoặc không mất mẫu. Phần mạng và bộ đệm raw do IT triển khai sau, cần đo ảnh hưởng riêng.

## Kiểm thử

Build/nạp toàn hệ thống; kiểm tra số mẫu, tốc độ, timestamp và tải đồng thời I2C/ADC.

## Điều kiện nghiệm thu

- [ ] Có bằng chứng thật cho mục tiêu.
- [ ] Các kiểm thử bắt buộc đều đạt.
- [ ] Cập nhật tiến độ và rủi ro trước khi chuyển tiếp.

## Đầu ra

Phần triển khai có thể review, kết quả kiểm thử và tiến độ đã cập nhật. Không tự chuyển sang giai đoạn sau khi chưa có yêu cầu.

## Rủi ro

Tranh chấp I2C, lệnh đọc chặn, thiếu bộ nhớ hoặc trễ lịch lấy mẫu.

## Xử lý lỗi và khôi phục

Tắt lần lượt từng cảm biến và quan sát bộ đếm thời gian.

## Kết quả

Đã đọc phần triển khai từ PR #7; build trên máy đạt. Chưa có biên bản kiểm thử trên board đáp ứng các mục bên trên.

## Bằng chứng hoàn thành

Cần lưu board, commit, cấu hình, mẫu có thứ tự, số đo thời gian và thử ngắt cảm biến. Chưa đủ để đánh dấu DONE.

## Giai đoạn tiếp theo

Giai đoạn 07 — Kết nối Wi-Fi với backend

