# Chạy backend MQTT và thiết bị giả lập

Áp dụng nhánh `feature/backend-session-lifecycle`, cập nhật 2026-11-01. Dữ liệu demo luôn SYNTHETIC. Không cần ESP32 để thử nhánh04; firmware MQTT thuộc05, lưu raw bền/chống trùng thuộc06.

## 1. Cài thư viện và tạo cấu hình local

PowerShell ở thư mục gốc, dùng Python3.12 và Docker Desktop đang chạy:

```powershell
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt -r ai/requirements.txt
.\.venv\Scripts\python.exe scripts/setup_local_mqtt.py
```

Công cụ tạo `infra/mosquitto/local/` đã bị Git bỏ qua: mật khẩu broker đã băm, ACL riêng từng tài khoản, registry, cấu hình backend và credential simulator. Secret ngẫu nhiên, không in ra terminal; không ghi đè cấu hình đã có. Giữ các file này trên máy người vận hành. Cấu hình demo có SIM-001 và SIM-OTHER, cùng nguồn SYNTHETIC.

Chọn **một** transport cho một thiết bị. Mặc định SIM-001 dùng MQTT. Muốn thử simulator HTTP cũ, tạo cấu hình ở thư mục mới bằng `--directory <thư mục mới> --http-simulator`; trỏ registry/backend tới thư mục đó. Không đồng thời chạy hai simulator cùng SIM-001.

## 2. Chạy bằng Compose

```powershell
docker compose config --quiet
docker compose up -d --build broker backend frontend
```

Broker loopback `127.0.0.1:1883`, backend `http://localhost:8000`, Dashboard `http://localhost:5173`. HTTP health công khai ở `/api/v1/health`; dữ liệu/điều khiển cần đăng nhập. Broker chỉ mount file passwords/ACL, không đọc secret người vận hành. Backend đọc cấu hình local qua env_file, registry qua mount chỉ đọc.

Lần khởi động đầu với DB cũ: tự sao lưu `*.db.v0-<UTC>.bak` trong cùng vùng lưu, rồi chuyển schema SQLite0→1 bằng transaction. Không xoá volume hoặc JSONL cũ. Nếu không sao lưu/chuyển đổi được, backend dừng; không chạy tiếp với DB nửa chừng.

## 3. Chạy backend trực tiếp thay cho container

Không chạy cả backend trực tiếp và backend Compose cùng DB/client ID. Nạp env vào đúng tiến trình PowerShell, không in secret:

```powershell
Get-Content infra/mosquitto/local/backend.env | ForEach-Object {
    $setting = $_ -split '=', 2
    if ($setting.Count -eq 2) { [Environment]::SetEnvironmentVariable($setting[0], $setting[1], 'Process') }
}
docker compose up -d broker
Push-Location backend
..\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1
Pop-Location
```

Không dùng `--reload` hoặc nhiều worker cho receiver. Khoá file chặn hai tiến trình dùng cùng receiver lock; DB vẫn chặn hai phiên mở cùng thiết bị. Mặc định các URL/đường DB tương đối theo thư mục backend. Cấu hình trong backend/.env cũ không được ghi đè file mới; biến môi trường trên ưu tiên hơn .env.

## 4. Đăng nhập và điều khiển

Terminal điều khiển nạp `backend.env` như bước3, rồi:

```powershell
$operatorHeaders = @{ Authorization = "Bearer $env:OPERATOR_TOKEN" }
Invoke-RestMethod http://localhost:8000/api/v1/health/mqtt -Headers $operatorHeaders
$recordingId = 'SYN-' + [guid]::NewGuid().ToString('N')
$startBody = @{ session_id = $recordingId; device_id = 'SIM-001' } | ConvertTo-Json
Invoke-RestMethod http://localhost:8000/api/v1/sessions/start -Method Post -Headers $operatorHeaders -ContentType application/json -Body $startBody
```

Start trả202/STARTING sau lưu phiên+lệnh. Chưa có simulator online thì lệnh chờ; quá30 s không ACK sẽ ABORTED, không giả đang thu. Vì vậy nên khởi động simulator ở bước5 trước khi bấm Start.

```powershell
Invoke-RestMethod http://localhost:8000/api/v1/sessions -Headers $operatorHeaders
$stopBody = @{ session_id = $recordingId } | ConvertTo-Json
Invoke-RestMethod http://localhost:8000/api/v1/sessions/stop -Method Post -Headers $operatorHeaders -ContentType application/json -Body $stopBody
```

Browser không cần và không được nhúng bearer token vào bundle. Trước UI09 có thể đăng nhập qua DevTools Console của trang `http://localhost:5173`:

```javascript
await fetch('http://localhost:8000/api/v1/auth/login', {
  method: 'POST', credentials: 'include',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({token: prompt('Nhập OPERATOR_TOKEN từ file local')})
});
```

Chỉ nhập token trên trang local tin cậy. Token không lưu localStorage hoặc URL; backend trả cookie HttpOnly/SameSite=Lax, hết hạn1 giờ. Đóng Console và tải lại Dashboard để socket gửi cookie. Dùng cùng hostname `localhost` ở cả frontend/backend, không trộn localhost với127.0.0.1. POST có cookie và WS cần Origin đúng CORS. API gọi bằng cookie cần `credentials:'include'`; đăng xuất bằng POST `/api/v1/auth/logout`. Đổi COOKIE_SECRET để thu hồi toàn bộ cookie hiện có. UI đăng nhập hoàn chỉnh chưa thuộc nhánh04.

## 5. Chạy thiết bị MQTT giả

Terminal khác, từ root:

```powershell
.\.venv\Scripts\python.exe -m ai.simulator.mqtt_device --credentials infra/mosquitto/local/simulator.json
```

Simulator hỏi trạng thái sau SUBACK và mỗi15 s, nhận Start/Stop QoS1, gửi ACK và đợi state confirmation trước telemetry1 Hz. Reconnect đổi connection_id, reboot đổi boot_id. Payload demo là giá trị gán sẵn, không suy luận AI hoặc số đo người thật.

Simulator này chưa ghi raw: Stop báo zero-batch/raw_recording_enabled=false; backend STOPPED nhưng recording_complete=false với RAW_RECORDING_DISABLED. Khi raw được bật và không có batch, có thể complete-empty; không coi đây là bộ dữ liệu hữu ích. Có raw thì phải chờ đối chiếu ở06, không báo đủ từ ACK Stop.

Simulator HTTP cũ: registry phải dùng transport=http; đặt DEVICE_HTTP_TOKEN của SIM-001 và OPERATOR_TOKEN vào biến môi trường của tiến trình simulator, chạy với PYTHONPATH=ai. Nó dùng `/devices/sync` và `/devices/ack` để mô phỏng cùng handshake. Đây là đường tương thích cho simulator HTTP, không yêu cầu firmware MQTT poll HTTP. Mỗi replay tạo session_id mới; file replay dùng lại ID đã đóng phải đổi ID có kiểm soát trước chạy lại. --send-raw vẫn append JSONL có quyền/phiên hợp lệ, chưa có bảo đảm lưu bền của06.

## 6. Kiểm thử riêng, không đụng dữ liệu nhóm

```powershell
Push-Location backend
..\.venv\Scripts\python.exe -m pytest -q
Pop-Location
.\.venv\Scripts\python.exe .github/scripts/check-mock-transport.py
.\.venv\Scripts\python.exe scripts/check_mqtt_integration.py
```

Kiểm thử MQTT tự tạo container có tên riêng, cổng loopback riêng, secret/DB/raw tạm; tự dọn đúng container đó khi xong. Cần Docker thật, không tự skip rồi gọi PASS. CI chạy hai bài tích hợp trong check Backend tests, giữ nguyên6 tên check bảo vệ nhánh.

## Vận hành, LAN và khôi phục

- API tra cứu vẫn dùng được khi broker lỗi; `/health/mqtt` báo kết nối, số thiết bị đã đồng bộ, hàng đợi và bộ đếm lỗi. Không dùng presence retained hoặc PUBACK làm bằng chứng đang thu.
- Mặc định broker chỉ mở loopback. Khi thử ESP32, chủ máy chọn IP LAN riêng cho port mapping và backend; kiểm tra ACL/registry trước. Không mở ra Internet hoặc thay tường lửa toàn máy. Cấu hình demo TCP1883/HTTP8000 chỉ có xác thực, **không mã hoá**.
- Ngoài LAN phát triển riêng phải dùng TLS/reverse proxy: mẫu broker ở `infra/mosquitto/tls.conf.example`, backend `MQTT_CA_FILE` kiểm tra CA/hostname, COOKIE_SECURE=true, ALLOW_INSECURE_LOCAL=false. File mẫu TLS chưa được nghiệm thu triển khai chứng chỉ; không dùng tls_insecure_set hoặc bỏ kiểm tra.
- Thêm thiết bị thật: đăng ký ID/nguồn DEVICE/profile trong registry, tài khoản MQTT riêng và ACL đúng6 topic; tạo token HTTP riêng tối thiểu32 ký tự. Dùng mosquitto_passwd tương tác để thêm tài khoản vào file băm, không đặt mật khẩu trong lệnh/Git. Đồng bộ thay đổi registry/ACL, khởi động lại backend/broker; giữ bản sao credential trước sửa. Không đổi nguồn chỉ bằng prefix tên.
- DB cũ giữ phiên LEGACY/UNKNOWN, không đoán nguồn hoặc thời điểm đã dừng. Phiên legacy chưa đóng chặn Start đến khi thiết bị đăng ký đồng bộ IDLE/STOPPED hoặc người vận hành đối chiếu rõ.
- Khôi phục: dừng backend, nạp cấu hình local, từ backend chạy `python -m app.db.migrations --restore <bản-sao.bak> --to <DB-mới.db>`. Công cụ chỉ tạo file mới, không ghi đè. Kiểm tra DB mới rồi trỏ DATABASE_URL và chạy phiên bản code phù hợp; giữ DB lỗi và raw để đối chiếu. Không xoá DB để sửa migration.
- Bằng chứng nhánh04 ở [bàn giao](04-HANDOFF.md); chưa phải nghiệm thu ESP32, raw lưu bền, JCS hoặc thuật toán AI.
