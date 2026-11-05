# Chạy nhánh 05 trên máy Trung - theo từng bước

Cập nhật 2026-11-05. Nhánh `fix/esp32-local-mqtt-integration`, từ dev `46d4e2d`.

Mục tiêu: ESP thật → Wi-Fi LAN → MQTT trên laptop → backend → WebSocket → Dashboard localhost.

## Trạng thái hiện tại

- [x] Đọc và rà soát thay đổi PR #17; xem [phân tích](05-REVIEW-PR17.md).
- [x] Sửa code nhận/gửi dữ liệu, quyền browser và thống nhất ID thiết bị.
- [x] Trung xác nhận board ESP32-S3 Super Mini, MAX30102, MPU6050, Grove GSR đang ở máy mình.
- [x] Máy đã nhận ESP qua USB Serial Device COM7, VID:PID303A:1001 (kết quả Trung gửi 2026-11-05).
- [x] Esptool xác nhận ESP32-S3 QFN56 rev0.2, flash4 MB, PSRAM nhúng2 MB.
- [x] Trung xác nhận dây đúng bảng GPIO, cả3 cảm biến dùng3V3 và chung GND.
- [x] Laptop kết nối hotspot iPhone dùng5G Viettel; IP172.20.10.3, gateway172.20.10.1.
- [x] Đã tạo DEVICE/ACL và chạy broker/backend riêng; kiểm tra MQTT login, backend health và WS cookie đạt.
- [x] Trung đã điền/lưu Wi-Fi; kiểm tra trường cấu hình, ID/broker/credential MQTT khớp và file được Git bỏ qua.
- [x] Build env esp32s3_supermini với cấu hình mạng thật đạt; chưa nạp.
- [x] Trung nạp firmware COM7 thành công, hash verified, SUCCESS21.78 giây theo log đã gửi.
- [x] Backend báo1 thiết bị sync; đã đọc3 frame DEVICE/ESP32-001 thật qua WebSocket, session=null, chu kỳ khoảng1002 ms.
- [x] Đã đọc Serial: wifi/mqtt/sync=1, không lỗi/drop; driver GSR/IMU báo VALID, PPG báo NO_FINGER.
- [x] Trung gửi ảnh MAX30102 báo VALID/có HR; chỉ smoke test, chưa đo độ ổn định/độ chính xác.
- [x] Đã thay thao tác DevTools bằng npm run dev tự bật dịch vụ và mở phiên local theo yêu cầu mới của Trung.
- [ ] **Đang làm: Trung chạy npm run dev và xác nhận ESP32-001 hiển thị live trên Dashboard.**
- [ ] Xác nhận DEVICE đi qua backend/DB/WS đến Dashboard.
- [ ] Start/Stop, reconnect/reboot, lỗi cảm biến và đo tài nguyên/nhịp mẫu.
- [ ] Cập nhật F01–F19, PR/CI và chốt nghiệm thu theo bằng chứng.

Không đánh dấu DONE chỉ vì build thành công hoặc broker nhận JSON. Các bước sau sẽ được bổ sung/hướng dẫn khi bước hiện tại đạt.

## Bước 1 đã đạt: nhận cổng USB để nạp

USB có hai vai trò độc lập: cấp nguồn và truyền dữ liệu để nạp/xem log. Số đo tới Dashboard vẫn dùng Wi-Fi. Đèn nguồn sáng chưa chứng minh cáp có đường dữ liệu.

Lần đầu chỉ thấy COM3–COM6 là **Standard Serial over Bluetooth link**. Kết quả Trung gửi sau đó đã có **USB Serial Device COM7**, USB VID:PID303A:1001. Dùng COM7, không dùng các cổng Bluetooth để nạp ESP.

1. Dùng cáp USB có truyền dữ liệu, cắm trực tiếp từ ESP vào laptop. Nếu cáp hiện tại chỉ sạc, thay cáp trước.
2. Trong PowerShell tại `D:\Projects\asd-ease`, chạy:

```powershell
.\.venv\Scripts\python.exe -m serial.tools.list_ports -v
```

3. Gửi lại kết quả. Cần thấy một cổng kiểu `COM3`, `COM5` kèm tên/USB VID:PID. Nếu vẫn `no ports found`, ghi đúng kết quả đó để tiếp tục kiểm tra bootloader/cổng/driver theo thiết bị thực.

Điều kiện qua bước: xác định đúng cổng của ESP, không nhầm thiết bị serial khác. Chưa nạp, đổi GPIO, cài driver ngẫu nhiên hoặc mở cổng mạng trong bước này.

Đối chiếu cổng bằng cách rút/cắm và xem Device Manager theo [hướng dẫn Espressif](https://docs.espressif.com/projects/esp-idf/en/v4.4/esp32s3/get-started/establish-serial-connection.html).

## Bước 2 đã đạt: đọc thông tin chip và flash

Đóng Serial Monitor nếu đang mở để giải phóng COM7. Từ thư mục gốc repo, chạy esptool đã được PlatformIO cài:

```powershell
.\.venv\Scripts\python.exe "$env:USERPROFILE\.platformio\packages\tool-esptoolpy\esptool.py" --chip esp32s3 --port COM7 flash_id
```

Lệnh đọc thông tin chip/flash, không ghi hoặc xoá firmware trong flash. Esptool có thể reset board và nạp chương trình trợ giúp tạm vào RAM để đọc. Gửi toàn bộ kết quả để đối chiếu chip, dung lượng flash và thông tin PSRAM nếu công cụ có báo. Cấu hình build 4 MB chưa phải số đọc từ chip thật.

Nếu dừng ở Connecting hoặc báo port bận, giữ nguyên kết quả lỗi để chẩn đoán; chưa thay GPIO hoặc nạp firmware.

Kết quả Trung gửi ngày 2026-11-05:

| Mục | Kết quả từ esptool4.11.0 |
|---|---|
| Chip | ESP32-S3 QFN56 rev0.2 |
| Flash | 4 MB, XMC; manufacturer46, device4016 |
| PSRAM | Chip báo Embedded PSRAM2 MB, AP_3v3; chưa kiểm tra cấp phát/chạy runtime |
| Crystal | 40 MHz; đây là thạch anh, không phải tốc độ CPU |
| USB | USB-Serial/JTAG trên COM7 |
| eFuse flash | Quad, điện áp3.3 V |

Flash4 MB khớp platformio.ini hiện tại. Không tự bật PSRAM từ kết quả nhận dạng này; code hiện chưa cần PSRAM và chưa kiểm tra cấu hình RAM trên board.

## Bước 3 đã đạt theo xác nhận của Trung: đối chiếu dây và nguồn

Chỉ nhìn/đối chiếu dây đang có. Nếu cần chỉnh dây, ngắt nguồn trước.

| Cảm biến | Chân tín hiệu theo code |
|---|---|
| MAX30102 | SDA → GPIO8; SCL → GPIO9 |
| MPU6050 | SDA → GPIO5; SCL → GPIO11 |
| Grove GSR | SIG/analog → GPIO7 |

Các số là GPIO, không phải thứ tự lỗ cắm. Xác nhận thêm VCC của từng cảm biến đang nối3V3 hay5V và các GND có chung GND ESP không. Chưa kết luận dây đúng từ việc đọc được chip ESP.

[Grove GSR của Seeed](https://wiki.seeedstudio.com/Grove-GSR_Sensor/) hỗ trợ nguồn3.3V/5V và xuất điện áp analog. Cần xác nhận nguồn/đường tín hiệu thực trước khi thử ADC ESP32. Chưa cấp lại nguồn hoặc đổi dây khi chưa đối chiếu được mạch.

Trung trả lời: GPIO đúng bảng, VCC cả3 là3V3, GND đã chung. Đây là xác nhận đấu dây của người vận hành, chưa phải số đo điện áp hoặc bằng chứng driver đọc cảm biến thành công.

## Bước 4 đã đạt: laptop kết nối hotspot iPhone

Trước đó laptop ở Wi-Fi quán, IP192.168.110.167. Trung đã chuyển sang hotspot iPhone dùng5G Viettel; kiểm tra Windows thấy IP172.20.10.3 và gateway172.20.10.1. Không dùng lại IP quán cho firmware.

ESP32-S3 dùng [Wi-Fi2.4 GHz](https://www.espressif.com/en/products/socs/esp32-s3); giữ Tăng tối đa khả năng tương thích trên iPhone ở trạng thái bật. Việc laptop đã kết nối chưa chứng minh ESP đã vào Wi-Fi hoặc truy cập được laptop. Chưa đổi firewall hoặc profile mạng Windows.

Không gửi mật khẩu Wi-Fi trong chat. Thông tin bí mật sẽ điền trong file local bị Git bỏ qua ở bước cấu hình. Khi đổi mạng phải đọc lại IP LAN laptop, không dùng lại IP quán nếu đã chuyển hotspot.

## Bước 5 đã đạt: điền Wi-Fi vào firmware local

Đã chuẩn bị:

- Thư mục `infra/mosquitto/local/esp32-trung/`: account DEVICE riêng ESP32-001, nguồn DEVICE, transport MQTT, profile danh định50/50/20; không thay account simulator.
- `.env` root: Compose project `asd-ease-esp32-trung`, bind broker172.20.10.3:1883 và backend127.0.0.1:8000. Dữ liệu backend dùng volume riêng của project này.
- `ai/edge_firmware/include/network_config.h`: đã điền ID/broker/credential MQTT; tên Wi-Fi và mật khẩu Wi-Fi để rỗng cho Trung tự điền bằng editor.
- Đã kiểm tra Git bỏ qua cả3 đường cấu hình local, không có file secret nào được track.
- Broker/backend healthy; backend MQTT connected, số thiết bị sync0 là đúng vì chưa nạp/chạy ESP với cấu hình mới. Probe login bằng account backend/esp32 đã đạt, không gửi STATE_REQUEST hoặc gói đo giả.
- HTTP login và WS cookie handshake thực qua backend local đã đạt. Frontend hiện có trên localhost5173 trả200, title ASD-EASE; chưa là bằng chứng dữ liệu cảm biến lên UI.

Trong `ai/edge_firmware/include/network_config.h`, chỉ điền hai dòng:

```cpp
#define WIFI_SSID "TEN_WIFI_IPHONE"
#define WIFI_PASSWORD "MAT_KHAU_HOTSPOT"
```

Thay bằng tên/mật khẩu đúng trong mục Điểm truy cập cá nhân của iPhone, giữ dấu nháy kép. Các dòng MQTT đã điền sẵn. Lưu file rồi báo đã điền và lưu; không gửi file/nội dung password vào chat. Chưa nạp ở bước này.

Broker và backend đã được chạy bằng `docker compose up -d --build broker backend`. Frontend dùng tiến trình Vite đang có tại5173, không chạy thêm container frontend. Mạng hotspot hiện là Public; chưa mở thêm firewall, cần kiểm tra từ ESP sau nạp trước khi kết luận LAN thông suốt.

Trung xác nhận đã điền/lưu. Kiểm tra không in secret: SSID/password có giá trị và độ dài hợp lệ; ID/username/password MQTT khớp bộ credential DEVICE; broker172.20.10.3:1883, opt-in LAN bật. Đối chiếu SSID trong hồ sơ Wi-Fi bằng netsh không yêu cầu/in mật khẩu; tên profile Windows có thể có hậu tố khác SSID thực.

Build networking-enabled bằng env esp32s3_supermini đã SUCCESS: static RAM47180 byte, flash915953 byte. Đây là kết quả build, chưa phải số đo runtime hoặc bằng chứng kết nối board. Broker/backend vẫn healthy, MQTT connected/sync0; COM7 còn nhận đúng ESP.

## Bước 6 đã đạt: nạp firmware

Đóng Serial Monitor nếu đang giữ COM7. Từ thư mục gốc repo chạy:

```powershell
.\.venv\Scripts\python.exe -m platformio run -d ai/edge_firmware -e esp32s3_supermini -t upload --upload-port COM7
```

Giữ cáp USB trong khi nạp. Gửi phần cuối kết quả SUCCESS hoặc lỗi thực tế để tiếp tục. Chưa chạy env esp32s3_network_check vì đây chỉ là env compile-check, không kết nối thật. Chưa xác nhận upload hoặc radio/sensor PASS khi chưa có kết quả.

Trung đã gửi log upload SUCCESS21.78 giây: ghi firmware vào flash và Hash of data verified. Sau reset, backend báo synchronized_devices=1, queue trống, không có lỗi ingest trong counter lúc kiểm tra.

Probe đăng nhập HTTP rồi mở WS bằng cookie như browser đã đọc3 frame nguồn DEVICE, device_id ESP32-001, session_id=null, timestamp tăng143693 →144695 →145697 ms. GSR raw có giá trị, HR null tại thời điểm kiểm tra; chưa kết luận đủ3 cảm biến hoạt động hoặc độ chính xác sinh lý. Snapshot bằng chứng ở `infra/mosquitto/local/esp32-trung/evidence/live-smoke.jsonl`, được Git bỏ qua; không đưa số đo cá nhân vào tài liệu/fixture public.

## Bước 7 đã đạt: xem log cảm biến và mạng

Chạy tại repo:

```powershell
.\.venv\Scripts\python.exe -m platformio device monitor -d ai/edge_firmware -e esp32s3_supermini --port COM7 --baud 115200
```

Chờ10–15 giây. Gửi một dòng `[NET]` mới nhất và một gói JSON trạng thái cảm biến. Mong đợi wifi=1, mqtt=1, sync=1; các trạng thái NO_FINGER/CALIBRATING cần được diễn giải theo thực tế đang đặt ngón tay/đeo điện cực, không tự coi là lỗi mạng. Ctrl+C để thoát monitor và trả COM cho lần nạp sau.

Chưa nghiệm thu Dashboard browser, Start/Stop và các ca lỗi/độ trễ/rate/RAM thật. Không coi3 frame WS là hoàn tất toàn nhánh05.

Trung gửi đoạn log uptime335.9–360.0 s gồm25 dòng NET: wifi=1/mqtt=1/sync=1; fail/drop/invalid/controlDrop/error/fatal đều0, pending/outbox0. HeapMin201764 byte, network stack watermark3780 byte, max loopGap10 ms. Từ chênh bộ đếm mẫu và uptime làm tròn: tốc độ mẫu được phần mềm xử lý xấp xỉ PPG50.08/IMU49.75/GSR19.92 Hz trong24.1 s. Chưa chứng minh không mất mẫu FIFO hoặc ổn định dài hạn; chưa có đối chứng mạng tắt/Serial tắt để hoàn tất F17.

Driver GSR và IMU báo VALID; PPG báo NO_FINGER. Điều này xác nhận trạng thái driver/giao tiếp, chưa chứng minh các giá trị điện da/nhịp tim đã được hiệu chuẩn. Raw log chỉ lưu tại `infra/mosquitto/local/esp32-trung/evidence/serial-initial.txt` bị Git bỏ qua.

## Bước 8 đã đạt smoke test: MAX30102 nhận ngón tay

Giữ Serial Monitor đang mở. Đặt nhẹ đầu ngón tay che mặt kính/LED của MAX30102, giữ yên khoảng20–30 giây, không ấn mạnh hoặc di chuyển board. Theo code hiện tại, có ngón tay thì NO_FINGER chuyển sang ACQUIRING (enum PULSE_ACQUIRING); cần ít nhất2 nhịp được driver chấp nhận và HR đạt điều kiện mới thành VALID.

Gửi5–10 dòng PPG mới cùng một dòng NET. Nếu vẫn NO_FINGER hoặc ACQUIRING thì giữ nguyên log để chẩn đoán ánh sáng/tín hiệu/driver, không đổi ngưỡng hoặc gán số HR để làm giao diện có dữ liệu.

Trung đã gửi ảnh PPG VALID và có HR, cùng GSR/IMU VALID. Trung yêu cầu thử đường truyền, chưa giữ đo lâu để đánh giá ổn định; ghi nhận đúng mức smoke test, không dùng các số HR/SpO2 để kết luận sinh lý.

Lần chụp này ở uptime khoảng116–117 s, NET vẫn wifi/mqtt/sync1, lỗi0; heapMin202632 byte, stackWater3780 byte nhưng loopGap106 ms. Giữ riêng cửa sổ này với log uptime335.9–360 s trước đó, chưa có đủ bằng chứng cùng boot hoặc bài đối chứng để kết luận F17. Cần xem lại spike106 ms khi đo sensing/Serial/network sau.

## Bước 9 hiện tại: mở Dashboard bằng một lệnh

Trung yêu cầu bỏ DevTools/token và dùng cùng cách trên2 máy. Đã thêm launcher/phiên localhost; xem [hướng dẫn Trung/Tân](05-ONE-COMMAND-DEV.md). Từ root hoặc frontend chỉ chạy:

```powershell
npm run dev
```

Lệnh tự bật dịch vụ, mở localhost5173 và cấp cookie HttpOnly. Chọn ESP32-001 nếu cần. Docker Desktop cần chạy; firmware ESP phải có Wi-Fi/IP/credential đúng. Đổi mạng thì sửa header và nạp lại theo hướng dẫn.

Đã thử cả2 entry cùng client auto-session→cookie→3 frame DEVICE thật, không nhập token. Chờ Trung xác nhận UI; browser tool hiện không khả dụng.

Nếu đã nhấc ngón tay, HR có thể trở về null/— theo freshness; đây không phải bằng chứng mất mạng. Movement/probability vẫn null khi chưa có thuật toán/mô hình. Chưa đánh F18 PASS trước khi Trung hoặc browser thật xác nhận UI.

Sau mỗi bước, ghi kết quả/lệnh và thời điểm vào đây hoặc 05-VERIFICATION.md để giữ tiến độ qua nhiều buổi làm.
