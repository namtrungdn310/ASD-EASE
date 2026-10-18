# Responsibilities

## Person A — IT student

Repository/Git, Docker, FastAPI, SQLite, REST/WebSocket, React dashboard, simulator, data and preprocessing software, feature engineering, AI experiments/evaluation/export, Python/C++ parity framework and automated tests.

For the device-ingestion milestone, IT also owns data/units/timestamp normalization, session control, firmware serializers, Wi-Fi/HTTP transport, raw buffering/batching, retry behavior and backend recording/export. Implementation is split into ten branches in the [IT device-integration plan](integration/README.md), with a [branch progress tracker](integration/PROGRESS.md).

## Person B — Automation engineering student

Physical ESP32-S3 Super Mini and pin verification, MAX30102, MPU6050, GSR/ADC, wiring, power/battery, sensor drivers, acquisition sampling/timing measurements and physical wearable integration. Automation supplies measured driver output units/rates, calibration and board evidence to IT. Firmware networking and wire-format/batching implementation for this milestone belong to IT.

## Shared

API contract, experiment design, dataset collection, feature validation, model selection, Edge deployment, parity, end-to-end/competition testing and demo. Neither person may silently change the contract or claim clinical meaning from engineering states.

Coordinate edits to firmware `main.cpp`, `board_config.h` and sensor interfaces before either contributor changes them. A software build or merged implementation does not replace physical acceptance evidence.

