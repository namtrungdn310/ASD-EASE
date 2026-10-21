# Kế hoạch IT — Chuẩn hoá dữ liệu và kết nối ESP32 với backend

Ngày lập: 2026-10-18 (Asia/Saigon). Baseline đã đọc: `dev` tại `332f249` (PR #7).

## Mục tiêu bàn giao

IT phụ trách trọn phần chuẩn hoá dữ liệu, điều khiển phiên, serializer firmware, Wi-Fi/HTTP, raw batching, backend nhận/lưu/export và dashboard. Kết quả cần đạt:

```text
Cảm biến thật -> sampling -> buffer -> serializer -> ESP32 Wi-Fi/HTTP
                                                       |
                          +----------------------------+----------------------+
                          v                                                   v
                 /api/v1/telemetry                                  /api/v1/raw-batch
                          |                                                   |
                 WebSocket -> dashboard                       file batch + SQLite metadata
                                                                              |
                                                                   kiểm tra -> export + manifest
```

Trạng thái lập kế hoạch không phải bằng chứng đã triển khai. Các tính năng dưới đây chưa được đánh dấu hoàn thành chỉ vì bộ tài liệu này đã merge. Nhánh hiện tại `docs/it-device-integration-plan` chỉ xuất bản kế hoạch.

## Hiện trạng làm cơ sở

- Firmware đã có driver MAX30102/MPU6050/GSR, EMA và báo cáo Serial text/JSON; chưa có transport HTTP hoạt động.
- JSON Serial hiện khác contract API; không gửi nguyên JSON này vào backend.
- Backend đã có telemetry, session, raw-batch và WebSocket; raw storage hiện chỉ append JSONL theo session, chưa xử lý retry/idempotency và ràng buộc session đầy đủ.
- Trang Sessions/History còn placeholder; kết nối WebSocket chưa phản ánh việc thiết bị có đang gửi dữ liệu mới hay không.
- `FINAL_VERIFICATION.md` còn marker conflict; `.env.example` bị xoá; có file cấu hình IDE sinh tự động chứa đường dẫn máy riêng.
- Baseline đã kiểm tra trước khi lập kế hoạch: 13 backend tests, 15 AI tests và firmware build pass. Các kết quả này không xác nhận đo đúng trên phần cứng.

## Phân công mới

| Người | Phạm vi |
|---|---|
| IT — Trung | Tất cả 10 nhánh trong kế hoạch này, bao gồm firmware giao thức, networking và raw buffer |
| Tự động hoá — Tân | Wiring, chân GPIO, board/flash/PSRAM, driver cảm biến, hiệu chuẩn, tốc độ lấy mẫu và nguồn/battery thực tế |
| Cùng phối hợp | Xác nhận đơn vị/nhịp mẫu đầu ra driver, log board, kiểm thử trên thiết bị thật và nghiệm thu |

Trước khi sửa `main.cpp` hoặc `board_config.h`, thống nhất với Tân để tránh hai người sửa cùng file. IT ưu tiên module riêng trong `src/communication/`, `include/communication/` và module buffer; thay đổi driver cần một PR riêng có phối hợp.

## Danh sách nhánh và phụ thuộc

| ID | Nhánh | Điều kiện bắt đầu | Kế hoạch |
|---|---|---|---|
| 01 | `chore/repository-integration-cleanup` | Kế hoạch đã merge | [01](01-repository-integration-cleanup.md) |
| 02 | `fix/frontend-live-connection-status` | 01 | [02](02-frontend-live-connection-status.md) |
| 03 | `docs/device-ingestion-contract` | 01 | [03](03-device-ingestion-contract.md) |
| 04 | `feature/backend-session-lifecycle` | 03 | [04](04-backend-session-lifecycle.md) |
| 05 | `feature/firmware-telemetry-client` | 03, 04; 02 trước nghiệm thu dashboard | [05](05-firmware-telemetry-client.md) |
| 06 | `feature/backend-raw-ingestion` | 03, 04 | [06](06-backend-raw-ingestion.md) |
| 07 | `feature/firmware-raw-batching` | 05, 06; có xác nhận sampling từ Tân | [07](07-firmware-raw-batching.md) |
| 08 | `feature/backend-recording-export` | 06; 07 trước nghiệm thu dữ liệu thật | [08](08-backend-recording-export.md) |
| 09 | `feature/frontend-recording-control` | 02, 04, 08 | [09](09-frontend-recording-control.md) |
| 10 | `chore/e2e-device-ingestion` | 01–09 và phần cứng sẵn sàng | [10](10-e2e-device-ingestion.md) |

Thứ tự làm một người: **01 -> 02 -> 03 -> 04 -> 05 -> 06 -> 07 -> 08 -> 09 -> 10**. 02 và 03, hoặc 05 và 06, có thể đổi thứ tự nếu giữ đúng phụ thuộc. Không cần tạo tất cả nhánh cùng lúc.

## Những quyết định phải chốt ở nhánh 03

Đây là phương án đề xuất cho implementation, chưa thay thế [API_CONTRACT.md](../API_CONTRACT.md):

1. Giữ wire schema telemetry/raw `1.0` nếu không đổi ý nghĩa/trường bắt buộc. Endpoint điều khiển session có contract riêng được mô tả đồng bộ. Breaking change phải có kế hoạch version và cập nhật backend, TypeScript, C++, simulator cùng nhau.
2. Backend quản lý phiên; ESP32 poll session-control, xác nhận bắt đầu, rồi dùng một mốc thời gian thu nhận chung. Khi reboot trong phiên, báo gián đoạn và kết thúc/đánh dấu phiên cũ; không reset timestamp về 0 trong cùng phiên.
3. Lifecycle đề xuất: `STARTING -> RECORDING -> STOPPING -> STOPPED`; có `ABORTED` khi không thể hoàn tất. Chỉ `RECORDING` khi thiết bị xác nhận. `STOPPING` nhận nốt raw đã thu trước mốc dừng trong khoảng chờ hữu hạn.
4. Raw batch bất biến, định danh bằng `(session_id, device_id, batch_id)`, retry giữ nguyên dữ liệu. Cùng ID/cùng payload được xác nhận lại; cùng ID/khác payload trả `409`.
5. Lưu mỗi batch thành một file, SQLite lưu index/metadata. Chỉ trả thành công khi dữ liệu đã ghi xong và index nhất quán hoặc có cơ chế phục hồi đã kiểm thử.
6. Raw IMU dùng `g` và `degrees/s`, lấy trước EMA. PPG dùng red/IR counts; GSR giữ ADC trước EMA và ghi rõ việc averaging tại driver trong manifest. Không thay raw bằng chỉ số hiển thị đã làm mượt.
7. Giữ mẫu thiếu bằng `null`, giữ thời gian thực của phiên. Không gom 1 giây snapshot Serial rồi gọi đó là raw 100 Hz.
8. Chưa có model: `model_version=none`, `probability=null`; trạng thái `CALIBRATING`/`UNCERTAIN` theo quy tắc đã viết. Không suy ra `NORMAL` chỉ từ việc driver báo `VALID`.
9. Tách metadata `DEVICE`/`SYNTHETIC` từ session đến storage/export; không suy nguồn chỉ bằng prefix ID. Dữ liệu fixture và replay phải có nhãn đúng.

## Cách dùng và theo dõi

- Mở [PROGRESS.md](PROGRESS.md) để chọn công việc tiếp theo và cập nhật trạng thái tổng.
- Mở file nhánh tương ứng, thực hiện checklist theo thứ tự, ghi command/kết quả vào bảng bằng chứng của file đó.
- Khi code hoàn thành nhưng chưa có phần cứng, dùng `WAITING_HARDWARE`; không dùng `DONE` cho nghiệm thu thiết bị thật.
- Cập nhật kế hoạch nhánh và tracker trong chính PR code; đừng chờ cuối dự án mới bổ sung.
- [../PROGRESS.md](../PROGRESS.md) vẫn là tiến độ các phase chính thức. Tracker ở đây theo dõi các PR triển khai, không thay thế điều kiện nghiệm thu phase.
- Phase 02 chỉ đóng sau kiểm chứng browser. Phase 07–08 chỉ đóng sau test thiết bị thật. Phase 00/03–06 cần bằng chứng phần cứng từ Tân. Phase 09 mới chuẩn bị hạ tầng, chưa coi là đã thu dataset.
- Kế hoạch này dừng ở nghiệm thu ingestion/recording. Chưa mở rộng sang train model, inference, benchmark khoa học hay đóng băng thi đấu.

## Quy trình Git cho từng nhánh

Chỉ thực hiện khi working tree sạch và không có merge/rebase đang dở:

```powershell
git status
git switch dev
git pull --ff-only origin dev
git switch -c chore/repository-integration-cleanup
```

Thay tên nhánh bằng đúng tên trong bảng. Hoàn thành một phần việc:

```powershell
git status
git add <cac-file-lien-quan>
git diff --staged
git commit -m "chore: clean up firmware integration artifacts"
git push -u origin chore/repository-integration-cleanup
```

Tạo PR **base `dev`**, điền test evidence và liên kết file kế hoạch. Sáu required checks giữ nguyên tên: `Workflow policy`, `Backend tests`, `AI tests`, `Frontend build`, `Firmware build`, `Repository checks`.

PR của Trung có thể dùng review bypass theo thiết lập hiện có, sau khi checks pass, branch cập nhật và không conflict. PR của Tân cần Trung approve. Không push trực tiếp `dev`/`main`.

Sau squash merge, quay về `dev`, pull và tạo nhánh kế tiếp. Không tiếp tục commit vào nhánh đã merge. Khi cần xoá local branch đã squash, kiểm tra commit và diff trước; `git branch -d` có thể từ chối vì lịch sử commit khác nhau, không tự chuyển sang `-D`.

Nếu `dev` đổi trong lúc đang làm, cập nhật feature branch theo quy trình nhóm. Không dùng `git pull origin dev` với ý định chuyển về `dev`; lệnh đó merge vào nhánh đang đứng.

## Lệnh kiểm tra dùng lại

Chạy tại root với PowerShell và `.venv` đã có dependencies:

```powershell
# Backend: chạy từ backend để import app đúng.
Push-Location backend
..\.venv\Scripts\python.exe -m pytest -q
Pop-Location

# AI/simulator.
$env:PYTHONPATH = (Resolve-Path .\ai).Path
.\.venv\Scripts\python.exe -m pytest ai/tests -q
Remove-Item Env:\PYTHONPATH

# Frontend / cấu hình / firmware.
npm --prefix frontend run build
docker compose --profile ai config --quiet
.\.venv\Scripts\pio.exe run -d ai/edge_firmware
git diff --check
```

Nếu terminal đã đặt `PYTHONPATH` riêng, lưu và phục hồi giá trị thay vì xoá. Các lệnh trên là baseline; mỗi file nhánh còn có test hành vi riêng. Không ghi PASS cho lệnh chưa chạy.

## Mốc bàn giao

| Mốc | Điều kiện |
|---|---|
| M1 — nền tảng/contract | 01–04 xong; mock E2E đã quan sát; dữ liệu/lifecycle đã thống nhất |
| M2 — telemetry thật | 05 xong; ESP32 POST LAN và dashboard nhận đúng dữ liệu DEVICE |
| M3 — recording thật | 06–08 xong; raw từ board được lưu, retry không trùng và export đọc lại đúng |
| M4 — vận hành/ nghiệm thu | 09–10 xong; bắt đầu/dừng có xác nhận, kiểm thử mất mạng và báo cáo đầy đủ |

Ước lượng để phân bổ công việc: khoảng 10–18 ngày làm việc IT nếu phần cứng sẵn sàng, chưa tính thời gian chờ phản hồi và sửa driver. Đây không phải deadline; tracker dùng kết quả test và blocker thực tế.
