# Phân công

## Trung — IT

Quản lý repo/Git, Docker, FastAPI/SQLite, HTTP/WebSocket, dashboard, giả lập dữ liệu, xử lý/đặc trưng, thử nghiệm/xuất mô hình, đối chiếu Python/C++ và kiểm thử tự động.

Mốc tích hợp thiết bị còn gồm: chuẩn hoá đơn vị/timestamp, điều khiển phiên, đóng gói firmware, Wi-Fi/MQTT, raw HTTP, bộ đệm, gửi lại, lưu/xuất dữ liệu. Xem [10 nhánh](integration/README.md) và [tiến độ](integration/PROGRESS.md).

## Tân — Tự động hoá

Kiểm tra board/chân kết nối, cảm biến, dây nối, nguồn/pin, driver, hiệu chuẩn và đo tốc độ/thời gian lấy mẫu. Cung cấp log và thông số đã đo cho IT.

Kế hoạch hiện giao nhánh 05 cho IT, Tân hỗ trợ phần cứng. Nếu giao hẳn nhánh này cho Tân, cần xác nhận và cập nhật phân công trước.

## Cùng phối hợp

Thống nhất đặc tả, quy trình thu dữ liệu, thí nghiệm, chọn mô hình, triển khai trên ESP32 và nghiệm thu/trình diễn. Không tự đổi quy ước dữ liệu hoặc biến trạng thái kỹ thuật thành kết luận y khoa.

Thống nhất trước khi cùng sửa main.cpp, board_config.h hoặc giao diện driver. Build/merge thành công không thay nghiệm thu phần cứng.

