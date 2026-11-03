# Nhật ký hoàn thiện nhánh 5

Ngày 2026-11-03. Nhánh `feature/firmware-telemetry-client-completion` từ dev `1e73aea` (PR #14 của Tân), sau backend04 `7ff5a2c`.

## Phạm vi và bằng chứng

Trung yêu cầu hoàn thiện phần code còn thiếu. Board/cảm biến hiện ở chỗ Tân; discovery serial trên máy này không có thiết bị. Chỉ xác nhận build/tests/tích hợp phần mềm; phần cứng ghi WAITING_HARDWARE.

Giữ thay đổi GPIO MPU SDA5/SCL11 của Tân, PPG8/9 và GSR7; không tự đổi lại dây hoặc thuật toán lọc. Giữ hai thay đổi định dạng schema local và prompt chưa commit của Trung.

## Rà soát PR #14

- Đã có serializer và điểm tích hợp vào main, nhưng publish ba topic `asd/v1/devices/.../sensors/*` khác contract `asd-ease/v1/DEVICE/.../telemetry`.
- Transport đợi Wi-Fi tới8 s trong loop sensing; queue16 snapshot và flush backlog; chưa subscribe/state/Start/Stop/ACK.
- PubSubClient không đáp ứng publish QoS1 cho control. Chuyển sang ESP-MQTT có sẵn trong Arduino/ESP-IDF đang dùng, pin platform; build cả nhánh network-disabled và network-enabled.
- Serializer chưa có tuổi mẫu, quality gán0.9/1 và mapping CALIBRATING/GSR chưa khớp quy ước.
- mqtt_subscriber.py mới là đường gom topic khác contract, chưa được main khởi động; nếu nối vào sẽ bỏ qua registry/boot/phiên và còn broadcast khi DB lỗi. Loại bỏ đường thử chưa dùng này, dùng receiver04 có xác thực/nghiệp vụ chung; giữ tests hồi quy và thay tests cho đường bị bỏ bằng kiểm tra chặn topic cũ.

## Các mốc

- [x] Đọc diff Tân, code/contract, kiểm tra môi trường và tách nhánh; hỏi vị trí board.
- [x] Core C++ portable: control/lease/epoch/chống trùng, serializer/freshness, native harness xuất JSON thật.
- [x] ESP-MQTT QoS1/task mạng riêng, queue hữu hạn/latest-only, SUBACK/LWT/TLS/reconnect, tích hợp sensing.
- [x] Cấu hình DEVICE/ACL/profile và LAN; bỏ đường subscriber khác contract.
- [x] Native tests/fixtures qua Pydantic; harness C++ qua broker thật → backend/DB/WS, các lỗi và hồi quy.
- [x] Build firmware hai chế độ, backend/AI/frontend, hướng dẫn05/ma trận nghiệm thu cho Tân.
- [ ] Tân nạp/đo cảm biến thật, LAN/Dashboard, StartStop/lỗi/tài nguyên trên ESP32; board chưa ở máy Trung.
- [x] Trung yêu cầu đưa code vào dev: commit d1101c5, push và mở [PR #15](https://github.com/namtrungdn310/ASD-EASE/pull/15). CI/review/merge theo kết quả trên head cuối của PR; local không thay CI.

## Kết quả chạy local

- PlatformIO2 env đạt, header4/4; native C++30 tests qua Pydantic runtime.
- Hai bài MQTT (core C++ và simulator Python) đều đạt7 nhóm qua Mosquitto thật; account DEVICE riêng bị chặn khi publish vào topic SYNTHETIC khác.
- Backend61, AI15, frontend26/build/audit0; HTTP transport19 frame đạt. Compose config --quiet đạt.
- Đã bổ sung timeout SUBACK, dừng retry khi CONNACK/quyền/chứng chỉ sai, thống kê outbox/lỗi; log ID/boot/connection/phiên và Serial dùng cùng ID MQTT. Build lại cả hai env đạt.
- Pin platform7.1.3/ArduinoJson7.4.3/C++17; SDK ESP-MQTT có sẵn đã link đủ nhánh TLS. Chưa thử handshake TLS/đồng hồ trên board.
- Chỉ kích thước static: mạng tắt RAM20636/flash322293 byte, build-check mạng RAM47180/flash913889 byte. Không xem đây là số đo RAM runtime.

Tài liệu vận hành ở [05-SETUP](05-SETUP.md), giải thích file ở [05-HANDOFF](05-HANDOFF.md), ma trận phần mềm/phần cứng ở [05-VERIFICATION](05-VERIFICATION.md). Phần code READY_FOR_REVIEW, nghiệm thu WAITING_HARDWARE; không đóng phase07.

## Điểm kỹ thuật phải giữ khi tiếp tục

- Telemetry nguồn DEVICE thật trên board; fixture native/SYNTHETIC phân biệt rõ, không giả phần cứng.
- Control1.0/telemetry1.0; topic/QoS/retain theo MQTT_CONTROL.md; backend kiểm tra ACK nonce hiện hành.
- Không có raw ở05: STOPPED summary zero/cutoff0/raw_recording_enabled=false, complete=false.
- Mạng không chạy chờ trong sensing. Callback chỉ xếp gói có giới hạn; worker duy nhất xử lý state; snapshot copy nhất quán.
- Boot mới sau reboot, connection mới trước CONNECT/LWT, request mới mỗi sync. Epoch không reset khi reconnect/lặp lệnh.
- Chưa có board: không nạp, không ghi tốc độ/RAM chạy thật hoặc ảnh Dashboard thật đã PASS.

Nguồn kiểm tra API: [ESP-MQTT IDF4.4.7](https://docs.espressif.com/projects/esp-idf/en/v4.4.7/esp32s3/api-reference/protocols/mqtt.html), header mqtt_client.h và libmqtt.a thực có trong framework cài trên máy.
