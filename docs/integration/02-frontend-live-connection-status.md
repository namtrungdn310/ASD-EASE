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

Baseline trước nhánh này: `useLiveTelemetry` dùng WebSocket open/close cho `connected`, nhận tất cả payload vào một biểu đồ và chưa xử lý JSON lỗi. Hook hiện đã nối parser/stream helpers, tách dữ liệu theo device và freshness; component hiển thị bốn trạng thái, selector và cảnh báo dữ liệu cũ vẫn chưa triển khai. Trang điều khiển recording dành cho nhánh 09, không làm trong PR này.

File dự kiến: `frontend/src/hooks/useLiveTelemetry.ts`, `components/DeviceStatus.tsx`, `pages/Dashboard.tsx`, `types/telemetry.ts` khi cần tách kiểu UI, test frontend, `docs/phases/PHASE_02_MOCK_END_TO_END.md`, `docs/PROGRESS.md`, changelog.

## Học code từng file

Codex xử lý Git, comment, tài liệu, cấu hình test/CI; Trung tự viết source cốt lõi. Chỉ sang file kế tiếp sau khi kiểm tra file hiện tại. Nhánh tạo từ dev `86cd09f`; connection.ts, validation.ts, parseTelemetry.ts, telemetryStream.ts và useLiveTelemetry.ts đã đạt TypeScript typecheck. Validation helpers có 29 runtime cases PASS; telemetry parser/guard có 137 assertions PASS; stream helpers có 563 runtime assertions PASS. Hook đã nối helpers, qua 89 assertions trong harness mô phỏng state/effect, WebSocket và timer; chưa phải test React renderer hoặc browser. Frontend production build PASS; component UI chưa sửa.

Thứ tự dự kiến:

1. Đã xong `frontend/src/types/connection.ts`: kiểu ConnectionStatus có đúng bốn trạng thái UI; typecheck PASS, không đổi wire contract.
2. Đã xong `frontend/src/utils/validation.ts`: isRecord, isFiniteNumber, isNumberInRange; TypeScript và 29 runtime cases PASS (null/array/chuỗi/NaN/Infinity/giá trị biên).
3. Đã xong `frontend/src/utils/parseTelemetry.ts`: isTelemetry và parseTelemetry dùng helpers, trả payload hợp lệ hoặc null. Typecheck và 137 assertions PASS (payload hợp lệ, null, biên, thiếu field, sai nested object, enum, số không hữu hạn, JSON lỗi và không mutate input).
4. Đã xong `frontend/src/utils/telemetryStream.ts`: TelemetryStream, updateTelemetryStream và getConnectionStatus; tách stream theo device/session/origin, reset chart khi đổi stream/timestamp lùi, giữ tối đa 60 điểm, duplicate timestamp không refresh tuổi dữ liệu. TypeScript và 563 runtime assertions PASS: mapping/null/zero, không mutate input, duplicate giữ object và thời điểm nhận, reset từng khóa/timestamp, rolling buffer và bốn trạng thái với default/custom timeout.
5. Đã xong `useLiveTelemetry.ts`: áp dụng parser/stream helpers; Map theo device, lựa chọn thiết bị ổn định, chỉ xem dữ liệu nhận trong kết nối hiện tại là fresh; dùng performance.now cho freshness, interval cập nhật status, reconnect và cleanup socket/timer. Typecheck/build PASS, 89 assertions trong harness mô phỏng PASS; cần test React/browser thực tế. `connected` tạm giữ để tương thích Dashboard nhưng giờ chỉ true khi live; dữ liệu cũ vẫn giữ, chưa có nhãn stale trên UI.
6. `DeviceStatus.tsx`: bước tiếp theo, hiển thị rõ bốn trạng thái kết nối/dữ liệu. Dashboard sẽ nối prop mới ở bước sau; không xem UI hoàn tất chỉ vì hook đã pass.
7. `Dashboard.tsx`: lựa chọn thiết bị/phiên, cảnh báo dữ liệu cũ và giữ synthetic provenance.

Tên/ranh giới helpers được chốt trước lúc hướng dẫn file đó dựa trên code đã có. Không viết trước các file kế tiếp thay Trung. Unit tests và visual test theo checklist dưới; chưa ghi PASS trước khi chạy.

## Checklist triển khai

- [x] Tách `backendConnected`, thời điểm nhận cuối và thiết bị/phiên đang chọn; trạng thái UI không thêm bừa vào enum prediction của wire contract. Hook giữ phiên mới nhất cho từng thiết bị; selector UI chưa có.
- [x] Dùng thời gian nhận trên browser để tính độ cũ; không so uptime thiết bị với đồng hồ wall-clock của browser. Hook dùng performance.now cho cả receive/now.
- [x] Chọn stale timeout cấu hình được, đề xuất ban đầu 5 giây cho telemetry 1 Hz; ghi đây là giá trị dev cần đo lại. Tham số useLiveTelemetry(staleTimeoutMs) mặc định 5000 ms; cần đo lại khi có thiết bị thật.
- [ ] Hiển thị riêng: backend disconnected, waiting for data, live, stale.
- [ ] Giữ giá trị cũ có nhãn rõ hoặc hiện unavailable; không báo bình thường từ một payload đã quá cũ.
- [ ] Gắn dữ liệu theo `device_id` + `session_id`; thêm selector tối thiểu hoặc quy tắc chọn rõ ràng, không trộn nhiều thiết bị.
- [x] Reset/tách buffer biểu đồ khi đổi thiết bị/phiên hoặc timestamp trở về đầu phiên mới. Helper và hook harness PASS; UI selection chưa nghiệm thu.
- [x] Bảo vệ parse/shape payload, không để một JSON lỗi làm chết handler; không ghi secret hoặc toàn payload nhạy cảm vào log.
- [x] Reconnect không tạo nhiều timer/socket; cleanup đúng khi unmount. Harness mô phỏng PASS; chưa thay thế kiểm thử React renderer/browser thực tế.
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
| 2026-10-18 / local validation.ts | Trung viết ba runtime guard helpers | TypeScript --noEmit PASS; Node --experimental-strip-types chạy 29 assertions về object/null/array, số hữu hạn, invalid types và range boundaries: PASS | File đạt; tiếp parseTelemetry.ts. Chưa validate toàn payload hoặc nối hook |
| 2026-10-18 / local parseTelemetry.ts | Trung viết telemetry guard và JSON parser | TypeScript --noEmit PASS; 137 runtime assertions qua Node stripTypeScriptTypes PASS, bao gồm full payload/nested fields/nulls/ranges/JSON lỗi | File đạt; tiếp telemetryStream.ts, chưa nối hook/UI |
| 2026-10-18 / local telemetryStream.ts | Trung viết stream/chart reducer và connection status helper | TypeScript --noEmit PASS; 563 runtime assertions qua Node stripTypeScriptTypes PASS; git diff --check PASS | File đạt; tiếp useLiveTelemetry.ts. Chưa kiểm thử WebSocket/reconnect hoặc UI; 563 là số assertions, gồm vòng lặp kiểm tra rolling buffer |
| 2026-10-18 / local useLiveTelemetry.ts | Trung nối helpers vào WebSocket hook, per-device selection/freshness/reconnect/cleanup | TypeScript --noEmit và npm run build PASS; 89 assertions qua source TS thực trong harness Node mô phỏng hooks/WebSocket/timer PASS: invalid/binary/duplicate/null, buffer 60, device/session/origin, stale/custom timeout, reconnect waiting, stale callbacks, constructor/error retry, effect setup-cleanup-setup và unmount | Chưa phải React renderer/browser test; harness chạy inline, chưa có test suite tái chạy trong repo/CI. Build còn cảnh báo bundle >500 kB (không fail). Tiếp DeviceStatus; selector/cảnh báo stale/visual nghiệm thu chưa thực hiện |
