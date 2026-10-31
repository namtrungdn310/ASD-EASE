# Quyết định thiết kế

Các mục cũ chưa rõ ngày giữ “-”, không điền ngày giả. Đã thống nhất thiết kế không có nghĩa đã triển khai hoặc nghiệm thu.

## ADR-001 — Ba thư mục mã nguồn

Trạng thái: ACCEPTED.

Dùng backend, frontend, ai; docs chỉ chứa tài liệu. Giữ ít cấu trúc để nhóm hai người dễ bảo trì, không tạo mã nguồn riêng cho mỗi giai đoạn.

Ngày: -.

## ADR-002 — Vị trí firmware

Trạng thái: ACCEPTED.

Firmware nằm tại ai/edge_firmware; thao tác PlatformIO từ thư mục này, không tạo mô-đun mã nguồn thứ tư.

Ngày: -.

## ADR-003 — Vi điều khiển chính

Trạng thái: ACCEPTED.

Chọn họ ESP32-S3 Super Mini. Biến thể board, chân và bộ nhớ vẫn phải kiểm chứng trên hàng thật.

Ngày: -.

## ADR-004 — Suy luận cuối trên thiết bị

Trạng thái: ACCEPTED.

ESP32-S3 tự trích đặc trưng, chạy AI, chuyển trạng thái và quyết định cảnh báo. Suy luận trên laptop chỉ dùng khi phát triển.

Ngày: -.

## ADR-005 — Vai trò laptop

Trạng thái: ACCEPTED.

Laptop nhận/lưu tuỳ chọn và hiển thị khi thi đấu, không tính lại để thay trạng thái thiết bị.

Ngày: -.

## ADR-006 — Wi-Fi cục bộ

Trạng thái: ACCEPTED.

Thiết bị và laptop cùng LAN để không cần USB truyền dữ liệu. Backend lắng nghe địa chỉ phù hợp; ESP32 dùng IP LAN laptop.

Ngày: -.

## ADR-007 — Không phụ thuộc Internet

Trạng thái: ACCEPTED.

Luồng thi đấu chạy không cần dịch vụ đám mây; giúp trình diễn lặp lại khi mạng Internet không ổn định.

Ngày: -.

## ADR-008 — Pin và USB khi thi đấu

Trạng thái: ACCEPTED.

ESP32 dùng pin và ngắt USB. Nguồn/sạc/an toàn phải kiểm chứng phần cứng, không suy từ tên board.

Ngày: -.

## ADR-009 — FastAPI và React

Trạng thái: ACCEPTED.

Dùng FastAPI nhận dữ liệu, React hiển thị, HTTP/WebSocket làm giao diện trình duyệt. Hai người dễ đọc và bảo trì.

Ngày: -.

## ADR-010 — Tách thông tin và mẫu thô

Trạng thái: ACCEPTED.

SQLite giữ thông tin/chỉ mục; file giữ batch mẫu tốc độ cao. Sao lưu phải gồm cả DB và file.

Ngày: -.

## ADR-011 — Chất lượng kém có thể UNCERTAIN

Trạng thái: ACCEPTED.

Không ép mô hình kết luận từ tín hiệu kém. Cho phép giá trị cảm biến/điểm dự đoán null và trạng thái chưa đủ tin cậy.

Ngày: -.

## ADR-012 — So với phương pháp đơn giản

Trạng thái: ACCEPTED.

So mô hình với quy tắc HR, HR+GSR, HR+GSR+IMU. Không mặc định mô hình phức tạp sẽ tốt hơn.

Ngày: -.

## ADR-013 — Thông số phần cứng cần bằng chứng

Trạng thái: ACCEPTED.

Chưa chốt GPIO/flash/PSRAM theo suy đoán. Profile build không thay nhận dạng và phép đo board thật.

Ngày: -.

## ADR-014 — Mạng không chặn xử lý trên thiết bị

Trạng thái: ACCEPTED.

Thu mẫu/suy luận tiếp tục khi Wi-Fi lỗi. Giới hạn hàng đợi và thời gian thử lại; kiểm tra hệ thống thi đấu ở giai đoạn21.

Ngày: -.

## ADR-015 — Nguồn giả lập và giao diện dùng chung

Trạng thái: ACCEPTED.

Giả lập dùng cùng đặc tả raw và đầu vào xử lý, giữ nguồn SYNTHETIC và nơi lưu riêng. Kết quả chỉ từ giả lập không xác nhận hiệu quả thật hoặc tự cho phép triển khai mô hình.

Ngày: -.

## ADR-016 — MQTT cho telemetry/điều khiển, HTTP cho raw

Trạng thái: ACCEPTED — thống nhất thiết kế; triển khai còn ở nhánh04–08.

MQTT3.1.1/Mosquitto cục bộ cho telemetry, lệnh, ACK và đồng bộ; raw HTTP, browser HTTP/WS. TelemetryQoS0 chỉ bản mới, controlQoS1 không retained; presence retained chỉ là gợi ý kết nối. Dùng phiên MQTT sạch, DB giữ lệnh bền. Nhánh04 có backend trước05 client; tốc độ cảm biến độc lập nhịp gửi. PUBACK không là ACK thực thi/lưu. Client Arduino phải được thử khả năng gửiQoS1, TLS, bộ nhớ; phiên bản cụ thể chốt ở04/05.

Ngày: 2026-10-31 (ghi thành văn bản; hướng giao thức thống nhất 2026-10-22).

## ADR-017 — Phiên bản control và mốc thu khi nối lại

Trạng thái: ACCEPTED — thống nhất thiết kế; triển khai còn ở nhánh04–08.

Giữ telemetry/raw1.0 và /api/v1; control1.0 độc lập. Lưu ý định/lệnh trước HTTP202; chỉ ACK ứng dụng mới xác nhận RECORDING. Lệnh ràng buộc boot, kết nối, request nonce, generation bền và thời hạn theo đồng hồ tăng đơn điệu, không cần giả UTC đồng bộ. Reboot gián đoạn phiên; reconnect không reset epoch. Xem [control](contracts/MQTT_CONTROL.md). Nếu raw không đáp ứng lưới thời gian, đổi phiên bản thay vì bịa alignment. Đo board là cổng05/07.

Ngày: 2026-10-31.

## ADR-018 — Xác nhận lưu raw và giới hạn mất dữ liệu

Trạng thái: ACCEPTED — thống nhất thiết kế; triển khai còn ở nhánh04–08.

File batch bất biến +SQLite index, khoá phiên/thiết bị/batch và SHA256/JCS. PENDING → file tạm → công bố nguyên tử/lưu bền → COMPLETE →202. Trùng đúng202, xung đột409; đối chiếu sau lỗi, giữ JSONL cũ. Tổng kết MQTT có thể trước/sau raw HTTP, STOPPED khác đủ dữ liệu. Bộ đệm giới hạn số/byte, đầy thì bỏ batch mới đóng và ghi mất. Xem [nhận dữ liệu](contracts/INGESTION_V1.md). Chưa tuyên bố toàn hệ thống đúng một lần; cần kiểm thử JCS/lỗi/concurrency. Không tự ghi flash hoặc chuyển đổi xoá dữ liệu.

Ngày: 2026-10-31.

## ADR-019 — Danh tính, nguồn và phạm vi bàn giao03

Trạng thái: ACCEPTED — thống nhất thiết kế; triển khai còn ở nhánh04–08.

Tài khoản gắn device/origin; MQTT ACL theo thiết bị, HTTP bearer theo danh tính. Body/tiền tố không tự chứng minh DEVICE. Không ẩn danh; TLS ngoài ngoại lệ LAN phát triển đã ghi rủi ro; không secret trong Git/VITE/log. Chưa ước lượng chất lượng thì0 bảo thủ; chưa mô hình thì probabilitynull và CALIBRATING/UNCERTAIN. Simulator cũ phải được cập nhật xác thực/vòng đời, không bỏ quyền DEVICE để test xanh. Nhánh03 chỉ hoàn thiện tài liệu/mẫu/công cụ kiểm tra, chưa runtime, phần cứng, thu người thật hoặc merge nhánh bảo vệ.

Ngày: 2026-10-31.

