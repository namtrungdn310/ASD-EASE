# Tiến độ IT — Device ingestion và recording

Kế hoạch: [README.md](README.md). Baseline: `332f249`. Chủ phần triển khai: Trung (IT).

Ngày cập nhật: 2026-10-18 (Asia/Saigon).

## Công việc hiện tại

- **Lập kế hoạch:** [PR #8](https://github.com/namtrungdn310/ASD-EASE/pull/8) đã merge vào dev tại `0bcd833`.
- **Implementation:** [PR #9](https://github.com/namtrungdn310/ASD-EASE/pull/9) đã merge vào dev tại `86cd09f`; sáu required checks PASS trên commit PR cuối `c764210`. Phần cleanup phần mềm đã hoàn tất, không thay thế xác nhận wiring vật lý.
- **Nhánh đang làm:** `fix/frontend-live-connection-status`, tạo từ dev `86cd09f`. connection.ts và validation.ts đã đạt typecheck, 29 runtime cases cho helpers PASS; tiếp theo `utils/parseTelemetry.ts`. Hook và giao diện chưa thay đổi.
- **Chế độ học:** Codex xử lý Git/tài liệu/cấu hình hỗ trợ; Trung viết từng source file cốt lõi, kiểm tra xong mới qua file tiếp.
- **Việc phối hợp đầu tiên:** lấy xác nhận GPIO GSR, board/flash và lịch sửa `main.cpp`/`board_config.h` từ Tân.

## Quy ước trạng thái

| Trạng thái | Ý nghĩa |
|---|---|
| `TODO` | Chưa bắt đầu; xem phụ thuộc trước khi tạo nhánh |
| `IN_PROGRESS` | Đang triển khai và cập nhật checklist |
| `WAITING_HARDWARE` | Phần mềm đã có thể kiểm thử, thiếu bằng chứng thiết bị thật |
| `BLOCKED` | Có blocker cụ thể, ghi đầu vào/người phụ trách/hành động tiếp |
| `IN_REVIEW` | Có PR, đang chờ checks hoặc review |
| `DONE` | Đã merge, đủ tiêu chí nghiệm thu của nhánh, có bằng chứng |

Một PR phần mềm có thể merge trước test board nếu ghi rõ giới hạn. Khi đó ghi trạng thái `WAITING_HARDWARE` thay vì mặc định `DONE` cho toàn nhánh. Không đồng nhất trạng thái merge với hoàn thành phase.

## Bảng theo dõi duy nhất theo nhánh

| ID | Kế hoạch / tên nhánh | Phụ thuộc | Trạng thái | Bắt đầu | Kết thúc | PR | Bằng chứng / blocker |
|---|---|---|---|---|---|---|---|
| 01 | [chore/repository-integration-cleanup](01-repository-integration-cleanup.md) | PR #8 đã merge | DONE | 2026-10-18 | 2026-10-18 | [#9 merged](https://github.com/namtrungdn310/ASD-EASE/pull/9) | Software cleanup xong, CI cuối 6/6 PASS; wiring vẫn pending ngoài nghiệm thu cleanup |
| 02 | [fix/frontend-live-connection-status](02-frontend-live-connection-status.md) | 01 đã merge | IN_PROGRESS | 2026-10-18 | — | — | connection/validation typecheck + 29 helper cases PASS; tiếp parseTelemetry.ts. Full payload/UI checks chưa thực hiện |
| 03 | [docs/device-ingestion-contract](03-device-ingestion-contract.md) | 01 | TODO | — | — | — | Cần xác nhận output driver từ Tân |
| 04 | [feature/backend-session-lifecycle](04-backend-session-lifecycle.md) | 03 | TODO | — | — | — | Chưa triển khai |
| 05 | [feature/firmware-telemetry-client](05-firmware-telemetry-client.md) | 03,04; 02 cho UI | TODO | — | — | — | Cần ESP32 + LAN để nghiệm thu |
| 06 | [feature/backend-raw-ingestion](06-backend-raw-ingestion.md) | 03,04 | TODO | — | — | — | Chưa triển khai |
| 07 | [feature/firmware-raw-batching](07-firmware-raw-batching.md) | 05,06 + sampling | TODO | — | — | — | Cần log tốc độ mẫu thực tế |
| 08 | [feature/backend-recording-export](08-backend-recording-export.md) | 06;07 cho board | TODO | — | — | — | Chưa triển khai |
| 09 | [feature/frontend-recording-control](09-frontend-recording-control.md) | 02,04,08 | TODO | — | — | — | Chưa triển khai |
| 10 | [chore/e2e-device-ingestion](10-e2e-device-ingestion.md) | 01–09 + board | TODO | — | — | — | Không đóng bằng simulator-only |

## Blocker và quyết định cần theo dõi

Các mục dưới đây là đầu vào còn thiếu/việc cần chốt, chưa có nghĩa mọi nhánh đều bị chặn.

| ID | Đầu vào / quyết định | Người phối hợp | Chặn nhánh nào | Kết quả / hành động tiếp |
|---|---|---|---|---|
| B01 | GPIO GSR cấu hình=4, comment đã sửa khớp; board/flash chưa có log trong docs | Tân | Thay giá trị GPIO, 05 nghiệm thu | Cleanup giữ nguyên giá trị; lấy wiring + log board trước khi đổi hoặc xác nhận vật lý |
| B02 | PPG rate sau FIFO averaging, mất mẫu và timestamp các stream | Tân + IT | 03 raw timing, 07 | Đo số mẫu nhận được theo thời gian, ghi config |
| B03 | Session-control handshake, stop/drain, reboot | IT | 04–09 | Chốt ở 03, triển khai ở 04/05/07 |
| B04 | Firmware JSON debug khác API v1.0 | IT | 05 | Viết serializer riêng theo contract |
| B05 | Browser/board sẵn sàng cho test | IT + Tân | 02 visual, 05/07/10 physical | Ghi thiết bị và môi trường test khi có |

## Checklist cập nhật sau mỗi buổi

- [ ] Tick các task đã làm trong đúng file kế hoạch nhánh.
- [ ] Ghi command, kết quả thật, link log/ảnh/test report và commit tương ứng.
- [ ] Cập nhật trạng thái, PR và blocker trong bảng trên.
- [ ] Ghi quyết định mới ảnh hưởng contract/phân công vào tài liệu nguồn.
- [ ] Cập nhật `docs/PROGRESS.md` khi tiến độ phase thực sự thay đổi.
- [ ] Nếu PR đã merge, chuẩn bị nhánh tiếp từ `dev` mới nhất.

## Nhật ký công việc

| Ngày | Nhánh / commit | Đã làm | Kiểm tra / bằng chứng | Bước tiếp theo |
|---|---|---|---|---|
| 2026-10-18 | docs/it-device-integration-plan | Lập 10 kế hoạch nhánh và tracker; chuyển networking/serializer/raw batching sang IT | Kiểm tra 10 tên nhánh hợp CI, 230 checklist mở, 62 liên kết local tồn tại; giữ 25 phase files và chỉ thay Markdown. Chưa triển khai tính năng | Merge kế hoạch, bắt đầu 01 |
| 2026-10-18 | chore/repository-integration-cleanup | Dọn tài liệu/env/IDE/CI; giữ nguyên core source để Trung code tay | Scanner: fail khi có marker, pass sau dọn, propagate Git error; env Settings/Compose/ignore/diff check pass, 4 local generated files giữ nguyên | Trung tự viết common_types.h, rồi lần lượt các headers theo kế hoạch 01 |
| 2026-10-18 | chore/repository-integration-cleanup / PR #9 | Trung hoàn tất 5 core headers; Codex kiểm tra và mở draft PR | Firmware build, 4 tổ hợp header, frontend build, Compose và conflict scan PASS; CI theo trạng thái GitHub | Merge PR #8 trước; cập nhật ancestry của cleanup sau squash merge, chờ CI/review rồi mới tạo nhánh 02 |
| 2026-10-18 | chore/repository-integration-cleanup / sau PR #8 | Rebase ba commit cleanup lên dev `0bcd833`, không đưa lại commit kế hoạch vào PR #9 | So sánh tree trước/sau rebase: giống nhau; bốn file IDE local giữ nguyên hash; CI 6/6 đã pass tại `7ff1851` trước rebase | Review/merge PR #9 sau khi CI commit mới pass; nhánh 02 chỉ bắt đầu sau khi #9 merge |
| 2026-10-18 | fix/frontend-live-connection-status | Xác nhận PR #9 merge tại 86cd09f, cập nhật dev và tạo nhánh 02 | Tree dev sau squash merge giống cleanup đã review; 4 local generated files giữ nguyên; CI PR cuối c764210 đã 6/6 PASS | Trung tự tạo frontend/src/types/connection.ts; kiểm tra xong file mới sang bước tiếp |

| 2026-10-18 | fix/frontend-live-connection-status / connection.ts | Trung hoàn tất kiểu ConnectionStatus cho UI | TypeScript `--noEmit` PASS; chưa thay wire contract hoặc hook | Viết utils/validation.ts từng file, rồi module parse telemetry |

| 2026-10-18 | fix/frontend-live-connection-status / validation.ts | Trung hoàn tất ba helper kiểm tra dữ liệu runtime | TypeScript PASS; 29 runtime assertions PASS | Viết parseTelemetry.ts, sau đó kiểm tra payload hợp lệ/lỗi trước khi nối hook |

## Điều kiện mở PR dev -> main

- [ ] Mốc M1–M4 trong README có bằng chứng và blocker còn lại được xử lý.
- [ ] Telemetry/raw thật qua LAN; provenance và timestamp đúng.
- [ ] Retry, reconnect, stop/drain và restart không tạo bản ghi trùng hoặc báo sai dữ liệu đầy đủ.
- [ ] Export tải lại được, gaps/loss được khai báo; raw không bị thay bằng EMA.
- [ ] Required CI pass, không conflict, docs khớp implementation.
- [ ] Chủ repo thực hiện review cuối và mở PR `dev -> main`.

Hoàn thành ingestion không tự động có nghĩa toàn dự án đã sẵn sàng thi đấu hoặc đã có model được kiểm chứng.
