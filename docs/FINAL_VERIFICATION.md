# Báo cáo kiểm chứng

## Trạng thái

- Hoàn tất chính thức: giai đoạn01, khung dự án, DONE.
- Đang mở:02, kiểm thử toàn luồng giả lập, IN_PROGRESS; còn xác nhận trực quan giá trị và nhãn SYNTHETIC DATA.
- Driver/vòng đọc có từ PR #7, sau đó cập nhật PR #11;03–06 chưa có hồ sơ nghiệm thu phần cứng.
- Cleanup01 đã gom enum/header tương thích; build không xác nhận GPIO/board thật.
- Bàn giao đặc tả nhánh03 ngày2026-10-31 ở [đây](integration/03-HANDOFF.md). Chưa có runtime MQTT hoặc tự đổi phase DONE.

## Kết quả đã ghi nhận

Các mục dưới là bằng chứng của lần kiểm tra đã lưu, không phải tất cả đều chạy lại khi dịch tài liệu. Kết quả mới phải gắn đúng commit/ngày.

| Mục | Kết quả | Bằng chứng/giới hạn |
|---|---|---|
| Cấu trúc | PASS | backend/frontend/ai/docs và25 tài liệu giai đoạn |
| Repo | PASS theo hồ sơ | namtrungdn310/ASD-EASE, mặc định dev; không xác minh quyền trực tuyến trong lượt dịch |
| Bảo vệ dev/main | PASS theo hồ sơ | PR,6 CI, nhánh cập nhật/không xung đột, xử lý trao đổi, lịch sử tuyến tính; không push trực tiếp |
| Quyền review | Theo quy trình | Tân cần Trung approve; Trung chỉ dùng ngoại lệ PR của mình sau kiểm tra |
| PR #1 | PASS theo hồ sơ | fix/* →dev,6 checks đạt; không tự suy tình trạng PR hiện tại |
| Docker Compose | PASS | docker compose config trả0 |
| Backend | PASS | 13 pytest tests |
| AI/giả lập | PASS | 15 pytest tests |
| Frontend | PASS | TypeScript/Vite build; sau đó26 tests tự động được ghi trong tracker |
| Audit production | PASS ở lần ghi nhận | npm audit --omit=dev:0 lỗ hổng |
| Docker images/runtime | PASS | Build3 image; backend khoẻ, frontend chạy |
| Health/OpenAPI | PASS | HTTP200 |
| Telemetry HTTP | PASS | Mẫu giả lập202, từ chối dữ liệu sai theo tests hiện có |
| WebSocket | PASS | Nhận SIM-E2E, nguồn SYNTHETIC |
| Raw | PASS ở mức khung | Ghi JSONL; chưa chứng minh lưu bền/chống trùng của đặc tả mới |
| Phát lại/ngắt nối | PASS | Sau tạm ngắt2 giây, tiếp tục timestamp đúng thứ tự |
| Dashboard phục vụ HTTP | PASS | HTTP200 |
| Giá trị/nhãn trực quan | NOT_VERIFIED | Chưa có trình duyệt điều khiển được; build không thay quan sát |
| Firmware build | PASS | PlatformIO6.2.0, profile ESP32-S3 tạm |
| Board/cảm biến/pin | NOT_VERIFIED | Cần kiểm chứng vật lý |

Cảnh báo matplotlib/Starlette về API cũ và bundle Recharts lớn không làm lần build/test đã ghi nhận thất bại. Không tuyên bố số liệu khoa học từ các kiểm tra này.

## Lệnh tái hiện

### Docker

```powershell
docker compose up --build
```

### Backend

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r backend\requirements.txt
Push-Location backend
..\.venv\Scripts\python -m pytest -q
Pop-Location
```

### Frontend

```powershell
npm --prefix frontend install
npm --prefix frontend run build
```

### Giả lập và AI

```powershell
.\.venv\Scripts\python -m pip install -r ai\requirements.txt
Push-Location ai
..\.venv\Scripts\python -m pytest -q
Pop-Location
docker compose --profile ai run --rm ai python -m simulator.mock_device --scenario attention_mock --duration 30 --send-raw
```

### Firmware

```powershell
.\.venv\Scripts\python.exe -m pip install platformio
.\.venv\Scripts\pio.exe run -d ai\edge_firmware
```

## Đã có và chưa có

Đã có khung kiểm tra telemetry/raw, thông tin SQLite, JSONL và phát WebSocket; dashboard; bộ sinh/lưu/phát lại giả lập và giao diện đầu vào xử lý chung; Docker; driver và Serial.

Chưa có quy trình nghiên cứu hoàn chỉnh, xử lý/chất lượng/mức nền/đặc trưng sản phẩm, mô hình đã huấn luyện/xuất, suy luận thiết bị hoặc logic trạng thái cuối. Client ESP32 mạng và bộ đệm raw có giới hạn vẫn là việc sau. HardwareProfiler có code nhưng setup hiện chưa gọi.

Cần phần cứng để xác nhận chip/board, GPIO/I2C/ADC, flash/PSRAM, USB, nguồn/pin và hoạt động độc lập. Không suy từ tên ESP32-S3 Super Mini hoặc profile PlatformIO.

## Cây bàn giao tham khảo

Cây dưới giữ ảnh chụp cấu trúc ở lần lập báo cáo, không thay git ls-files hiện tại. Không liệt kê thư viện/build/cache hoặc các file mới đã bổ sung sau đó.

```text
ASD-EDGE-AI/
    ├── .env.example
    ├── .github
    │   ├── CODEOWNERS
    │   ├── pull_request_template.md
    │   └── workflows
    │       └── ci.yml
    ├── .gitignore
    ├── ai
    │   ├── .dockerignore
    │   ├── data
    │   │   ├── interim
    │   │   │   ├── .gitkeep
    │   │   │   └── README.md
    │   │   ├── processed
    │   │   │   ├── .gitkeep
    │   │   │   └── README.md
    │   │   ├── raw
    │   │   │   ├── .gitkeep
    │   │   │   └── README.md
    │   │   └── synthetic
    │   │       ├── manifests
    │   │       │   └── .gitkeep
    │   │       ├── processed
    │   │       │   └── .gitkeep
    │   │       └── raw
    │   │           └── .gitkeep
    │   ├── Dockerfile
    │   ├── edge_firmware
    │   │   ├── .gitignore
    │   │   ├── include
    │   │   │   ├── board_config.h
    │   │   │   ├── GSRSensor.h
    │   │   │   ├── HardwareProfiler.h
    │   │   │   ├── interfaces.h
    │   │   │   ├── MAX30102Sensor.h
    │   │   │   ├── model_config.h
    │   │   │   ├── model_generated.h
    │   │   │   ├── MPU6050Sensor.h
    │   │   │   ├── network_config.example.h
    │   │   │   ├── pins.h
    │   │   │   └── sensor_config.h
    │   │   ├── platformio.ini
    │   │   ├── src
    │   │   │   ├── baseline
    │   │   │   │   └── .gitkeep
    │   │   │   ├── communication
    │   │   │   │   └── .gitkeep
    │   │   │   ├── features
    │   │   │   │   └── .gitkeep
    │   │   │   ├── hardware
    │   │   │   │   └── HardwareProfiler.cpp
    │   │   │   ├── inference
    │   │   │   │   └── .gitkeep
    │   │   │   ├── main.cpp
    │   │   │   ├── processing
    │   │   │   │   └── .gitkeep
    │   │   │   ├── quality
    │   │   │   │   └── .gitkeep
    │   │   │   ├── sensors
    │   │   │   │   ├── GSRSensor.cpp
    │   │   │   │   ├── MAX30102Sensor.cpp
    │   │   │   │   └── MPU6050Sensor.cpp
    │   │   │   └── state
    │   │   │       └── .gitkeep
    │   │   └── test
    │   │       └── .gitkeep
    │   ├── models
    │   │   ├── experiments
    │   │   │   └── .gitkeep
    │   │   └── production
    │   │       └── .gitkeep
    │   ├── notebooks
    │   │   └── README.md
    │   ├── requirements.txt
    │   ├── simulator
    │   │   ├── __init__.py
    │   │   └── mock_device.py
    │   ├── src
    │   │   ├── baseline
    │   │   │   └── __init__.py
    │   │   ├── evaluation
    │   │   │   └── __init__.py
    │   │   ├── export
    │   │   │   └── __init__.py
    │   │   ├── feature_extraction
    │   │   │   └── __init__.py
    │   │   ├── preprocessing
    │   │   │   ├── __init__.py
    │   │   │   └── interface.py
    │   │   ├── signal_quality
    │   │   │   └── __init__.py
    │   │   └── training
    │   │       └── __init__.py
    │   ├── synthetic
    │   │   ├── __init__.py
    │   │   ├── artifacts.py
    │   │   ├── config.py
    │   │   ├── generator.py
    │   │   ├── labeling.py
    │   │   ├── motion.py
    │   │   ├── physiology.py
    │   │   ├── scenarios.py
    │   │   └── validation.py
    │   └── tests
    │       ├── test_mock_device.py
    │       ├── test_synthetic_contract.py
    │       ├── test_synthetic_generator.py
    │       └── test_synthetic_reproducibility.py
    ├── backend
    │   ├── .dockerignore
    │   ├── app
    │   │   ├── __init__.py
    │   │   ├── api
    │   │   │   ├── __init__.py
    │   │   │   └── v1
    │   │   │       ├── __init__.py
    │   │   │       ├── annotations.py
    │   │   │       ├── devices.py
    │   │   │       ├── events.py
    │   │   │       ├── health.py
    │   │   │       ├── raw_data.py
    │   │   │       ├── sessions.py
    │   │   │       ├── telemetry.py
    │   │   │       └── websocket.py
    │   │   ├── core
    │   │   │   ├── config.py
    │   │   │   └── enums.py
    │   │   ├── db
    │   │   │   ├── database.py
    │   │   │   └── models.py
    │   │   ├── main.py
    │   │   ├── schemas
    │   │   │   ├── annotation.py
    │   │   │   ├── event.py
    │   │   │   ├── raw_batch.py
    │   │   │   ├── session.py
    │   │   │   └── telemetry.py
    │   │   └── services
    │   │       ├── raw_storage.py
    │   │       ├── session_service.py
    │   │       ├── telemetry_service.py
    │   │       └── websocket_manager.py
    │   ├── Dockerfile
    │   ├── requirements.txt
    │   ├── storage
    │   │   ├── .gitkeep
    │   │   └── raw
    │   │       └── .gitkeep
    │   └── tests
    │       ├── conftest.py
    │       ├── test_health.py
    │       ├── test_raw_batch.py
    │       └── test_telemetry.py
    ├── compose.yaml
    ├── docs
    │   ├── API_CONTRACT.md
    │   ├── ARCHITECTURE.md
    │   ├── CHANGELOG.md
    │   ├── COMPETITION_MODE_TEST.md
    │   ├── DATASET_PROTOCOL.md
    │   ├── DECISIONS.md
    │   ├── DEVELOPMENT_WORKFLOW.md
    │   ├── FINAL_VERIFICATION.md
    │   ├── GIT_WORKFLOW.md
    │   ├── HARDWARE_PROFILE.md
    │   ├── phases
    │   │   ├── PHASE_00_HARDWARE_VERIFICATION.md
    │   │   ├── PHASE_01_PROJECT_SCAFFOLD.md
    │   │   ├── PHASE_02_MOCK_END_TO_END.md
    │   │   ├── PHASE_03_MAX30102.md
    │   │   ├── PHASE_04_MPU6050.md
    │   │   ├── PHASE_05_GSR.md
    │   │   ├── PHASE_06_SENSOR_INTEGRATION.md
    │   │   ├── PHASE_07_WIFI_BACKEND.md
    │   │   ├── PHASE_08_DATA_LOGGER.md
    │   │   ├── PHASE_09_DATASET_COLLECTION.md
    │   │   ├── PHASE_10_SIGNAL_PROCESSING.md
    │   │   ├── PHASE_11_BASELINE_FEATURES.md
    │   │   ├── PHASE_12_RULE_BASELINES.md
    │   │   ├── PHASE_13_ML_EXPERIMENTS.md
    │   │   ├── PHASE_14_MODEL_SELECTION.md
    │   │   ├── PHASE_15_MODEL_EXPORT.md
    │   │   ├── PHASE_16_EDGE_INFERENCE.md
    │   │   ├── PHASE_17_PARITY_TEST.md
    │   │   ├── PHASE_18_TEMPORAL_LOGIC.md
    │   │   ├── PHASE_19_BATTERY_STANDALONE.md
    │   │   ├── PHASE_20_COMPETITION_WIRELESS.md
    │   │   ├── PHASE_21_NETWORK_RESILIENCE.md
    │   │   ├── PHASE_22_DEMO_SCENARIOS.md
    │   │   ├── PHASE_23_BENCHMARK.md
    │   │   └── PHASE_24_COMPETITION_FREEZE.md
    │   ├── PROGRESS.md
    │   ├── README.md
    │   ├── RESPONSIBILITIES.md
    │   └── SYNTHETIC_DATA_SPEC.md
    ├── frontend
    │   ├── .dockerignore
    │   ├── Dockerfile
    │   ├── index.html
    │   ├── package-lock.json
    │   ├── package.json
    │   ├── src
    │   │   ├── api
    │   │   │   └── index.ts
    │   │   ├── App.tsx
    │   │   ├── components
    │   │   │   ├── DeviceStatus.tsx
    │   │   │   ├── GSRChart.tsx
    │   │   │   ├── HeartRateChart.tsx
    │   │   │   ├── MetricChart.tsx
    │   │   │   ├── MovementChart.tsx
    │   │   │   ├── ProbabilityChart.tsx
    │   │   │   ├── SignalQuality.tsx
    │   │   │   └── StateCard.tsx
    │   │   ├── hooks
    │   │   │   └── useLiveTelemetry.ts
    │   │   ├── main.tsx
    │   │   ├── pages
    │   │   │   ├── Dashboard.tsx
    │   │   │   ├── History.tsx
    │   │   │   └── Sessions.tsx
    │   │   ├── styles.css
    │   │   ├── types
    │   │   │   └── telemetry.ts
    │   │   └── utils
    │   │       └── README.md
    │   ├── tsconfig.app.json
    │   ├── tsconfig.json
    │   ├── tsconfig.node.json
    │   └── vite.config.ts
    └── README.md
```

Xem [tiến độ hiện tại](PROGRESS.md), [tracker nhánh](integration/PROGRESS.md) và [bằng chứng nhánh02](integration/02-VERIFICATION.md).
