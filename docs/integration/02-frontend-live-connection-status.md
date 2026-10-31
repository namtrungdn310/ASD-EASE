# 02 — Trạng thái kết nối và dữ liệu trực tiếp

| Mục | Nội dung |
|---|---|
| Nhánh | `fix/frontend-live-connection-status` |
| Phụ trách | Trung — IT |
| Phụ thuộc | PR #9 đã merge tại86cd09f |
| Ước lượng |0,5–1 ngày |
| Tiến độ |[Dòng02](PROGRESS.md) |

## Mục tiêu và tình trạng

Trình duyệt phân biệt có kết nối backend với có dữ liệu mới từ thiết bị. Giữ biểu đồ đúng thiết bị/phiên/nguồn, cảnh báo số cũ và không biến null thành0.

**Code đã merge PR #10 tại ea959ef theo tracker.** Giai đoạn02 vẫn IN_PROGRESS/BLOCKED_BROWSER vì chưa có nghiệm thu trực quan độc lập. Tests React/jsdom/HTTP/WS không thay trình duyệt thật. Điều khiển ghi dữ liệu thuộc09, không nhánh này.

## File đã làm

Trung gõ mã cốt lõi; Codex xử lý Git/comment/tài liệu/cấu hình kiểm thử:

| File | Vai trò | Kiểm tra lúc hướng dẫn |
|---|---|---|
| types/connection.ts | Bốn trạng thái giao diện, không đổi enum dự đoán |TypeScript đạt |
| utils/validation.ts | Kiểm tra object, số hữu hạn, dải giá trị |29 phép kiểm tra đạt |
| utils/parseTelemetry.ts | Kiểm tra toàn payload và parseJSON |137 phép kiểm tra đạt |
| utils/telemetryStream.ts | Tách luồng, reset, giữ60 điểm và tuổi dữ liệu |563 phép kiểm tra, gồm vòng lặp bộ đệm |
| hooks/useLiveTelemetry.ts | Nhận WS, chọn thiết bị, thời gian nhận, nối lại/dọn tài nguyên |89 phép kiểm tra trong mô phỏng Node, ban đầu chưa renderer |
| components/DeviceStatus.tsx | Nhãn/icon/trạng thái và thông báo hỗ trợ tiếp cận |74 phép kiểm tra render server |
| pages/Dashboard.tsx | Nối trạng thái/selector/biểu đồ, giữ nhãn cũ/nguồn/null |Build và tests sau đó đạt |

Các phép kiểm tra ban đầu không phải cùng một suite hay số lượng test riêng. Bộ lưu trong repo hiện có26 tests:16 helper/render và10 React DOM/hook thật trong jsdom; mạng/đồng hồ giả lập. Script riêng nhận18/18 gói qua HTTP/WS thật. Xem [bằng chứng và cách thử tay](02-VERIFICATION.md).

## Công việc

- [x] Tách kết nối backend, thời điểm nhận và thiết bị/phiên chọn; hook giữ phiên mới nhất mỗi thiết bị.
- [x] Dùng performance.now trên browser, không so uptime thiết bị với giờ máy.
- [x] Ngưỡng cũ mặc định5000 ms cho gửi1 Hz, cấu hình được, cần đo lại khi có board.
- [x] Hiển thị riêng mất backend, chờ, trực tiếp và dữ liệu cũ.
- [x] Giữ số/biểu đồ cũ có nhãn; không hiện dự đoán/chất lượng như đang mới khi không live.
- [x] Lựa chọn thiết bị và tách device/session/origin, không trộn điểm.
- [x] Reset khi đổi luồng hoặc timestamp lùi; gói trùng không làm mới tuổi.
- [x] JSON/payload lỗi không làm hỏng handler, không log dữ liệu nhạy cảm.
- [x] Kết nối lại không nhân socket/timer, dọn khi unmount; StrictMode/jsdom đã thử.
- [x] Nhãn SYNTHETIC DATA còn khi stale/mất kết nối; null khác số0 thật.
- [x] Có tests trong repo/CI, không chỉ ảnh chụp markup.
- [ ] Chạy simulator và quan sát trường/nhãn/biểu đồ bằng browser thật.
- [ ] Chỉ đóng giai đoạn02 khi có ảnh/log phù hợp; thiếu browser ghi BLOCKED, không WAITING_HARDWARE.

## Kiểm thử và demo

| Tình huống | Mong đợi |
|---|---|
| Backend chạy, chưa nguồn gửi |Chờ, không live |
| Phát lại giả lập |Giá trị/nhãn/trục thời gian đúng |
| Dừng nguồn nhưng backend còn |Sau ngưỡng chuyển cũ |
| Dừng/bật backend |Mất kết nối→chờ tới bản mới→live |
| Nhiều thiết bị/phiên |Không trộn biểu đồ |
| Gói lỗi/null |Không crash, chưa có hiển thị đúng |

```powershell
docker compose up -d --build backend frontend
$env:PYTHONPATH = (Resolve-Path .\ai).Path
.\.venv\Scripts\python.exe -m simulator.mock_device --scenario attention_mock --duration 30
```

Mở http://localhost:5173, thử poor_signal và disconnect_reconnect. Ngắt giả lập2 s ngắn hơn stale5 s, nên cần dừng gửi riêng lâu hơn để quan sát cũ.

## Nghiệm thu và bàn giao

- [x] Tests timeout/nối lại/tách thiết bị đã đạt; không đồng nghĩa trực quan đạt.
- [ ] Lưu hoặc review bằng chứng browser, không tự ghi giai đoạn02 DONE.
- [ ] Khi xét thay đổi mới, kiểm tra lại CI trên head tương ứng, không dùng kết quả cũ thay mới.

Commit mới gợi ý: `fix(frontend): phân biệt kết nối backend và dữ liệu mới`. Không đổi payload backend để sửa trạng thái UI. Nhánh09 dùng lại lựa chọn thiết bị/phiên.

## Nhật ký tóm tắt

- 2026-10-18: tạo từ dev86cd09f, giữ4 file IDE local; Trung lần lượt hoàn tất7 file.
- 2026-10-20: DeviceStatus đạt build/74 phép kiểm tra; Dashboard và16 tests đầu đạt, chưa browser.
- 2026-10-20: thêm jsdom/10 tests; tổng26/26, build/audit, backend13/AI15/header4/4 và transport18/18 đạt. Hai container/HTTP200 đạt.
- Công cụ browser trả No browser is available, discovery=[] sau xử lý theo hướng dẫn; giữ thiếu nghiệm thu, không bịa từ HTTP200.
- 2026-10-22: PR #10 merge theo quyết định chủ repo, CI head6/6 đã đạt; phần quan sát vẫn chưa có bằng chứng.

Các nhận xét về nhãn/icon/chọn thiết bị trong lần làm trước có tham khảo ui-ux-pro-max; lần Việt hoá này không sửa giao diện.
