# Kiểm tra nhánh 5

Ngày 2026-11-03, Windows, Python3.12. Code hoàn thiện tại d1101c5 trên nhánh `feature/firmware-telemetry-client-completion`, base dev `1e73aea`. Board ở chỗ Tân, serial discovery trên máy này trả [].

**WAITING_HARDWARE cho nghiệm thu.** Code và tài liệu được bàn giao qua [PR #15 vào dev](https://github.com/namtrungdn310/ASD-EASE/pull/15) theo yêu cầu Trung; kết quả CI/head/merge tra trực tiếp tại PR. Bảng local dưới đây không thay bằng chứng CI.

## Kết quả local

| Bài | Kết quả | Phạm vi |
|---|---|---|
| PlatformIO esp32s3_supermini | PASS | Build/link mặc định mạng tắt, không cần secret |
| PlatformIO esp32s3_network_check | PASS | Compile/link đủ ESP-MQTT/TLS bằng cấu hình build-only, không tự kết nối |
| Header compatibility | PASS4/4 | Các thứ tự include chung/cũ |
| Native C++ protocol | PASS30 tests | Core/serializer production → schema Pydantic runtime; clock/transport giả |
| Native C++ qua Mosquitto | PASS7 nhóm | Paho làm transport test, core C++ xử lý JSON/phiên; broker/API/DB/WS thật, dữ liệu SYNTHETIC |
| Backend pytest | PASS61 | Gồm chặn topic cũ/sai nguồn |
| AI pytest | PASS15 | Hồi quy hiện có |
| Frontend tests/build/audit | PASS26, build đạt, audit0 | React/jsdom; chưa là kiểm tra browser bằng board |
| HTTP transport | PASS19 frame | HTTP/simulator → WS thật, gồm nối lại; không board |
| Compose mặc định/LAN | PASS | config --quiet; bind IP cụ thể đúng1 port, chọn đúng thư mục credential; không in secret |
| MQTT simulator Python | PASS7 nhóm | Bài hồi quy riêng qua broker thật, không thay core C++ |

Static size ở lần build cuối:
- Mạng tắt: RAM20636/327680 byte, flash322293/1310720 byte.
- Build-check mạng: RAM47180/327680 byte, flash913889/1310720 byte.
- Đây là kích thước link, chưa tính/đo heap, task stack, queue và TLS runtime trên board. Không suy RAM còn đủ cho07 từ các số này.

Cảnh báo hiện có: frontend bundle khoảng590 kB vượt ngưỡng500 kB; không làm build lỗi. Python có cảnh báo deprecation của dependency. Không sửa dependency không liên quan để che cảnh báo.

## F01–F19

PASS_SW chỉ nghĩa phần mềm được kiểm tra. NOT_RUN_HW nghĩa chưa chạy trên ESP32 thật; không dùng PASS_SW thay nghiệm thu phần cứng.

| ID | Kết quả | Bằng chứng đã có / việc Tân cần xác nhận |
|---|---|---|
| F01 | PASS_SW | Hai env PlatformIO; không cần network_config.h/credential thật. |
| F02 | PASS_SW | Native harness compile chính session_protocol.cpp và xuất JSON; InboundTelemetry/control.py kiểm tra thực. Không dùng fixture Python thay serializer. |
| F03 | PASS_SW; NOT_RUN_HW | Test tuổi HR/PPG/GSR/NaN/0/baseline/null và CALIBRATING; cần tháo cảm biến/chờ TTL trên board. |
| F04 | NOT_RUN_HW | Chưa ESP32/LAN/SUBACK; code ESP-MQTT đã link. Credential DEVICE riêng/profile50/50/20 được Registry kiểm tra và account thật thử ACL trong broker test. |
| F05 | PASS_SW; NOT_RUN_HW | Core ngoài phiên dùng boot timestamp/session=null sau sync. Chờ DEVICE thật→DB/WS/Dashboard. |
| F06 | PASS_SW; NOT_RUN_HW | Core + broker thật Start→ACK→DB RECORDING→WS. Chờ ESP-MQTT/cảm biến thật. |
| F07 | PASS_SW; NOT_RUN_HW | Topic/pending_command trùng chỉ Start một lần, epoch giữ; chờ lặp thật trên board. |
| F08 | PASS_SW; NOT_RUN_HW | Profile/ID/boot/connection/request/generation/lease; lệnh sai không Start. Chờ thiết bị thật. |
| F09 | PASS_SW; NOT_RUN_HW | Stop zero-batch/raw-disabled, DB complete=false đúng. Chờ Stop vật lý và đo độ trễ. |
| F10 | PASS_SW; NOT_RUN_HW | STOP trước START confirmation, START cũ tới muộn không làm ghi lại; chờ board. |
| F11 | NOT_RUN_HW | Chưa thử Wi-Fi sai/mất/khôi phục khi cảm biến đang đọc; cần đo rate/gap/bộ nhớ. |
| F12 | PASS_SW; NOT_RUN_HW | Broker thật restart, core giữ epoch/đồng bộ; LWT nonce mới có native test. Chờ ESP-MQTT reconnect/LWT thật. |
| F13 | PASS_SW; NOT_RUN_HW | Backend thật restart khi broker còn, DB/ACK/phiên phục hồi, sync lại. Chờ board. |
| F14 | PASS_SW; NOT_RUN_HW | Khởi tạo core boot mới không giữ Start/epoch; chờ reboot ESP32 đang thu và log backend. |
| F15 | NOT_RUN_HW | Serializer có test null/stale; chưa tháo cảm biến khi MQTT vẫn tốt. |
| F16 | PASS_SW; NOT_RUN_HW | Broker thật chặn anonymous/sai password/cross-device; native chặn retained/nonce cũ/quá gói/JSON trùng/sai số. Chờ SDK auth/ACL/TLS/retained thật. |
| F17 | NOT_RUN_HW | Chưa có số đo sensing/network/Serial, heap/stack/timing; không điền số danh định làm số đo. |
| F18 | NOT_RUN_HW | Frontend26 tests đạt nhưng chưa ảnh browser nhận ESP32 thật. |
| F19 | PASS_SW local; CI xem PR | Backend/AI/frontend/firmware/header/HTTP/native MQTT đạt theo bảng; cả6 check được theo dõi tại PR #15 trên head cuối. |

## Lệnh tái hiện

PowerShell tại root, venv đã cài requirements backend/AI và PlatformIO. Native cần g++/clang++ C++17; Windows máy này dùng C:\msys64\ucrt64\bin\g++.exe (thêm thư mục vào PATH), Linux CI dùng g++ có sẵn.

```powershell
.\.venv\Scripts\python.exe -m platformio run -d ai/edge_firmware
.\.venv\Scripts\python.exe .github/scripts/check-firmware-headers.py
.\.venv\Scripts\python.exe scripts/check_firmware_protocol.py
.\.venv\Scripts\python.exe scripts/check_mqtt_integration.py --native-firmware
.\.venv\Scripts\python.exe scripts/check_mqtt_integration.py
.\.venv\Scripts\python.exe .github/scripts/check-mock-transport.py
Push-Location backend
..\.venv\Scripts\python.exe -m pytest -q
Pop-Location
Push-Location ai
..\.venv\Scripts\python.exe -m pytest -q
Pop-Location
npm --prefix frontend test
npm --prefix frontend run build
npm --prefix frontend audit --omit=dev
docker compose config --quiet
```

Bài MQTT tạo container/port/DB/secret tạm riêng, dọn đúng container khi xong; không dùng hoặc sửa dữ liệu nhóm. Hai chế độ MQTT dùng cùng bài7 nhóm, một chế độ simulator Python, một chế độ core C++ với Paho transport test. Chưa chạy phần radio/driver ESP-MQTT trên ESP32.

## Mẫu điền nghiệm thu board

Tân bổ sung ngày, SHA firmware/backend/frontend, board/flash/PSRAM thực, dây, SSID đã che, IP/port, profile, firmware version; không lưu password/token. Mỗi Fxx ghi thao tác, kết quả mong đợi/thực tế, log/ảnh đã che secret và PASS/FAIL.

Đo cùng cửa sổ60 s: số PPG/IMU/GSR được xử lý, khoảng trống lớn nhất, lỗi FIFO, Start/Stop latency, heapMin, stack watermark byte, queue/outbox; so mạng tắt/mạng bật/Serial giảm. Nếu fail, giữ log và lỗi, không sửa schema/ngưỡng hoặc đánh PASS bằng kết quả mô phỏng.
