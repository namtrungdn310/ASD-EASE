# Cài đặt và cấu hình trên máy

## File cấu hình

- .env.example là mẫu được theo dõi trong Git, không chứa secret thật.
- Backend đọc .env theo thư mục chạy; chạy backend trực tiếp từ backend/.
- Vite đọc cấu hình trong frontend/, dùng frontend/.env.local để ghi giá trị riêng.
- VITE_* là công khai, nằm trong mã build trình duyệt; không đặt mật khẩu/token/Wi-Fi.
- .env và .env.* được bỏ qua, trừ .env.example.

## Backend trực tiếp

**Từ nhánh04:** đọc [hướng dẫn MQTT/xác thực](integration/04-SETUP.md) trước. Chạy `scripts/setup_local_mqtt.py` để tạo registry và secret ngẫu nhiên, rồi nạp backend.env vào tiến trình. Mẫu .env có secret trống nên không thể chạy nguyên xi. Giữ cấu hình local cũ, không ghi đè.

Chỉ sao chép khi chưa có cấu hình local; không ghi đè file đang dùng:

```powershell
Copy-Item -LiteralPath .env.example -Destination backend/.env
```

Settings bỏ qua khoá thừa; Vite trong file backend không cấu hình frontend. Ngoài DATABASE_URL/RAW_STORAGE_DIR/CORS_ORIGINS, nhánh04 thêm registry, MQTT, token người vận hành và cookie; xem .env.example và hướng dẫn liên kết trên. Host/port HTTP truyền qua Uvicorn.

```powershell
Push-Location backend
..\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1
Pop-Location
```

Chạy đúng thư mục để SQLite và đường lưu tương đối trỏ về backend.

## Frontend trực tiếp

Nếu cần, tạo frontend/.env.local:

```dotenv
VITE_API_BASE_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000/api/v1/ws/live
```

Từ thư mục gốc:

```powershell
npm --prefix frontend run dev
```

Vite đọc biến khi khởi động/build. Đổi cấu hình thì khởi động lại dev server hoặc build lại. Đổi biến môi trường runtime không tự sửa bundle tĩnh.

## Docker Compose

```powershell
.\.venv\Scripts\python.exe scripts/setup_local_mqtt.py
docker compose --profile ai config --quiet
docker compose up -d --build backend frontend
```

compose.yaml đặt trực tiếp đường lưu container và build.args frontend. .env ở root không tự thay các giá trị không được nội suy; cần sửa cấu hình phù hợp, build lại frontend khi đổi Vite. Secret thật ở file local bị bỏ qua.

## Firmware và LAN

- platformio.ini hiện dùng esp32s3_supermini, firmware0.2.0, board esp32-s3-devkitc-1, flash cấu hình4 MB. Chưa phải kết quả nhận dạng board.
- Build từ root: .\.venv\Scripts\pio.exe run -d ai/edge_firmware.
- Wi-Fi/credential local nằm trong ai/edge_firmware/include/network_config.h bị bỏ qua; file example có trong Git. Chép file này chưa làm networking hoạt động.
- ESP32 dùng IP LAN laptop. localhost trên ESP32 là chính nó; tên service Docker không phải DNS LAN.
- Broker MQTT có địa chỉ/cổng riêng; HTTP raw dùng backend8000. Backend MQTT đã có ở04; firmware MQTT ở05, raw client/lưu bền ở06/07. Broker demo chỉ mở loopback, muốn thử LAN cần cấu hình quyền và listener theo hướng dẫn04.
- Browser trên máy LAN khác cũng không dùng localhost để trỏ laptop; cần API/WS URL và CORS đúng.

## File IDE sinh tự động

.vscode và compile_commands.json chứa đường dẫn máy riêng, không nên chia sẻ như cấu hình chung. PR #11 có đưa lại một số file sinh tự động; không xoá chúng trong lượt chỉnh tài liệu này. Tạo lại bằng PlatformIO khi cần.

Xem [phần cứng](HARDWARE_PROFILE.md) và [tiến độ](integration/PROGRESS.md).
