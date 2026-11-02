# Kế hoạch chuẩn hoá và kết nối ESP32

Lập2026-10-18, cập nhật2026-10-31, Asia/Saigon. Ban đầu trên dev332f249; nhánh03 từ d80cc0e sau PR #11.

## Mục tiêu

IT làm chuẩn hoá dữ liệu, phiên, đóng gói firmware, Wi-Fi/MQTT, raw HTTP, backend nhận/lưu/xuất và dashboard. Tân phụ trách phần cứng/driver/đo thực tế. Theo [kiến trúc](MQTT_ARCHITECTURE.md):

```text
ESP32 -- MQTT telemetry/ACK --> broker --> backend --> WS --> dashboard
ESP32 <-- MQTT lệnh/trạng thái -- broker <-- backend <-- HTTP từ UI
ESP32 -- HTTPraw -------------------------> file + chỉ mục SQLite
```

01 và code02 đã merge;03 merge [PR #12](https://github.com/namtrungdn310/ASD-EASE/pull/12) tại752bd5d. 04 đã triển khai backend MQTT/phiên, thử broker thật và push [PR #13](https://github.com/namtrungdn310/ASD-EASE/pull/13); hoàn tất khi PR merge vào dev sau đủ CI. Xem [bàn giao04](04-HANDOFF.md), [cách chạy](04-SETUP.md) và [tracker](PROGRESS.md). Firmware MQTT05 và raw lưu bền06/07 chưa triển khai.

## Điểm xuất phát

Có driver/EMA/Serial nhưng JSON khác API; mạng ESP32 chưa triển khai. Backend có HTTPtelemetry/raw/WS nhưng raw mới appendJSONL, chưa đủ chống trùng/phiên. Sessions/History còn giữ chỗ; frontend02 có trạng thái còn mới nhưng thiếu nghiệm thu browser.

Cleanup01 xử lý tài liệu/env; PR #11 có thêm lại file IDE và cập nhật driver. Không xoá file nhóm trong nhánh đặc tả. Mapping/rate phải đối chiếu lại; số đo phần cứng còn thiếu.

## Phân công

| Người | Phạm vi |
|---|---|
| Trung — IT |10 nhánh, gồm firmware mạng/đóng gói/bộ đệm và backend/frontend |
| Tân — Tự động hoá |Wiring, GPIO, board/flash/PSRAM, nguồn/pin, driver, hiệu chuẩn/rate |
| Cùng phối hợp |Đơn vị/log đo, thử thiết bị và nghiệm thu |

Thống nhất trước khi sửa chung main.cpp/board_config.h. IT ưu tiên mô-đun riêng; thay thuật toán driver cần phối hợp. Nhánh05 chưa tự chuyển người phụ trách chỉ từ trao đổi đề xuất.

## Nhánh và phụ thuộc

| ID | Nhánh | Điều kiện | Kế hoạch |
|---|---|---|---|
| 01 | `chore/repository-integration-cleanup` | PR #8 | [01](01-repository-integration-cleanup.md) |
| 02 | `fix/frontend-live-connection-status` | 01 | [02](02-frontend-live-connection-status.md) |
| 03 | `docs/device-ingestion-contract` | 01 | [03](03-device-ingestion-contract.md) |
| 04 | `feature/backend-session-lifecycle` | 03 | [04](04-backend-session-lifecycle.md) |
| 05 | `feature/firmware-telemetry-client` | 03/04;02 cho UI | [05](05-firmware-telemetry-client.md) |
| 06 | `feature/backend-raw-ingestion` | 03/04 | [06](06-backend-raw-ingestion.md) |
| 07 | `feature/firmware-raw-batching` | 05/06 và số đo mẫu | [07](07-firmware-raw-batching.md) |
| 08 | `feature/backend-recording-export` | 06;07 trước nghiệm thu thật | [08](08-backend-recording-export.md) |
| 09 | `feature/frontend-recording-control` | 02/04/08 | [09](09-frontend-recording-control.md) |
| 10 | `chore/e2e-device-ingestion` | 01–09 và board | [10](10-e2e-device-ingestion.md) |

Thứ tự tiếp:03→04→05→06→07→08→09→10. Sau04 có thể đổi thứ tự05/06;08 bắt đầu sau06 bằng mẫu nhưng cần07 trước nghiệm thu thật. Không tạo tất cả nhánh cùng lúc.

Broker/backend MQTT ở04 để05 có bên nhận.04 nhiều việc hơn nên tách commit theo phần; muốn thêm nhánh phải báo Trung trước.

## Quyết định đã ghi ở03

1. Telemetry/raw1.0 giữ cấu trúc, control phiên bản riêng; thay đổi mất tương thích có kế hoạch.
2. Backend giữ phiên; UIHTTPStartStop→MQTTcommand→ACK, đồng bộ sau reconnect; không firmware pollHTTP song song.
3. STARTING→RECORDING→STOPPING→STOPPED, ABORTED khi không khép được; ACK thực thi khác PUBACK.
4. Raw bất biến theo phiên/thiết bị/batch; cùng ID/nội dung xác nhận lại, khác trả409.
5. Mỗi batch một file/chỉ mục; xác nhận sau lưu bền/nhất quán, có đối chiếu sau lỗi.
6. IMUraw g/degrees-s trướcEMA, PPGred/IR, GSR ADCtrung bình8 trướcEMA; giữ rõ đơn vị/phép xử lý.
7. Null giữ mẫu thiếu/thời gian; không biến snapshot1Hz thành raw100Hz.
8. Chưa mô hình: modelnone/probabilitynull, CALIBRATING/UNCERTAIN, không tựNORMAL từVALID.
9. Nguồn DEVICE/SYNTHETIC được ràng buộc, không chỉ tin prefix.
10. Topic/QoS/retain, danh tính/quyền, boot/generation, giới hạn và timeout theo [đặc tả](../API_CONTRACT.md).
11. Tổng kết MQTT có thể trước/sau rawHTTP; đủ dữ liệu phải đối chiếu ID/count, không dựa thứ tự hai kênh.

## Theo dõi và học

Cập nhật đúng kế hoạch/tracker trong PR. Chờ board dùng WAITING_HARDWARE; build/merge không thay nghiệm thu. [Tiến độ giai đoạn](../PROGRESS.md) khác bảng nhánh.

Riêng03 Codex đã hoàn thiện theo yêu cầu2026-10-31. Các nhánh code sau Trung vẫn có thể gõ từng file, kiểm tra rồi mới qua tiếp. Giai đoạn02 cần browser;07/08 cần thiết bị thật;09 thu dataset không hoàn tất chỉ vì có hạ tầng ghi.

Phạm vi này dừng ở nhận/ghi dữ liệu; train/benchmark/thi đấu lập kế hoạch sau.

## Git cho từng nhánh

Chỉ khi cây làm việc sạch, không merge/rebase dở:

```powershell
git status
git switch dev
git pull --ff-only origin dev
git switch -c chore/repository-integration-cleanup
```

Thay tên nhánh bằng bảng. Hoàn thành phần việc:

```powershell
git status
git add <cac-file-lien-quan>
git diff --staged
git commit -m "chore: dọn cấu hình tích hợp"
git push -u origin chore/repository-integration-cleanup
```

PRbase dev, ghi kiểm thử và link kế hoạch. Giữ tên6 checks: Workflow policy, Backend tests, AI tests, Frontend build, Firmware build, Repository checks.

Tân cần Trung approve; PRTrung dùng ngoại lệ theo quyền sau đủ CI/cập nhật/không conflict. Không push trực tiếp. Sau squash quay dev/pull/tạo nhánh mới; -d từ chối thì kiểm tra trước, không tự -D.

git pull origin dev không chuyển nhánh: nó merge vào nhánh đang đứng.

## Lệnh kiểm tra dùng lại

PowerShell từ root, .venv đã có dependencies:

```powershell
Push-Location backend
..\.venv\Scripts\python.exe -m pytest -q
Pop-Location
$env:PYTHONPATH = (Resolve-Path .\ai).Path
.\.venv\Scripts\python.exe -m pytest ai/tests -q
Remove-Item Env:\PYTHONPATH
npm --prefix frontend run build
docker compose --profile ai config --quiet
.\.venv\Scripts\pio.exe run -d ai/edge_firmware
git diff --check
```

Nếu PYTHONPATH đã có giá trị riêng, lưu/khôi phục thay vì xoá. Mỗi nhánh còn tests hành vi riêng; chưa chạy không ghi PASS.

## Mốc bàn giao

| Mốc | Điều kiện |
|---|---|
| M1 |01–04, broker/thiết bị giả→phiên/WS; contract thống nhất, browser02 có bằng chứng |
| M2 |05, telemetry/ACK thật qua LAN, dashboard đúng DEVICE và còn mới |
| M3 |06–08, raw thật lưu chống trùng, xuất/đọc lại đúng |
| M4 |09–10, Start/Stop có xác nhận, thử lỗi và báo cáo đủ |

Ước lượng03–10 khoảng13–23 ngày IT nếu board sẵn sàng, chưa tính học/chờ/sửa driver; không phải deadline. Cập nhật theo kết quả thật sau thử tương thích04/05.
