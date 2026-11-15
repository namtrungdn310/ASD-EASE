# Bố cục theo dõi thiết bị và báo cáo AI

## Trang Thiết bị

- Sidebar chứa logo, hai mục Thiết bị/Báo cáo AI và nút Thu gọn ngay bên dưới. Thẻ firmware, gói dữ liệu, thời gian thiết bị và ghi chú nghiên cứu nằm cuối sidebar. Thu/mở dùng 150ms, tắt hiệu ứng theo tùy chọn giảm chuyển động.
- Header giữ mã phiên, chọn thiết bị và nút kết nối/ngắt kết nối.
- Màn hình desktop từ 1120px: vùng trái chứa bốn thẻ HR/GSR/gia tốc/tốc độ xoay; cột AI rộng 250–280px. Thu gọn cột thông số và khoảng cách để ưu tiên vùng vẽ. Các biểu đồ luôn có 5 mốc, chia cửa sổ 60 giây thành 4 khoảng 15 giây.
- Chiều cao bố cục theo viewport, vùng biểu đồ co theo thẻ. Ba đồ thị gia tốc chia chiều cao thực tế của vùng chứa, dùng chung trục thời gian.
- Màn hình nhỏ có bố cục thích ứng và cuộn để không cắt mất thông số. Không ép màn hình điện thoại vào bố cục desktop.
- Chuyển trang bằng hash `#devices` / `#reports`; hook theo dõi thiết bị nằm ở lớp chung nên chuyển trang không ngắt WebSocket.

## Trang Báo cáo AI

- Đọc lịch sử phân trang từ API `/api/v1/reports/ai?device_id=...&page=...`, không tạo dữ liệu mẫu trên giao diện. `/events` vẫn được giữ để tương thích API cũ.
- Chỉ lấy `ATTENTION` có xác suất; không đưa `NORMAL`, `UNCERTAIN`, `CALIBRATING` hoặc bản ghi thiếu xác suất vào danh sách cảnh báo.
- Giao thức hiện chỉ hỗ trợ mức cảnh báo Cần chú ý. Không tự suy thêm mức nghiêm trọng hoặc kết luận rối loạn.
- Biểu đồ dùng các điểm xác suất tại thời điểm backend ghi nhận, không nối đường qua các khoảng không có cảnh báo. Trục thời gian báo cáo là thời gian UTC của bản ghi, hiển thị theo múi giờ trình duyệt; khác với thời gian tương đối trên thiết bị.
- Biểu đồ và bảng nằm chung một khung. Bảng có bốn cột: thời điểm, trạng thái cảnh báo, xác suất và lý do. Cột lý do chứa số bản ghi; phần giải thích để trống đến khi AI cung cấp dữ liệu.
- Phân trang từ backend qua `/api/v1/reports/ai`, mặc định 10 nhóm mỗi trang, xem được lịch sử vượt 100 bản ghi. Biểu đồ phản ánh các kết quả trên trang bảng hiện tại. Các bản ghi cùng phiên/thiết bị và cách nhau tối đa 5 giây được gom để đọc gọn; đây là nhóm bản ghi, không phải kết luận một sự kiện sinh lý liên tục. Không lưu thêm lịch sử vào localStorage.
- Khung biểu đồ và bảng là hai thẻ riêng. Bảng có các cột Thời điểm, Khoảng thời gian, Trạng thái cảnh báo, Xác suất và Lý do; phần rộng còn lại dành cho Lý do. Khoảng thời gian là mốc đầu–cuối nhóm bản ghi, không khẳng định đó là thời lượng bất thường sinh lý.
- Thẻ dự đoán hiển thị Trạng thái dự đoán, Khoảng thời gian và Xác suất. Khoảng thời gian hiện là `—` vì telemetry chưa cung cấp cửa sổ dự đoán. Khi có cảnh báo live, chỉ hiện nút Xem chi tiết; không có thẻ tóm tắt.
- API kiểm tra quyền người vận hành như trước; bổ sung trường xác suất từ cột DB đã tồn tại, không cần migration. Lời gọi `/events` không thêm tham số vẫn giữ hành vi cũ.

## Kiểm tra

- Frontend build đạt; còn cảnh báo kích thước bundle trên 500kB.
- Các ca báo cáo, điều hướng giữ theo dõi, trục biểu đồ, SVG gia tốc và hiển thị telemetry đã chạy với React/Recharts và ngoại vi mạng giả trong test.
- Hai ca API backend kiểm tra quyền truy cập, lọc trước giới hạn 100 bản ghi và tương thích lời gọi cũ đã đạt.
- Công cụ Browser không có trình duyệt khả dụng trong phiên thực hiện; chưa kiểm tra bằng ảnh trên màn hình thật. Kiểm tra DOM/SVG không thay thế kiểm tra bố cục bằng browser.
