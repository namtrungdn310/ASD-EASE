# Giao diện theo dõi ASD-EASE

Ngày2026-11-05. Áp dụng cho màn hình đang chạy tại localhost5173 và bước mở phiên local.

## Hướng thiết kế

- Giữ nguyên logo đã chọn. Xanh chính#0638D8, xanh lá của logo dành cho nhận diện; trạng thái đang cập nhật dùng xanh lá tối để đọc rõ trên nền sáng.
- Nền sáng, chữ hệ thống có tiếng Việt, số tabular. Không tải font ngoài; không thêm hero, sidebar giả hoặc nút dẫn tới chức năng chưa có.
- Khoảng cách, viền12px và kích thước chữ dùng chung toàn trang. Các ô dữ liệu cùng chiều cao phần số và biểu đồ.
- Skill ui-ux-pro-max đã đọc; kết quả style Minimalism/Swiss phù hợp với bảng điều khiển. Gợi ý dark/glass/marketing của lần design-system không áp dụng vì khác yêu cầu. Tra cứu stack React không có mục khớp; dùng nguyên tắc chung/native controls và kiểm tra component thực.

## Bố cục

1. Đầu trang: logo nhỏ, nguồn giả lập nếu có và trạng thái thiết bị Đã kết nối/Chưa kết nối. Chỉ live mới được báo Đã kết nối; không suy từ Wi-Fi/MQTT hay việc socket mở đơn thuần.
2. Thanh ngữ cảnh: tiêu đề, số mẫu đang xem và chọn thiết bị. Bên dưới là khung Phiên tự động đọc trạng thái backend/mã session trong telemetry; không có nút Start/Stop theo yêu cầu Trung. Không lặp mã phiên ở cả hai nơi.
3. Bốn ô cảm biến dùng hết chiều rộng cửa sổ, không giới hạn1280px: từ1600px bốn cột,761..1599px hai cột và<=760px một cột. Mỗi ô gắn số đo với biểu đồ ngay bên dưới; giữ lề co giãn thay khoảng trống lớn hai bên.
4. Gia tốc/tốc độ xoay có độ lớn chính và ba trục có dấu. Đơn vị xuất hiện cùng số chính; chỉ ghi trọng lực một lần dưới vùng số đo.
5. Khung Dự đoán AI luôn có dưới cảm biến: trạng thái dự đoán, xác suất và lịch sử. Khi chưa có mô hình/mẫu hợp lệ hiển thị dấu — và chỗ chờ, không dựng đường hoặc phần trăm giả. Khung có dữ liệu sẽ dùng prediction/model_version từ telemetry hiện có. Thông tin thiết bị thu gọn chỉ giữ chất lượng và phiên bản.
6. Một dòng ghi mục đích nghiên cứu ở chân trang.

## Dữ liệu và trạng thái

- Badge thiết bị có hai nhãn công khai: Đã kết nối khi live, Chưa kết nối cho waiting/stale/backend_disconnected. Vẫn giữ trạng thái chi tiết ở tooltip/screen reader và thông báo ngữ cảnh. Dùng freshness hiện có: mẫu mới hợp lệ của thiết bị được chọn trong5 giây và thuộc kết nối hiện tại; gói trùng/pong không làm mới. Badge có chữ/icon, giữ aria-live khi đổi trạng thái.
- Khi cũ/mất kết nối/chờ sau reconnect, giữ số đo/history trước đó cùng một thông báo rõ; không dùng dự đoán/chất lượng cũ làm hiện tại.
- Null là dấu — và khoảng trống trên đường vẽ; số0 vẫn là số0. Mẫu đầu có điểm riêng, không tạo đường giả.
- Trục thời gian phút:giây từ epoch thiết bị. Lấy tối đa5 mốc từ mẫu thực, bỏ nhãn trùng; không dồn nhãn có nhiều chữ số thập phân. Khoảng thời gian được mở rộng khi chỉ có một mẫu.
- Ba trục dùng tên và kiểu nét khác nhau ngoài màu. Bật accessibility layer của Recharts; số hiện tại đọc được độc lập với biểu đồ.
- DEVICE/modelnone/cả3 quality0 theo quy ước firmware hiện tại hiển thị Chưa đánh giá; không biến thành chất lượng tốt hoặc lỗi cảm biến. Sau này có estimator thật cần phân biệt rõ0 đo được với trạng thái chưa đánh giá.
- Khung AI có ba trạng thái chuẩn bị/chạy/tạm ngưng. DEVICE/modelnone luôn để trạng thái và xác suất trống; có model nhưng chưa có xác suất vẫn giữ null, không hiện0 thay thiếu. Có model/nguồn giả lập và history xác suất thì vẽ lịch sử; không có thì giữ vùng chờ. Mất live thì ẩn nhãn/kết quả hiện tại, lịch sử vẫn giữ với ghi chú Dữ liệu trước đó. Dữ liệu giả lập luôn được nhận diện, không biến thành kết quả AI thật vì model_version=none.
- Giữ4 nhãn theo contract: Bình thường/Cần chú ý/Chưa xác định/Đang hiệu chuẩn. Xác suất0 và1 lần lượt là0%/100%, không phải độ chính xác của mô hình. Không tự suy trạng thái từ HR/GSR/điểm chuyển động hoặc đặt ngưỡng y khoa trên giao diện.
- Phiên tự mở ở backend theo boot của ESP; browser chỉ GET trạng thái. Không báo phiên đang hoạt động chỉ từ HTTP202: phải có telemetry mới cùng session và trạng thái phù hợp. Đổi thiết bị reset phần đọc phiên, không giữ nhầm mã thiết bị trước; đóng/mở tab không tạo phiên mới. Xem docs/integration/05-AUTOMATIC-SESSIONS.md.

## Màn hình và thao tác

- Bố cục fluid toàn chiều rộng; bốn cột từ1600px, hai cột ở màn hình vừa và một cột<=760px. Khung AI hai phần trên desktop, xếp dọc trên mobile. <=480px gom chọn thiết bị theo hàng riêng, trục có thể xếp nhãn trên số. Đây là chiều rộng viewport, không tự gọi browser Fullscreen hoặc ẩn thanh trình duyệt.
- Chọn thiết bị cao44px, summary ít nhất52px, nút thử lại44px. Dùng bàn phím được, có focus xanh rõ và skip link.
- Đường biểu đồ không có animation; giảm motion theo hệ điều hành. Không thay thuật toán, nhịp đo hoặc giao thức vì thay giao diện.
- Trang chờ/mở phiên và lỗi dịch vụ cùng kiểu chữ/màu/viền với Dashboard; nút retry giữ xử lý và cleanup sẵn có.

## Kiểm tra

- PASS:60 frontend tests, gồm hook thật với DOM/StrictMode, đổi thiết bị, stale/reconnect, vector âm/0/null, độ lớn, mở/đóng thông tin, quality chưa đánh giá và khung AI. Có ca chuyển từ modelnone sang mô hình test rồi mất live, xác suất0/1/null, nguồn giả lập, lịch sử cũ, phiên tự động chỉ đọc backend và nhãn kết nối chỉ bật sau mẫu mới. Build TypeScript/Vite đạt.
- PASS: độ tương phản chữ chính/muted/status được tính, thấp nhất4.72:1 trong các màu đã kiểm tra; focus/nút dùng màu brand tương phản cao. Viền chọn thiết bị tăng tương phản.
- PASS: HTTP giao diện/CSS/module và cookie→WS nhận3 frame DEVICE schema1.1 thật, đủ hai vector. Không công bố số sinh học thật trong fixture/PR.
- Giới hạn: Browser runtime không có trình duyệt khả dụng (list rỗng). Chưa chụp/đo bố cục thật tại375/768/1440px, chưa kiểm chứng bằng screen reader. DOM không tính layout; không coi tests là bằng chứng pixel hoặc chứng nhận WCAG.
- Cần đối chiếu trực quan sau tải lại trang; giữ các kích thước trên như mục tiêu CSS, chưa đánh dấu viewport QA đã chạy.
