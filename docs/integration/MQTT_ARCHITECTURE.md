# Kiến trúc kết nối — MQTT và HTTP

Cập nhật2026-10-31. Áp dụng nhánh03–10. Đây là tổng quan; quy tắc chi tiết ở [API](../API_CONTRACT.md), [nhận dữ liệu](../contracts/INGESTION_V1.md) và [MQTT](../contracts/MQTT_CONTROL.md) được ưu tiên khi tra cứu.

## Đã thống nhất

- MQTT cho telemetry và Start/Stop/ACK/đồng bộ trạng thái.
- Raw batch giữ HTTP, không chuyển cả dữ liệu sang broker.
- Browser giữ HTTP/WebSocket; không MQTT hoặc credential broker.
- Đặc tả03 đã hoàn thiện local, chờ review; chưa broker/client thực tế. Phiên bản thư viện/broker và số đo chốt ở04/05/07.

## Luồng

```text
ESP32 -- MQTT telemetry/ACK/state --> broker --> backend
ESP32 <-- MQTT command/state ------ broker <-- backend
ESP32 -- HTTP raw-batch ---------------------> file + chỉ mục DB
Browser -- HTTP Start/Stop/query/export -----> backend
Browser <-- WebSocket telemetry ------------- backend
```

Broker chuyển gói; backend vẫn kiểm tra quyền/dữ liệu, quản lý phiên và lưu/phát WS. Có thể chạy cùng laptop trên LAN, không cần cloud/Internet.

| Đường | Nhánh |
|---|---|
| Broker và backend MQTT, cùng nghiệp vụ HTTP |04 |
| Firmware telemetry/lệnh/ACK |05 |
| HTTP raw và xác nhận lưu bền |06–07 |
| Đọc/xuất dù broker offline |08–09 |
| Kiểm thử toàn luồng |10 |

## Quy tắc quan trọng

1. Đổi transport không tự đổi /api/v1 hoặc JSONtelemetry/raw1.0. Control có phiên bản riêng.
2. Chọn MQTT3.1.1/Mosquitto local, pin phiên bản ở04. Client Arduino05 phải chứng minh gửiQoS1, TLS, bộ đệm và build; không chỉ thấy hỗ trợ nhậnQoS1 là đủ.
3. Namespace asd-ease/v1/{origin}/{device_id}/. Device chỉ gửi/nhận topic của mình, đối chiếu tài khoản/topic/body; prefix không chứng minh nguồn.
4. TelemetryQoS0, retain=false, chỉ bản mới nhất; nhịp phát triển1000 ms độc lập rate cảm biến. ControlQoS1 không retained; presenceQoS1 retained chỉ gợi ý kết nối.
5. Lưu ý định/lệnh vào DB trước phát. PUBACK chưa chứng minh thực thi; chỉ ACK ứng dụng đúng lệnh/boot/kết nối và lưu bền mới đổi trạng thái.
6. Đồng bộ lại với nonce mới sau reconnect; generation không lùi, thời hạn dựa clock tăng đơn điệu, không chạy lại Start cũ. Reboot không nối clock reset vào phiên cũ.
7. Một tiến trình nhận MQTT; callback chỉ đưa vào hàng đợi có hạn, không chặn DB/file hoặc sensing. Không dùng DB session xuyên thread tuỳ ý.
8. Raw chỉ release khi HTTP202 xác nhận đúng batch đã lưu nhất quán. Tổng kết Stop có thể trước/sau raw cuối; thiết bị dừng chưa có nghĩa đủ dữ liệu.
9. Broker hỏng/HTTP còn và HTTP hỏng/MQTT còn là hai trường hợp riêng; ghi loss/gap đúng, không coi chart live là raw tốt.
10. Không anonymous; ACL theo thiết bị, secret local. TLS ngoài ngoại lệ LAN phát triển riêng; không tắt tường lửa/mở broker công khai.
11. Giữ HTTP simulator có cập nhật quyền/phiên, nhãn SYNTHETIC; không gửi đôi cùng luồng hoặc nới quyền DEVICE để giữ tương thích.
12. Khác nhau giữa backend/WS kết nối, broker kết nối, presence, tuổi telemetry, phiên thu và mức đủ dữ liệu phải được thể hiện rõ.

Xem [OASIS MQTT3.1.1](https://docs.oasis-open.org/mqtt/mqtt/v3.1.1/os/mqtt-v3.1.1-os.html) cho giao thức; [ESP-MQTT](https://docs.espressif.com/projects/esp-mqtt/en/latest/esp32/) cho tham khảo client. Vẫn cần thử với framework/thư viện thực tế, không suy non-blocking từ tên hàm.

## Phân việc và bước tiếp

Giữ nguyên10 nhánh/tên. Nhánh04 tăng phạm vi nên chia commit: broker/cấu hình → nhận chung/MQTT → phiên/lệnh chờ → simulator/tests/hướng dẫn. Nếu cần tách thêm PR phải báo Trung trước.

Sau [bàn giao03](03-HANDOFF.md), review/merge rồi mới04. Kết quả mẫu không thay nghiệm thu thật; rate/đồng bộ/RAM ở05/07 còn chờ Tân/IT. Các phần code sau vẫn có thể học từng file theo yêu cầu Trung.
