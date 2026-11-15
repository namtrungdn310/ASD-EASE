# Quy tắc chữ trên Dashboard

Nguồn duy nhất: `frontend/src/typography.css`. `styles.css` quản lý bố cục, không khai báo cỡ chữ/độ đậm riêng theo thẻ hoặc breakpoint. Font Segoe UI và các font hệ thống dự phòng, không tải thêm font ngoài.

| Vai trò | Cỡ chữ | Độ đậm | Giãn dòng |
|---|---|---|---|
| Tiêu đề thẻ, tiêu đề lịch sử | 14px | 600 | 1,4 |
| Điều hướng | 14px | 500; mục đang chọn 600 | 1,4 |
| Nội dung bảng, trạng thái, chọn thiết bị, mã phiên | 13px | 400; tên và giá trị metadata 500 | 1,5 |
| Nút thao tác | 13px | 600 | 1,4 |
| Nhãn phụ, đơn vị, phần trăm chất lượng, ghi chú, trục biểu đồ | 12px | 400; giá trị chất lượng và tiêu đề cột 600 | 1,5 |
| Số đo chính và xác suất AI | 32px | 600 | 1,2 |
| Trạng thái AI có kết quả | 20px | 600 | 1,4 |
| Dấu thiếu giá trị chính | 32px | 400 | 1,2 |

## Cách áp dụng

- Tên thẻ cùng cấp dùng cùng cỡ chữ và độ đậm; không làm tiêu đề AI nổi hơn tiêu đề cảm biến chỉ vì nằm ở cột khác.
- Dùng ba độ đậm 400/500/600. Không dùng 650 hoặc tăng đậm tùy từng thành phần.
- Giá trị chính và tiêu đề dùng màu chữ chính; nhãn/đơn vị/ghi chú dùng màu phụ. Xanh thương hiệu dành cho thao tác và mục đang chọn. Màu cảnh báo phản ánh trạng thái, không dùng để trang trí chữ thường.
- Số đo, mã phiên, phần trăm và thời điểm dùng chữ số rộng đều để không nhảy ngang khi cập nhật.
- Trạng thái trống không có độ đậm như cảnh báo. Các dấu trống trong thẻ AI và số đo tuân theo cùng vai trò.
- Khi màn hình hẹp, thay bố cục hoặc cho phép xuống dòng; không giảm chữ phụ xuống 10–11px.
- Nhãn trục và tooltip Recharts đọc cùng biến typography với phần còn lại của Dashboard.

## Kiểm tra lần áp dụng

Frontend build và 48 ca kiểm tra báo cáo/điều hướng/telemetry/biểu đồ đã đạt. Chưa có trình duyệt khả dụng để kiểm ảnh sau chỉnh; kiểm DOM và SVG không xác nhận được toàn bộ bố cục chữ theo pixel.
