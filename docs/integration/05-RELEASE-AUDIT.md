# Bàn giao tích hợp thiết bị và Dashboard — 15/11/2026

Nhánh: `feature/device-monitoring-workspace`, PR vào `dev`. Không đưa thay đổi lên `main`.

## Phạm vi và commit

1. Firmware: thu mẫu không nghẽn, hồi phục lỗi driver, bộ RR chính, worker chất lượng, đo IMU, bộ đếm mẫu 8 giây và test native.
2. Backend: telemetry 1.1/1.2, số mẫu chất lượng, phục hồi WebSocket, phiên tự động theo boot, báo cáo AI phân trang.
3. Frontend: kết nối thủ công, Dashboard hai trang, sidebar thu gọn, bốn biểu đồ 60 giây/15 giây mỗi khoảng, chất lượng và số mẫu thật, báo cáo AI.
4. Công cụ/CI/tài liệu: chạy local, nạp firmware riêng, cấu hình LAN và bằng chứng kiểm tra.
5. Dọn repo: bỏ file IDE/compile database sinh tự động khỏi Git, giữ bản local; bỏ các trang/component frontend không còn dùng, profile Demo/HR dự phòng đã bỏ, cấu hình broker trùng và placeholder hết nhiệm vụ.

## Kiểm tra tại máy Trung

- Backend: 141 test đạt; AI Python: 15 test đạt.
- Frontend: 95 test đạt, build đạt, audit production không có lỗ hổng đã biết. Bộ test hook đã chuyển sang hành động Kết nối thật thay kỳ vọng tự mở socket. Các ca reconnect, timeout, duplicate/stale, StrictMode, chọn thiết bị, phiên và teardown vẫn được kiểm tra.
- Firmware: bốn env `esp32s3_supermini`, `esp32s3_network_check`, `esp32s3_serial_check`, `esp32s3_hr_tracker` build đạt. Không bật networking bằng credential local trên CI.
- Test driver: 94 ca, gồm đổi nhịp 60→120 bpm và không nhận một đoạn đỉnh lẻ thành đổi nhịp bền. Bộ cửa sổ: 76 ca, 0/2400 cửa sổ chỉ có nhiễu tạo HR.
- Kiểm native chất lượng: 36 ca và 4 payload C++ qua schema runtime. HTTP/WebSocket và MQTT đều giữ số mẫu thật; dữ liệu cũ không được gắn số mẫu mới.
- Simulator HTTP và MQTT, firmware C++ qua broker Mosquitto thật/backend cô lập: đạt. Các bộ FIFO, capture, thuật toán offline và parity chất lượng được chạy theo CI.
- Hai mô phỏng cổ tay seed 701 và dense 801 hoàn tất 10 kịch bản mỗi lượt. Nhiễu tuần hoàn không có mạch vẫn là giới hạn nhận nhầm đã ghi nhận, không gọi là nghiệm thu độ chính xác.
- ESP thật trước bước dọn đã gửi PPG 401, GSR 160 và IMU 401 mẫu/cửa sổ 8 giây qua MQTT/backend/WebSocket. Không dùng kết quả này để xác nhận HR chính xác trên người hoặc cho mọi máy.

## Giới hạn và cách dùng

- HR vẫn chưa có đối chiếu đồng thời đủ để xác nhận sai số cổ tay. Sửa khóa RR trong lượt rà soát đã được kiểm bằng sóng tổng hợp; cần đối chiếu trên người khi kiểm độ chính xác.
- Khoảng thời gian dự đoán hiện để `—`; telemetry chưa có cửa sổ dự đoán AI. Cột khoảng thời gian trong bảng là đầu–cuối nhóm bản ghi, không khẳng định thời lượng bất thường sinh lý.
- `npm run dev` không nạp firmware. Dùng `npm run device:flash` sau khi cấu hình Wi-Fi/broker local; trên web chọn thiết bị và bấm Kết nối. Ngắt trên web không dừng phiên/ESP.
- Không commit secret, cấu hình mạng local, DB, raw, dataset tham chiếu hoặc log sinh ra. Tài liệu lịch sử và harness offline còn được CI sử dụng được giữ lại.
- Kiểm DOM/SVG không thay cho xem bố cục trực tiếp trên mọi màn hình. Build frontend còn cảnh báo bundle vượt 500kB; đây không phải lỗi build.

CI/PR được chốt theo SHA trên GitHub; kết quả local không thay thế CI. Log chi tiết local ở `backend/storage/local/release-audit/`, không đưa lên Git.
