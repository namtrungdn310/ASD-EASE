# 05 — Firmware gửi telemetry và nhận lệnh MQTT

| Mục | Nội dung |
|---|---|
| Nhánh | `feature/firmware-telemetry-client` |
| Phụ trách | Trung — IT, Tân hỗ trợ board/driver |
| Phụ thuộc |03/04;02 trước nghiệm thu dashboard |
| Ước lượng |2–4 ngày, chưa tính chờ phần cứng |
| Tiến độ |[Dòng05](PROGRESS.md) |

## Kết quả

ESP32 gửi telemetry1.0 qua broker LAN, nhận Start/Stop và trả ACK/đồng bộ. Mất/chậm mạng không dừng lấy mẫu. Raw HTTP làm ở07; USB chỉ nạp/chẩn đoán, không thay đường truyền. Theo [kiến trúc](MQTT_ARCHITECTURE.md), broker/backend04 đã có để thử.

## Phạm vi

Mô-đun Wi-Fi, MQTT, topic, lệnh và đóng JSON trong include/communication/ và src/communication/. Thay tối thiểu main.cpp; phối hợp Tân trước sửa chung. network_config.example.h dùng mẫu, network_config.h local bị bỏ qua. Thêm tests C++/Pydantic, hướng dẫn LAN và giai đoạn07; không đổi thuật toán cảm biến chỉ để payload đẹp.

## Đóng gói dữ liệu

- [ ] Dùng bộ đóng JSON riêng, không gửi nguyên Pretty JSON chẩn đoán.
- [ ] Theo mapping03: null khi lỗi/cũ, đúng phiên/thiết bị/phiên bản và DEVICE khi cảm biến thật.
- [ ] GSR delta đúng tỷ lệ; movement chưa thuật toán dùng null, không tính dự đoán giả trên laptop.
- [ ] Chưa mô hình: probabilitynull, modelnone và trạng thái/chất lượng đúng quy ước; VALID không tự NORMAL.
- [ ] Có trạng thái và tuổi mẫu; không gửi cache như số đo mới.
- [ ] Chụp dữ liệu nhất quán giữa task; copy giá trị, không giữ con trỏ vùng đang thay.
- [ ] Kiểm tra JSON do C++ tạo bằng Pydantic, không chỉ nhìn Serial.

## Mạng và phiên

- [ ] Chọn/pin thư viện Arduino sau thử gửiQoS1, subscribe/LWT/TLS, giới hạn packet/hàng chờ; không chỉ dựa khả năng nhậnQoS1.
- [ ] CI build không cần credential thật; thiếu file local không làm compile lỗi, mặc định networking tắt/cấu hình mẫu có kiểm soát.
- [ ] Broker host/port/clientID/credential/TLS riêng với HTTP backend cho07; dùng IP/DNS LAN, không localhost hoặc service Docker.
- [ ] Thử broker/health trong LAN,1883 dev hoặc8883 TLS theo quy tắc; không public broker hoặc tắt tường lửa.
- [ ] Wi-Fi nối lại có thời gian chờ tăng và log giới hạn, không vòng chờ làm dừng cảm biến.
- [ ] MQTT có timeout, task/hàng đợi hữu hạn; callback không chờ DB/HTTP. Tính RAM/stack, không mặc định publish không chặn.
- [ ] Không chờ broker/PUBACK trong loop10 ms; đo ảnh hưởng MQTT/Serial, để tài nguyên HTTPraw07.
- [ ] Topic/nguồn/quyền đúng; lệnh/telemetry không retained, LWT không biến dữ liệu cũ thành live.
- [ ] Subscribe xong mới đồng bộ boot/nonce; chỉ chạy lệnh đúng phiên/generation/thời hạn, ACK sau thực thi. Mốc thu chỉ đặt một lần.
- [ ] Timestamp theo epoch, xử lý rollover millis()/reboot theo đặc tả.
- [ ] Nhịp gửi thử1000 ms độc lập sensing; chỉ bản mới nhất, không gửi dồn dữ liệu cũ; raw không đi topictelemetry.
- [ ] Stop theo máy trạng thái; chưa có07 thì không tuyên bố gửi nốt raw xong.
- [ ] Phân biệt Wi-Fi/broker lỗi, backend chưa nhận và ứng dụng từ chối; PUBACK không là xác nhận nghiệp vụ. Retry đúng ID/thời hạn, không thử gói sai vô hạn.
- [ ] Log thiết bị/boot/lệnh/phiên bản/số đếm/thời gian, không secret. Broker còn nhưng backend mất không nghĩa đã bắt đầu thu.
- [ ] Ghi commit, cấu hình, board và kết quả thật trong giai đoạn07; nêu phần raw/chức năng còn thiếu.

## Kiểm thử

| Tình huống | Cần thấy |
|---|---|
| JSON hợp lệ/sai/null | Pydantic kiểm tra đúng, không trường debug |
| Build không có file local | CI đạt, không secret trong nguồn/image |
| ESP32+broker+backend LAN | Backend nhận/kiểm tra, DB/WS/dashboard đúng DEVICE |
| Wi-Fi/broker sai/mất/restart | Lấy mẫu tiếp, nối lại/hàng đợi hữu hạn, đồng bộ trước lệnh |
| Broker còn/backend mất | Không coi PUBACK là ACK đang thu |
| Sai quyền/payload/quá gói | Lý do rõ, không retry mù hoặc thành công giả |
| Lệnh/ACK lặp, Stop, reboot, lệnh cũ | Không reset epoch, nhầm phiên hoặc tự Start |
| Cảm biến mất khi mạng tốt | Null/trạng thái đúng, không số cũ hợp lệ |

## Nghiệm thu và khôi phục

- [ ] Build Windows/Linux, JSON fixtures và CI đạt.
- [ ] Có log so rate/gap trước/sau mạng, không chỉ comment “non-blocking”.
- [ ] Chưa board: có thể bàn giao phần mềm với WAITING_HARDWARE, không đóng giai đoạn07.
- [ ] Có board: giữ log MQTT/application ACK, DB/WS, ảnh dashboard, commit/cấu hình; không lấy PUBACK làm bằng chứng raw.
- [ ] Commit gợi ý: `feat(firmware): gửi telemetry MQTT và xác nhận lệnh phiên`.

Giữ chế độ Serial-only để chẩn đoán, không xoá driver của Tân. Nếu ảnh hưởng lấy mẫu, tắt transport bằng cấu hình và giữ log để sửa lịch chạy.

## Nhật ký

| Ngày/commit | Việc | Bằng chứng | Kết quả |
|---|---|---|---|
|—|—|—|Chưa thực hiện|
