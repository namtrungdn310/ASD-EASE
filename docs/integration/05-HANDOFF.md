# Bàn giao code nhánh 5

Cập nhật 2026-11-03. Nhánh `feature/firmware-telemetry-client-completion` từ dev `1e73aea` sau PR #14 của Tân.

**Phần mềm đã triển khai; nghiệm thu ESP32 đang WAITING_HARDWARE.** Board/cảm biến vẫn ở chỗ Tân. Chưa nạp, chưa đo ảnh hưởng mạng và chưa xác nhận Dashboard bằng dữ liệu board thật. Code được đưa vào dev qua [PR #15](https://github.com/namtrungdn310/ASD-EASE/pull/15) theo yêu cầu Trung; trạng thái CI/merge xác nhận tại PR.

## Đã hoàn thiện

- Wi-Fi và ESP-MQTT chạy ở task riêng, không chờ mạng trong vòng đọc cảm biến. Snapshot queue1 luôn thay bằng bản mới nhất, không xả telemetry cũ sau reconnect.
- Topic `asd-ease/v1/DEVICE/{device_id}/...`, telemetry QoS0, control/ACK/sync/presence QoS1; clean session, SUBACK trước sync, LWT có connection nonce mới trước CONNECT.
- Start/Stop, ACK thực thi, xác nhận backend, lease tính từ lượt sync, chống lặp/nonce/generation cũ, giữ epoch khi reconnect. Reboot không tự tiếp tục phiên cũ.
- Serializer đúng schema1.0; dữ liệu lỗi/cũ thành null, GSR delta=percentChange/100, không bịa quality/movement/prediction. Tuổi HR lấy từ nhịp hợp lệ và tuổi PPG, không chỉ lúc gọi read().
- Cấu hình DEVICE/ACL riêng, broker bind IP LAN có chủ đích. Giữ loopback mặc định và file secret local.
- Loại subscriber thử chưa dùng theo topic cũ; tiếp tục dùng receiver04 có registry/xác thực/phiên và DB→WS hiện có.
- Tests native C++ dùng chính core production, kiểm tra JSON bằng Pydantic runtime và đi qua Mosquitto/backend/DB/WS thật. Python chỉ thay lớp vận chuyển trong bài thử native, dữ liệu luôn SYNTHETIC.

## Các file chính làm gì?

| File/nhóm | Vai trò |
|---|---|
| include/communication/session_protocol.h và src/communication/session_protocol.cpp | Luật phiên/lệnh/ACK/đồng hồ và tạo JSON đúng đặc tả, chạy được cả ESP32 và tests native. |
| communication/mqtt_transport.* | Wi-Fi, ESP-MQTT, SUBACK/PUBACK, LWT, reconnect, task/queue có giới hạn và thống kê lỗi/tài nguyên. |
| communication/telemetry_serializer.* | Chụp số đo và tuổi mẫu từ driver, không gửi Pretty JSON Serial. |
| communication/network_settings.h, network_config.example.h | Mặc định mạng tắt; đọc cấu hình local, phân biệt LAN plaintext/TLS và env chỉ build. |
| MAX30102Sensor/MPU6050Sensor/GSRSensor | Thêm thời điểm mẫu/nhịp hợp lệ; giữ thuật toán lọc, đơn vị và GPIO của Tân. |
| src/main.cpp | Copy snapshot sang task mạng, thống kê số mẫu/loop; giữ đọc cảm biến và Serial. |
| platformio.ini | Pin platform7.1.3/ArduinoJson7.4.3/C++17, build thêm env kiểm tra mạng/TLS. |
| scripts/setup_local_mqtt.py | Tạo bộ credential mới có DEVICE riêng bằng --device-id, không ghi đè cấu hình cũ. |
| compose.yaml | MQTT_BIND_IP và MQTT_LOCAL_DIR để chọn LAN/bộ cấu hình thử, mặc định vẫn loopback. |
| tests/native/protocol_harness.cpp, scripts/firmware_native*.py | Chạy core C++ bằng clock/transport thử; không phải cảm biến hoặc radio thật. |
| scripts/check_firmware_protocol.py | Kiểm tra serializer/phiên/lệnh/freshness/giới hạn bằng core C++ và schema backend. |
| scripts/check_mqtt_integration.py | Kiểm tra broker/API/DB/WS; --native-firmware dùng core C++ thay simulator Python. |
| backend/tests/test_firmware_topics.py | Chặn topic cũ/sai nguồn qua receiver đang dùng. |
| .github/workflows/ci.yml | Thêm native/protocol/broker trong Firmware build, giữ6 tên check bảo vệ nhánh. |

## Lựa chọn SDK và giới hạn

Dùng ESP-MQTT có sẵn trong Arduino2.0.17/ESP-IDF4.4 của platform đã pin, publish được QoS1; bỏ PubSubClient vốn không publish QoS1. [API chính thức ESP-MQTT](https://docs.espressif.com/projects/esp-idf/en/v4.4.7/esp32s3/api-reference/protocols/mqtt.html). Header/API và libmqtt.a đã được compile/link cả nhánh mạng/TLS; TLS handshake trên board chưa thử.

Worker mạng stack12 KiB, SDK MQTT stack6 KiB; inbox8 gói tối đa4 KiB, core+outbox gửi giới hạn8 gói/32 KiB, snapshot1. Giới hạn này chưa chứng minh còn đủ heap/stack cho board và HTTPraw07; phải đo runtime. Chờ SUBACK/PUBACK có timeout, lỗi CONNACK cấu hình/quyền hoặc xác minh chứng chỉ dừng retry; lỗi mạng tạm dùng backoff.

Giữ MPU6050 SDA5/SCL11 của PR #14, MAX30102 SDA8/SCL9, GSR7. Profile50/50/20 là danh định, không ghi như số đo. Không đổi driver để làm payload trông đẹp.

## Cách dùng và bước tiếp

1. Tân làm theo [05-SETUP](05-SETUP.md), xác nhận board/dây rồi nạp env esp32s3_supermini với file credential local.
2. Điền [05-VERIFICATION](05-VERIFICATION.md), đặc biệt LAN/StartStop/reconnect/độ trễ/số mẫu/tài nguyên/Dashboard thật.
3. Code đã commit/push, [PR #15 vào dev](https://github.com/namtrungdn310/ASD-EASE/pull/15); theo [Git workflow](../GIT_WORKFLOW.md), chỉ merge sau đủ6 CI và không xung đột. Tân pull dev sau khi PR merge; chỉ ghi nhánh05 DONE sau đủ bằng chứng board.
4. Nhánh06 làm backend raw bền/chống trùng/đối chiếu;07 mới bật raw HTTP/batch và thay zero-batch summary bằng tổng kết thu thật.

Nhánh05 Stop có cutoff0/raw_recording_enabled=false, do đó complete=false là đúng. Không lấy telemetry1Hz thay raw hoặc kết quả native thay nghiệm thu ESP32.
