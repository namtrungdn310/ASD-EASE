# 02 — Trạng thái dữ liệu trực tiếp và đóng Phase 02

| Thuộc tính | Giá trị |
|---|---|
| Nhánh | `fix/frontend-live-connection-status` |
| Chủ trì | Trung — IT |
| Phụ thuộc | Đã đáp ứng: PR #9 merge tại dev 86cd09f |
| Ước lượng | 0,5–1 ngày |
| Theo dõi | [PROGRESS.md](PROGRESS.md), dòng 02 |

## Kết quả cần đạt

Browser thể hiện đúng kết nối tới backend và độ mới của dữ liệu thiết bị. Synthetic replay được kiểm chứng trực quan để đóng phần còn thiếu của Phase 02.

## Hiện trạng / phạm vi

`useLiveTelemetry` hiện dùng WebSocket open/close cho `connected`; nó không chứng minh ESP32 còn gửi. Hook nhận tất cả payload vào một biểu đồ và chưa xử lý JSON lỗi. Trang điều khiển recording dành cho nhánh 09, không làm trong PR này.

File dự kiến: `frontend/src/hooks/useLiveTelemetry.ts`, `components/DeviceStatus.tsx`, `pages/Dashboard.tsx`, `types/telemetry.ts` khi cần tách kiểu UI, test frontend, `docs/phases/PHASE_02_MOCK_END_TO_END.md`, `docs/PROGRESS.md`, changelog.

## Học code từng file

Codex xử lý Git, comment, tài liệu, cấu hình test/CI; Trung tự viết source cốt lõi. Chỉ sang file kế tiếp sau khi kiểm tra file hiện tại. Nhánh tạo từ dev `86cd09f`; Trung đã hoàn tất `types/connection.ts`, TypeScript typecheck PASS. Chưa thay hook/giao diện hiện tại.

Thứ tự dự kiến:

1. Đã xong `frontend/src/types/connection.ts`: kiểu ConnectionStatus có đúng bốn trạng thái UI; typecheck PASS, không đổi wire contract.
2. `frontend/src/utils/validation.ts`: các hàm nhỏ isRecord, isFiniteNumber, isNumberInRange cho runtime validation; Trung viết tiếp file này.
3. Module parse/validate telemetry: dùng helper bước 2 để nhận unknown, kiểm tra các trường UI cần và JSON lỗi. TypeScript cast không thay validation.
4. Helper quản lý stream/chart theo device/session, thời điểm nhận và timestamp reset; ưu tiên logic thuần có thể test.
5. `useLiveTelemetry.ts`: áp dụng helpers, selection/freshness, reconnect và cleanup socket/timer.
6. `DeviceStatus.tsx`: hiển thị rõ bốn trạng thái kết nối/dữ liệu.
7. `Dashboard.tsx`: lựa chọn thiết bị/phiên, cảnh báo dữ liệu cũ và giữ synthetic provenance.

Tên/ranh giới helpers được chốt trước lúc hướng dẫn file đó dựa trên code đã có. Không viết trước các file kế tiếp thay Trung. Unit tests và visual test theo checklist dưới; chưa ghi PASS trước khi chạy.

## Checklist triển khai

- [ ] Tách `backendConnected`, thời điểm nhận cuối và thiết bị/phiên đang chọn; trạng thái UI không thêm bừa vào enum prediction của wire contract.
- [ ] Dùng thời gian nhận trên browser để tính độ cũ; không so uptime thiết bị với đồng hồ wall-clock của browser.
- [ ] Chọn stale timeout cấu hình được, đề xuất ban đầu 5 giây cho telemetry 1 Hz; ghi đây là giá trị dev cần đo lại.
- [ ] Hiển thị riêng: backend disconnected, waiting for data, live, stale.
- [ ] Giữ giá trị cũ có nhãn rõ hoặc hiện unavailable; không báo bình thường từ một payload đã quá cũ.
- [ ] Gắn dữ liệu theo `device_id` + `session_id`; thêm selector tối thiểu hoặc quy tắc chọn rõ ràng, không trộn nhiều thiết bị.
- [ ] Reset/tách buffer biểu đồ khi đổi thiết bị/phiên hoặc timestamp trở về đầu phiên mới.
- [ ] Bảo vệ parse/shape payload, không để một JSON lỗi làm chết handler; không ghi secret hoặc toàn payload nhạy cảm vào log.
- [ ] Reconnect không tạo nhiều timer/socket; cleanup đúng khi unmount.
- [ ] Giữ badge `SYNTHETIC DATA`; `null` hiển thị unavailable, không chuyển thành 0.
- [ ] Thêm test hành vi bằng hạ tầng frontend nhẹ phù hợp repo: fake timers/WebSocket cho timeout và reconnect; tránh chỉ test snapshot markup.
- [ ] Chạy simulator, quan sát browser thực tế và lưu bằng chứng các trường/badge/biểu đồ.
- [ ] Cập nhật Phase 02 chỉ khi quan sát thật thành công; nếu chưa có browser thì ghi `BLOCKED` với blocker công cụ cụ thể trong tracker, không khai PASS. `WAITING_HARDWARE` chỉ dùng cho thiếu board/bằng chứng phần cứng.

## Ma trận kiểm thử

| Tình huống | Kết quả mong đợi |
|---|---|
| Backend chạy, chưa có simulator/ESP32 | Backend online, thiết bị waiting; không báo live |
| Replay synthetic | Giá trị cập nhật, badge đúng, trục thời gian đúng |
| Dừng replay nhưng backend vẫn chạy | Sau timeout chuyển stale |
| Dừng backend rồi bật lại | Disconnected -> reconnect -> waiting/live theo dữ liệu mới |
| Hai device hoặc hai session xen kẽ | Không trộn điểm biểu đồ |
| Payload lỗi / trường null | Không crash; unavailable đúng |

## Cách chạy demo

Tại root, sau khi stack đã chạy:

```powershell
docker compose up -d --build backend frontend
$env:PYTHONPATH = (Resolve-Path .\ai).Path
.\.venv\Scripts\python.exe -m simulator.mock_device --scenario attention_mock --duration 30
```

Mở `http://localhost:5173`, rồi kiểm tra scenario `poor_signal` và `disconnect_reconnect`. Mất mạng giả lập hiện có chỉ khoảng 2 giây, có thể ngắn hơn stale timeout; cần riêng một lần dừng nguồn gửi đủ lâu để kiểm thử stale.

## Điều kiện merge

- [ ] Kiểm thử timeout/reconnect/không trộn thiết bị pass.
- [ ] Có ghi nhận visual test hoặc ghi rõ phần đang chờ; không đánh dấu Phase 02 DONE trước visual test.
- [ ] Frontend build và required checks pass.
- [ ] Commit gợi ý: `fix(frontend): distinguish backend connection from live device data`.

## Rollback / bàn giao

Thay đổi chỉ ở UI/hook; không đổi payload backend để chữa trạng thái browser. Nhánh 09 tái sử dụng lựa chọn thiết bị/phiên ở đây, không xây một nguồn trạng thái khác.

## Nhật ký / kết quả thực hiện

| Ngày / commit | Task | Command / bằng chứng | Kết quả / blocker |
|---|---|---|---|
| — | — | — | Chưa thực hiện |
| 2026-10-18 / branch setup | Tạo fix/frontend-live-connection-status từ dev 86cd09f sau PR #9 | Working tree sạch khi tạo nhánh; 4 IDE-generated files local giữ nguyên | Bắt đầu types/connection.ts, chưa có source/test mới |
| 2026-10-18 / local connection.ts | Trung viết union type bốn trạng thái UI | `tsc -p frontend/tsconfig.app.json --noEmit`: PASS; chưa nối hook | File đạt; tiếp utils/validation.ts. Chưa xác nhận runtime/reconnect/UI |
