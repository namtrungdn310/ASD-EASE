# Số mẫu cảm biến trên Dashboard

Mỗi thẻ hiển thị `số mẫu · % chất lượng`, cùng cửa sổ 8 giây đã hoàn tất trên ESP. Không đếm gói telemetry, điểm biểu đồ, mẫu cache hoặc HR tạm tính.

- HR: mẫu PPG thực đọc sau gộp FIFO, không phải số lần tìm được nhịp tim.
- Điện da: mỗi lần đọc ADC hoàn tất tính là một mẫu GSR; các lần ADC con dùng để lấy trung bình không tính riêng.
- Gia tốc và tốc độ xoay: mỗi vector ba trục là một mẫu, không nhân ba. Hai thẻ dùng cùng lượt đọc IMU.

`signal_quality.hr/gsr/acceleration/rotation.sample_count` là số nguyên không âm hoặc null, được bổ sung tùy chọn trong telemetry 1.2. Firmware cũ không gửi trường này vẫn được nhận. Frontend cũ kiểm tra khóa nghiêm ngặt cần cập nhật cùng backend trước khi nạp firmware mới.

Firmware đếm trực tiếp trong các bucket của QualityWindow; loại bucket hiện tại để cửa sổ khớp phép tính chất lượng. Khi mới khởi động, số mẫu có thể ít hơn cửa sổ đầy. Khi chưa có phép thu, dữ liệu cũ hoặc snapshot hết hạn, giao diện hiện `— mẫu`.

Thu đủ mẫu không có nghĩa có tiếp xúc da, sóng mạch rõ hoặc HR chính xác. PPG có thể thu đủ mẫu trong khi chất lượng 0%. Không suy ra số mẫu bằng Hz nhân thời gian và không tính phần trăm chất lượng từ số gói nhận ở web.

Kiểm tra: `scripts/check_measurement_quality.py`, `backend/tests/test_metric_quality.py`, `frontend/tests/metric-quality.test.mjs`. Khi cập nhật, build backend rồi nạp bằng `npm run device:flash`; dữ liệu tiếp tục truyền bằng Wi-Fi/MQTT.
