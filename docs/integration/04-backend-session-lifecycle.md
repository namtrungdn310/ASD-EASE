# 04 — Broker MQTT và quản lý phiên ở backend

| Mục | Nội dung |
|---|---|
| Nhánh | `feature/backend-session-lifecycle` |
| Phụ trách | Trung — IT |
| Phụ thuộc |03 đã thống nhất đặc tả |
| Ước lượng |3–4 ngày, gồm broker và kiểm thử tích hợp |
| Tiến độ |[Dòng04](PROGRESS.md) |

## Kết quả

Backend nhận telemetry MQTT, quản lý phiên theo thiết bị/nguồn và phân biệt yêu cầu với xác nhận thực thi. Có broker cục bộ và thiết bị giả lập để thử trước firmware. Browser vẫn HTTP/WS; raw HTTP ở06. Theo [kiến trúc](MQTT_ARCHITECTURE.md) và [đặc tả](../API_CONTRACT.md).

## Phạm vi file

- backend/app/schemas/session.py, api/v1/sessions.py, services/session_service.py, db/models.py.
- Mô-đun cấu hình/client/nhận MQTT dưới backend/app; khởi động/dừng trong main.py, không dựng lại firmware hỏi phiên qua HTTP.
- Compose, mẫu cấu hình/ACL, biến môi trường và dependencies; không credential thật.
- Dịch vụ nhận telemetry chung; chỉ đổi ràng buộc phiên, không thay thuật toán dự đoán.
- Simulator/thiết bị MQTT giả, tests, chuyển DB có phiên bản, hướng dẫn vận hành và tài liệu liên quan.

## Công việc

- [ ] Thử Python client với Mosquitto: gửi/nhận QoS1, kích thước gói, kết nối lại; chốt phiên bản.
- [ ] Broker có kiểm tra sức khoẻ, quyền theo thiết bị/nguồn, quy tắc lưu phiên và TLS/listener; không anonymous hoặc mở Internet.
- [ ] Cấu hình MQTT có kiểm tra; broker lỗi báo riêng, HTTP tra cứu/xuất vẫn dùng được. Đóng client/task sạch khi dừng.
- [ ] Callback chỉ kiểm tra kích thước/đưa vào hàng đợi có giới hạn; DB session đúng thread/task, quá tải có bộ đếm/lỗi rõ.
- [ ] HTTP/MQTT dùng chung kiểm tra/nghiệp vụ, ràng buộc topic/body/tài khoản; chống trùng để không nhân đôi DB/sự kiện/WS.
- [ ] Chỉ một tiến trình nhận MQTT trong cấu hình ban đầu; ghi rõ hạn chế nhiều worker/reload và thử khởi động lại.
- [ ] Đưa mẫu03 thành tests chạy được, ghi rõ SYNTHETIC.
- [ ] ID theo allowlist/độ dài, chặn dấu phân cách và thoát thư mục; kiểm tra device/origin ở mọi API.
- [ ] Lưu trạng thái, nguồn, generation, boot và thời gian; DB chặn hai phiên đang mở cùng thiết bị kể cả request đồng thời.
- [ ] Tách giờ yêu cầu/nhận ACK khỏi mốc thu; không lấy giờ nhận HTTP/MQTT làm timestamp mẫu.
- [ ] Start lặp đúng quy tắc, không tạo thêm phiên; xung đột có mã rõ.
- [ ] Lưu ý định và hàng lệnh chờ trước HTTP202, phát sau commit; PUBACK không đổi actual state.
- [ ] Đồng bộ MQTT command/ACK/state theo boot/kết nối/nonce/thời hạn; không giữ retained Start/Stop.
- [ ] Retry và phục hồi sau lỗi giữ cùng ID/generation; ACK/lệnh cũ không reset epoch hoặc tạo lại phiên.
- [ ] Chỉ STARTED ACK hợp lệ đưa STARTING sang RECORDING.
- [ ] Stop đưa STOPPING, có cutoff, final batch và thời hạn gửi nốt;06/07 bổ sung đối chiếu raw.
- [ ] Lưu tổng kết MQTT độc lập thứ tự raw HTTP; chưa có raw thì thử bằng mẫu, không claim đã nghiệm thu ghi đủ.
- [ ] Phân biệt dừng/thiếu/ABORTED; mất ACK không báo hoàn tất.
- [ ] Reboot không nối timestamp0 vào recording cũ hoặc nhận batch boot cũ sang phiên mới.
- [ ] Telemetry có/không session theo đặc tả, không tự gán phiên.
- [ ] Chuyển SQLite cũ có phiên bản, sao lưu, khôi phục và test; create_all() không tự thêm cột.
- [ ] Dữ liệu cũ thiếu nguồn/trạng thái giữ legacy/unknown khi chưa có căn cứ; không đoán DEVICE từ ID.
- [ ] Simulator cập nhật Start/Stop, ID phiên mới, MQTT ACK/đồng bộ; giữ HTTP tương thích, không gửi đôi một luồng.
- [ ] Tests dùng DB/vùng lưu riêng, không dữ liệu nhóm.
- [ ] Chia commit: broker/cấu hình → nhận chung/MQTT → phiên/lệnh chờ/chuyển DB → simulator/tests/hướng dẫn. Không tự thêm nhánh11.

## Kiểm thử

| Tình huống | Kết quả cần |
|---|---|
| HTTPStart→MQTT→ACK thật→Stop | Trạng thái đúng; PUBACK chưa là đang thu/đủ raw |
| Telemetry giả qua broker thật | Cùng nghiệp vụ HTTP, DB/WS không đôi |
| Broker mất/restart, backend còn | Lệnh chờ/quá hạn rõ, tra cứu vẫn chạy |
| Lỗi sau commit/trước phát, ACK lặp | Phục hồi đúng ID, không mất/nhân đôi phiên |
| Kết nối lại, lệnh/presence cũ | Không tự Start hoặc báo live sai |
| Sai tài khoản/quyền/topic/body | Không ghi/điều khiển thiết bị khác |
| Start đồng thời; ACK sai/cũ/lặp | Một phiên, không reset hoặc đổi nhầm |
| Stop trước Start ACK, không Stop ACK | Không treo vô hạn |
| Reboot thiết bị/backend, DB cũ | Phiên/clock không trộn, thông tin phục hồi đúng |
| Simulator HTTP/MQTT | Giữ nguồn, tương thích sau cập nhật |

## Bàn giao05 và khôi phục

- [ ] Có ví dụ topic/gói/lỗi, hướng dẫn LAN và thiết bị giả qua broker thật tới DB/WS.
- [ ] Kiểm thử chuyển DB tạm, lỗi broker/restart/trùng/quyền đều đạt.
- [ ] Firmware biết cấu hình broker, QoS/retain, payload và đồng bộ; raw API do06 bàn giao.
- [ ] Backend/AI tests và6 CI đạt, giữ nguyên tên checks. Kiểm thử broker không được bỏ qua rồi gọi PASS.
- [ ] Commit gợi ý: `feat(backend): quản lý phiên và xác nhận thiết bị qua MQTT`.

Sao lưu trước chuyển DB, không xoá DB để sửa lỗi. Khôi phục bằng cách đã thử hoặc bản sao lưu; giữ raw riêng. Không tự đổi quyền/tường lửa toàn máy.

## Nhật ký

| Ngày/commit | Việc | Bằng chứng | Kết quả |
|---|---|---|---|
|—|—|—|Chưa thực hiện|
