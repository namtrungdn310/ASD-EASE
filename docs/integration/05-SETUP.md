# Chạy ESP32 thật qua MQTT trong LAN

Cập nhật 2026-11-03. Code ở nhánh `feature/firmware-telemetry-client-completion`, từ dev `1e73aea`. Board hiện ở chỗ Tân; hướng dẫn này chưa thay bằng chứng nạp/chạy thật. Xem [kết quả kiểm tra](05-VERIFICATION.md) và [bàn giao](05-HANDOFF.md).

## 1. Chuẩn bị

- Python 3.12, môi trường .venv, Node/npm, Docker Desktop đang chạy và PlatformIO.
- ESP32-S3, cảm biến và dây thật cần Tân xác nhận. Code giữ MAX30102 SDA8/SCL9, MPU6050 SDA5/SCL11, GSR ADC7 theo PR #14.
- Laptop và ESP32 trong LAN truy cập được nhau. Không dùng localhost hoặc tên service Docker làm địa chỉ broker trên ESP32.
- Chỉ một backend MQTT receiver, không chạy đồng thời container và Uvicorn trên cùng DB/client ID.

Từ thư mục gốc repo, PowerShell:

```powershell
.\.venv\Scripts\python.exe -m pip install platformio==6.2.0 -r backend/requirements.txt -r ai/requirements.txt
```

Platform đã pin espressif32 7.1.3; ArduinoJson 7.4.3. ESP-MQTT có sẵn trong SDK Arduino/ESP-IDF, không cài PubSubClient.

## 2. Tạo cấu hình thử riêng có thiết bị DEVICE

Tạo thư mục mới nằm trong vùng local bị Git bỏ qua; không ghi đè credential đang dùng:

```powershell
.\.venv\Scripts\python.exe scripts/setup_local_mqtt.py --directory infra/mosquitto/local/esp32-test --device-id ESP32-001
git check-ignore -v infra/mosquitto/local/esp32-test/firmware-device.json
```

Nếu thư mục đã có nội dung, tool dừng để bảo vệ cấu hình. Dùng lại cấu hình đúng hoặc chọn thư mục mới. Tool tạo SIM-001/SIM-OTHER nguồn SYNTHETIC và thêm ESP32-001 nguồn DEVICE với tài khoản esp32 riêng, token HTTP riêng và profile danh định PPG50/IMU50/GSR20 Hz. Không sửa tài khoản simulator thành DEVICE.

Các file cần đọc **bằng editor local**, không đưa vào chat/Git/ảnh:
- `firmware-device.json`: device_id, username/password MQTT của ESP32. HTTP token dành nhánh07, không đưa OPERATOR_TOKEN vào firmware.
- `device-registry.json`: nguồn DEVICE, transport mqtt, profile50/50/20, window1000 ms.
- `backend.env`: credential backend và token người vận hành.
- `passwords` là mật khẩu băm của broker; `acl` giới hạn topic từng thiết bị.

Mật khẩu ngẫu nhiên được sinh local, không in ra terminal. Tool tạo bộ cấu hình mới, chưa hỗ trợ thêm tài khoản vào bộ cấu hình đang vận hành. Khi đưa vào hệ đang dùng, cần đối chiếu/giữ các identity và credential cũ trước khi đổi cấu hình; không thay registry lúc đang thu.

## 3. Cho broker nghe trên IP LAN của laptop

Tìm IPv4 của adapter Wi-Fi/LAN đang dùng:

```powershell
Get-NetIPConfiguration
$env:MQTT_LOCAL_DIR = './infra/mosquitto/local/esp32-test'
$env:MQTT_BIND_IP = '192.168.1.10' # Thay bằng IP LAN thực của laptop
docker compose config --quiet
docker compose up -d --build broker backend frontend
docker compose port broker 1883
```

Kết quả port phải là IP đã chọn:1883. Compose mặc định vẫn 127.0.0.1; không dùng 0.0.0.0 hoặc mở thêm listener để né lỗi. Hai biến trên thuộc terminal hiện tại; mở terminal mới phải đặt lại hoặc lưu vào .env local. Không in toàn bộ `docker compose config` vì có thể chứa secret.

Ba địa chỉ khác nhau:
- ESP32: broker = IP LAN laptop, cổng1883.
- Backend container: broker = service `broker`, cổng1883.
- Browser laptop: Dashboard http://localhost:5173, API http://localhost:8000, WS ws://localhost:8000/api/v1/ws/live.

Nếu chạy backend trực tiếp theo [04-SETUP](04-SETUP.md), nạp backend.env rồi đặt MQTT_HOST bằng IP LAN đang bind; 127.0.0.1 không truy cập được listener chỉ bind IP LAN. Không chạy thêm backend Compose.

Nếu bị chặn, kiểm tra AP isolation, VPN và profile mạng Private. Chỉ khi cần, chủ máy tạo rule TCP1883 inbound trên adapter/IP LAN, profile Private, nguồn thiết bị hoặc LocalSubnet; không tắt tường lửa toàn máy. Thao tác sửa tường lửa cần quyền quản trị và chủ máy tự xác nhận.

1883 ở đây là **plaintext có xác thực trên LAN phát triển riêng**. Ngoài phạm vi này phải có broker TLS/chứng chỉ phù hợp, MQTT_USE_TLS=1 và CA kiểm tra hostname; không bỏ kiểm tra chứng chỉ. Nhánh này đã build nhánh TLS nhưng chưa nghiệm thu handshake/chứng chỉ/đồng hồ trên board.

## 4. Cấu hình và nạp ESP32

Mở `ai/edge_firmware/include/network_config.example.h`. Nếu chưa có file local, chép thành `network_config.h`; nếu đã có, đối chiếu và bổ sung, giữ cấu hình của Tân.

Điền đúng:
- ASD_NETWORK_ENABLED=1.
- SSID/password của Wi-Fi.
- MQTT_DEVICE_ID=`ESP32-001`, trùng registry.
- MQTT_BROKER_HOST=IP LAN laptop; MQTT_BROKER_PORT=1883.
- MQTT_USERNAME/MQTT_PASSWORD từ firmware-device.json.
- MQTT_USE_TLS=0 và ASD_ALLOW_INSECURE_LAN=1 chỉ cho LAN phát triển riêng.
- ASD_SERIAL_DIAGNOSTICS=1 để xem log; đặt0 khi so ảnh hưởng Serial. Log driver khởi động/lỗi vẫn có thể xuất hiện.

```powershell
git check-ignore -v ai/edge_firmware/include/network_config.h
git ls-files ai/edge_firmware/include/network_config.h
.\.venv\Scripts\python.exe -m platformio device list
.\.venv\Scripts\python.exe -m platformio run -d ai/edge_firmware -e esp32s3_supermini
.\.venv\Scripts\python.exe -m platformio run -d ai/edge_firmware -e esp32s3_supermini -t upload
.\.venv\Scripts\python.exe -m platformio device monitor -d ai/edge_firmware -e esp32s3_supermini
```

Lệnh ls-files phải không có kết quả. Chọn đúng COM/board thực nếu tự phát hiện không đúng. Cấu hình build 4MB không chứng minh flash/PSRAM thực tế.

**Không nạp env esp32s3_network_check để thử mạng.** Env này chỉ compile/link đủ SDK mạng/TLS bằng cấu hình không bí mật và chủ động không kết nối khi nạp nhầm. Env esp32s3_supermini mới đọc network_config.h local. Thiếu file/opt-in thì Serial-only, vẫn build được.

Log mong đợi: device/profile đúng, wifi=1, mqtt=1 rồi sync=1. Sync cần backend trả STATE_RESPONSE; broker online chưa đủ. NET metrics cập nhật khoảng5 s, telemetry khoảng1000 ms. Sai CONNACK/quyền/chứng chỉ sẽ dừng MQTT retry, báo fatal; sửa cấu hình rồi reboot. Mất mạng tạm thời dùng backoff1–30 s có jitter.

## 5. Xem Dashboard và thử Start/Stop

Nạp secret vào môi trường tiến trình mà không in ra:

```powershell
Get-Content infra/mosquitto/local/esp32-test/backend.env | ForEach-Object {
    $setting = $_ -split '=', 2
    if ($setting.Count -eq 2) { [Environment]::SetEnvironmentVariable($setting[0], $setting[1], 'Process') }
}
$operatorHeaders = @{ Authorization = "Bearer $env:OPERATOR_TOKEN" }
Invoke-RestMethod http://localhost:8000/api/v1/health/mqtt -Headers $operatorHeaders
```

Mở Dashboard, đăng nhập cookie theo mục4 của [04-SETUP](04-SETUP.md), rồi tải lại và chọn ESP32-001. Không đưa token vào VITE_*, URL hoặc localStorage. Browser dùng HTTP/WS hiện có, không kết nối broker trực tiếp.

Sau đồng bộ, telemetry ngoài phiên có session_id=null. HR có thể null khi chưa đo hợp lệ; GSR raw là ADC, delta là tỷ lệ. Movement/probability null, quality0 và UNCERTAIN/CALIBRATING là quy ước đúng khi chưa có thuật toán/mô hình; không cần mọi biểu đồ đều có đường.

Chỉ Start khi thiết bị online/sync:

```powershell
$recordingId = 'DEVICE-' + [guid]::NewGuid().ToString('N')
$startBody = @{ session_id = $recordingId; device_id = 'ESP32-001' } | ConvertTo-Json
Invoke-RestMethod http://localhost:8000/api/v1/sessions/start -Method Post -Headers $operatorHeaders -ContentType application/json -Body $startBody
Invoke-RestMethod http://localhost:8000/api/v1/sessions -Headers $operatorHeaders
$stopBody = @{ session_id = $recordingId } | ConvertTo-Json
Invoke-RestMethod http://localhost:8000/api/v1/sessions/stop -Method Post -Headers $operatorHeaders -ContentType application/json -Body $stopBody
```

Start: STARTING → ACK STARTED → RECORDING, chỉ sau backend xác nhận mới gửi telemetry theo phiên. Stop: STOPPING → thực thi → ACK STOPPED. Nhánh05 chưa ghi raw: summary zero-batch/cutoff0/raw_recording_enabled=false, backend recording_complete=false/RAW_RECORDING_DISABLED. Đây là kết quả dự kiến, không sửa thành complete=true. Lần thu mới dùng session_id mới.

## 6. Đo và bàn giao cho Trung

Điền [F01–F19](05-VERIFICATION.md) bằng board/commit/cấu hình thực. So cùng khoảng60 s trong ba chế độ: mạng tắt, mạng bật+Serial, mạng bật giảm Serial; thêm ca mất Wi-Fi/broker/backend.

Lưu phần chênh số mẫu/giây, max loopGap, heapMin, stackWater, queue/outbox, thời gian Start/Stop và ảnh Dashboard. Bộ đếm mẫu là số đọc/FIFO được phần mềm xử lý, chưa chứng minh không mất mẫu phần cứng; cần đối chiếu FIFO/rate thực. Stack watermark theo ESP-IDF của framework này tính bằng byte, không nhân4 theo FreeRTOS upstream. Static RAM/flash từ build khác RAM/stack chạy thật.

Raw HTTP/batch/đối chiếu đủ dữ liệu chưa thuộc05. Thiết bị phục vụ nghiên cứu kỹ thuật, không diễn giải HR/GSR thành chẩn đoán y khoa.
