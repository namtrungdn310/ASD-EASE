# Vòng tay thông minh ứng dụng Edge AI hỗ trợ nhận diện sớm trạng thái lo âu ở học sinh ASD trong môi trường giáo dục

Đây là nguyên mẫu nghiên cứu kỹ thuật sinh viên về wearable Edge AI, IoT mạng cục bộ và cảm biến đa phương thức. Hệ thống **không phải thiết bị y tế**, không chẩn đoán lo âu, ASD, stress, meltdown hoặc bất kỳ tình trạng y khoa/tâm thần nào. `ATTENTION` chỉ nghĩa là mẫu cảm biến thỏa tiêu chí kỹ thuật hiện tại cần chú ý.

## Architecture summary

Ở chế độ thi đấu, ESP32-S3 Super Mini chạy preprocessing, kiểm tra chất lượng, baseline, feature extraction, Edge AI và logic trạng thái. Laptop chỉ nhận/lưu telemetry và hiển thị dashboard qua LAN cục bộ. Hệ thống không cần Internet hoặc cáp USB; mất mạng không được làm dừng sensing/inference trên wearable.

```text
Sensors -> ESP32 Edge pipeline -> NORMAL/ATTENTION/UNCERTAIN -> local Wi-Fi -> FastAPI -> WebSocket -> React
```

## Repository structure

- `backend/`: FastAPI, SQLite metadata, raw-file receiver và WebSocket.
- `frontend/`: React/TypeScript/Vite/Tailwind/Recharts dashboard.
- `AI/`: synthetic data, simulator, future research interfaces và firmware tại `AI/edge_firmware/`.
- `docs/`: kiến trúc, hợp đồng, protocol và phase tracking; không phải source module.

Ba source module duy nhất là `backend`, `frontend`, `AI`.

## Technology stack

Python 3.12, FastAPI, Pydantic, SQLAlchemy/SQLite, React, TypeScript, Vite, Tailwind CSS, Recharts, NumPy, matplotlib, Arduino/PlatformIO và Docker Compose.

## Development modes

- Mode A — Development: USB chỉ để flash/debug firmware.
- Mode B — R&D/Data collection: ESP32 gửi raw batches để xử lý và nghiên cứu offline trên laptop.
- Mode C — Competition/Edge: battery-powered ESP32 tự quyết định trạng thái rồi gửi compact telemetry qua LAN.

## Git workflow

Daily work uses short-lived `feature/*`, `fix/*`, `docs/*` or `chore/*` branches and pull requests into protected `dev`. Stable promotions use a pull request from `dev` into protected `main`. Direct pushes are prohibited. Collaborator PRs require the owner's approval; owner-authored PRs may merge without another approval only after all required CI checks pass and the PR is up to date and conflict-free. See [Git/GitHub Workflow](docs/GIT_WORKFLOW.md).

## Prerequisites

Docker Desktop với Compose là đường chạy nhanh nhất. Phát triển trực tiếp cần Python 3.12+, Node 22+ và PlatformIO CLI cho firmware skeleton.

## Start backend and frontend

```bash
docker compose up --build
```

- Dashboard: <http://localhost:5173>
- API health: <http://localhost:8000/api/v1/health>
- OpenAPI: <http://localhost:8000/docs>

ESP32 thật về sau phải gửi tới `http://<LAPTOP_LAN_IP>:8000`, không dùng `localhost`.

## Run synthetic mock device

Sau khi stack chạy:

```bash
docker compose --profile ai run --rm ai python -m simulator.mock_device --scenario normal --duration 30
docker compose --profile ai run --rm ai python -m simulator.mock_device --scenario attention_mock --send-raw --speed 5
```

Mọi output simulator là **SYNTHETIC TEST DATA**, không phải dữ liệu ASD hoặc bằng chứng khoa học. Xem [Synthetic Data Specification](docs/SYNTHETIC_DATA_SPEC.md).

## Tests and builds

```bash
python -m pip install -r backend/requirements.txt
python -m pytest backend/tests
python -m pip install -r AI/requirements.txt
$env:PYTHONPATH="AI"; python -m pytest AI/tests
npm --prefix frontend install
npm --prefix frontend run build
docker compose config
docker compose build
```

## PlatformIO

Firmware dùng profile build ESP32-S3 bảo thủ tạm thời; profile này không xác nhận board vật lý. Từ `AI/edge_firmware`:

```bash
pio run
pio device monitor -b 115200
```

PlatformIO không được chạy trong Docker và việc build không chứng minh sensor/hardware hoạt động.

## Documentation

Bắt đầu tại [Documentation Index](docs/README.md), [Architecture](docs/ARCHITECTURE.md), [API Contract](docs/API_CONTRACT.md), [Dataset Protocol](docs/DATASET_PROTOCOL.md) và [Project Progress](docs/PROGRESS.md).

## Current phase

Phase 01 — Project Scaffold: DONE. Phase 02 — Mock End-to-End: IN_PROGRESS vì kiểm tra trực quan live dashboard chưa được thực hiện; HTTP/raw/WebSocket đã xác minh. Không bắt đầu Phase 03 nếu chưa có chỉ dẫn rõ ràng.

## Privacy and safety

Không lưu tên học sinh, Wi-Fi credentials, dữ liệu người tham gia hoặc annotation riêng tư trong Git. Chỉ dùng ID giả danh. Không diễn giải HR, GSR hoặc chuyển động như chẩn đoán lo âu.
