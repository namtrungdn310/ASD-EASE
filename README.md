# Vòng tay Edge AI hỗ trợ nghiên cứu trạng thái cần chú ý ở học sinh ASD

Đây là nguyên mẫu nghiên cứu kỹ thuật, **không phải thiết bị y tế**; không chẩn đoán lo âu, ASD hoặc tình trạng y khoa/tâm thần. ATTENTION chỉ mô tả kết quả theo tiêu chí kỹ thuật.

## Hệ thống mục tiêu

ESP32-S3 Super Mini tự xử lý tín hiệu, kiểm tra chất lượng, tạo mức nền/đặc trưng, chạy mô hình và quyết định trạng thái. Laptop chỉ nhận/lưu và hiển thị trên LAN; không cần Internet hoặc USB truyền dữ liệu khi thi đấu.

MQTT dùng cho telemetry/điều khiển, HTTP cho raw, WebSocket cho trình duyệt. Nhánh04 đã triển khai backend MQTT và thử bằng thiết bị giả qua broker thật; client ESP32 thuộc nhánh05.

## Cấu trúc

- backend/: FastAPI, SQLite, nhận file raw và WebSocket.
- frontend/: dashboard React/TypeScript/Vite/Tailwind/Recharts.
- ai/: giả lập, nghiên cứu và firmware tại ai/edge_firmware/.
- docs/: đặc tả, kiến trúc, kế hoạch và tiến độ.

Chỉ có ba thư mục mã nguồn backend, frontend, ai. Công nghệ chính: Python3.12, FastAPI/Pydantic/SQLAlchemy, React/TypeScript, NumPy/matplotlib, Arduino/PlatformIO và Docker Compose.

## Làm việc

USB dùng khi phát triển/nạp/xem log. Thu nghiên cứu gửi raw để xử lý trên máy. Khi thi đấu, ESP32 dùng pin và tự suy luận.

Mỗi việc có nhánh feature/*, fix/*, docs/* hoặc chore/* → PR vào dev. Bản ổn định dùng PRdev → main. Không push trực tiếp; Tân cần Trung review, PR của Trung chỉ dùng ngoại lệ sau đủ CI, cập nhật và không xung đột.

Xem [Git/GitHub](docs/GIT_WORKFLOW.md), [10 nhánh tích hợp](docs/integration/README.md), [tiến độ nhánh](docs/integration/PROGRESS.md).

## Chạy thử

Đọc [cài đặt local](docs/LOCAL_SETUP.md). Cần Docker Desktop/Compose; chạy trực tiếp cần Python3.12+, Node22+ và PlatformIO.

```bash
python scripts/setup_local_mqtt.py
docker compose up --build
```

Dashboard: <http://localhost:5173>. API health: <http://localhost:8000/api/v1/health>. OpenAPI: <http://localhost:8000/docs>.

Lần đầu cần tạo credential local, đăng nhập trước khi Dashboard nhận dữ liệu. Xem [hướng dẫn nhánh04](docs/integration/04-SETUP.md). ESP32 dùng IP LAN laptop, không dùng localhost; broker demo mặc định chỉ mở loopback.

## Chạy thiết bị giả lập

Sau khi backend/frontend đã chạy, thiết bị giả MQTT:

```bash
python -m ai.simulator.mqtt_device --credentials infra/mosquitto/local/simulator.json
```

Đầu ra luôn là SYNTHETIC TEST DATA, không phải dữ liệu người thật/bằng chứng khoa học. Simulator HTTP cũ cần registry transport=http và token theo [hướng dẫn](docs/integration/04-SETUP.md). Xem [đặc tả giả lập](docs/SYNTHETIC_DATA_SPEC.md).

## Kiểm tra

PowerShell tại thư mục gốc, sau khi đã có .venv và dependencies:

```powershell
Push-Location backend
..\.venv\Scripts\python.exe -m pytest -q
Pop-Location
Push-Location ai
..\.venv\Scripts\python.exe -m pytest -q
Pop-Location
npm --prefix frontend test
npm --prefix frontend run build
docker compose config --quiet
.\.venv\Scripts\python.exe docs/contracts/check_examples.py
.\.venv\Scripts\python.exe .github/scripts/check-mock-transport.py
.\.venv\Scripts\python.exe scripts/check_mqtt_integration.py
```

Firmware build trên máy, không trong Docker:

```powershell
.\.venv\Scripts\pio.exe run -d ai/edge_firmware
```

Profile build ESP32-S3 là cấu hình tạm, không chứng minh board/cảm biến hoạt động.

## Đang ở đâu?

Giai đoạn01 đã DONE;02 còn thiếu nghiệm thu trực quan. Driver03–06 có code nhưng thiếu phép đo. Nhánh tích hợp03 đã merge [PR #12](https://github.com/namtrungdn310/ASD-EASE/pull/12), commit752bd5d. Nhánh04 có backend MQTT/phiên đã kiểm thử và push [PR #13](https://github.com/namtrungdn310/ASD-EASE/pull/13); hoàn tất khi PR merge vào dev sau đủ CI. Hai hệ đánh số giai đoạn và nhánh khác nhau.

Xem [tiến độ giai đoạn](docs/PROGRESS.md), [bàn giao03](docs/integration/03-HANDOFF.md) và [mục lục](docs/README.md). Không suy hoàn thành từ file khung.

## Riêng tư

Chỉ dùng ID giả danh. Không đưa tên học sinh, dữ liệu người tham gia, chú thích riêng tư hoặc thông tin Wi-Fi/token lên Git. Không diễn giải HR/GSR/chuyển động như chẩn đoán lo âu.
