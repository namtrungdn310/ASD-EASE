# Nhật ký hoàn thiện nhánh 5

## Tiếp tục ngày 2026-11-05

- Theo yêu cầu mới, bỏ thao tác DevTools/token: npm run dev ở root/frontend tự chuẩn bị/reuse local theo header, bật broker/backend và Vite. Bridge Node giữ token ở server, chỉ cấp cookie HttpOnly cho localhost; App tự mở/gia hạn phiên. Hướng dẫn cùng cách Trung/Tân tại05-ONE-COMMAND-DEV.md.
- Đã chạy2 entry và stop/start trên máy Trung; auto-session lấy cookie rồi nhận3 frame DEVICE thật, cả sau restart. Chưa có browser tool để xác nhận UI, chưa chạy máy Tân. Backend77 tests, frontend41, build/audit0 đạt; Vite cập nhật8.3.6 sửa advisory dev server.

- Trung gửi ảnh PPG VALID/có HR, GSR/IMU VALID; chủ đích smoke test, chưa giữ đo ổn định. Chuyển sang đăng nhập cookie trên Dashboard. Ảnh mới có loopGap106 ms (heapMin202632/stackWater3780 byte), cần giữ là điểm kiểm tra F17; không gộp với cửa sổ uptime khác hoặc kết luận zero-loss.

- Đã có Serial thật từ Trung: cửa sổ24.1 s,25 NET lines, wifi/mqtt/sync1, các counter lỗi/drop0, pending/outbox0. HeapMin201764/stackWater3780 byte, loopGap10 ms; processed rates xấp xỉ50.08/49.75/19.92 Hz. Chưa đủ F17 do thiếu baseline và ca mất mạng. GSR/IMU driver VALID, PPG NO_FINGER; chuyển sang kiểm tra MAX30102 khi đặt ngón tay. Raw log giữ local bị Git bỏ qua.

- Trung đã nạp env esp32s3_supermini qua COM7, SUCCESS21.78 giây/hash verified. Sau reset backend MQTT connected/sync1. Probe WS qua cookie nhận3 frame thật DEVICE/ESP32-001/session=null, timestamp tăng, khoảng1002 ms. Bằng chứng nhỏ được lưu trong thư mục credential local bị Git bỏ qua; chưa có ảnh Dashboard, đo3 driver hoặc Start/Stop thật.

- Trung đã điền Wi-Fi trong header local; đã kiểm tra không in secret và đối chiếu credential MQTT, broker/IP hiện tại. Build esp32s3_supermini networking-enabled đạt (RAM47180 byte, flash915953 byte). Dịch vụ vẫn healthy/sync0; chuyển sang hướng dẫn Trung upload COM7, chưa có kết quả nạp.

- Trung đã nối laptop vào hotspot iPhone/5G Viettel: laptop172.20.10.3, gateway172.20.10.1. Tạo bộ credential local esp32-trung, account ESP32-001 riêng và header network_config.h (chờ Trung điền2 trường Wi-Fi).
- Compose project asd-ease-esp32-trung: broker172.20.10.3:1883, backend127.0.0.1:8000 healthy; account backend/esp32 đăng nhập MQTT đạt, backend MQTT connected/sync0. Login HTTP/WS cookie qua dịch vụ thật đạt. Không gửi gói đo giả; ESP chưa được nạp cấu hình mới. Frontend đang có tại localhost5173 đúng dự án.

- Bước dây/nguồn: Trung xác nhận GPIO đúng cấu hình,3 cảm biến đều3V3 và chung GND. Chuyển sang chọn LAN; chưa mở broker hoặc lưu mật khẩu Wi-Fi. Chưa có bằng chứng đọc cảm biến thật.

- Bước đọc chip/flash đã đạt theo output Trung gửi: ESP32-S3 QFN56 rev0.2, flash4 MB XMC, embedded PSRAM2 MB/AP_3v3, crystal40 MHz, USB-Serial/JTAG; eFuse flash Quad/3.3 V. Chưa nạp firmware mới; tiếp tục đối chiếu dây/VCC/GND của3 cảm biến.

- Bước USB đã đạt: Trung gửi kết quả USB Serial Device COM7, VID:PID303A:1001. Chuyển sang đọc chip/flash bằng esptool; chưa nạp firmware.

- Base dev46d4e2d sau PR #17, nhánh `fix/esp32-local-mqtt-integration`.
- Trung đã có ESP32-S3 Super Mini và 3 cảm biến, đang cấp nguồn qua USB ở quán cà phê. Serial/PnP chưa thấy ESP; chờ kiểm tra cáp/cổng để nạp. Chưa chạy radio/cảm biến thật.
- Đã phân tích thay đổi Tân, sửa đường telemetry/sync/DB/WS và auth. Giữ chẩn đoán Wi-Fi và cấu hình cổng/bind local. Chi tiết tại [rà soát PR #17](05-REVIEW-PR17.md).
- Kết quả local cuối: backend72, protocol C++30, frontend26/build, firmware2 env/header4 và Compose config đạt. Native C++ → Mosquitto/API/DB/WS đạt7 nhóm với login/cookie HttpOnly như browser; gồm Start/Stop và restart backend/broker. Chưa có CI cho lượt sửa local này.
- Tiếp tục cùng Trung từng bước tại [05-LOCAL-BRINGUP.md](05-LOCAL-BRINGUP.md). Không nạp khi chưa xác nhận COM/board/flash; chưa ghi HW PASS.

## Nhật ký trước đó - 2026-11-03

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
