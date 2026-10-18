# 09 — Giao diện điều khiển và xem phiên thu

| Thuộc tính | Giá trị |
|---|---|
| Nhánh | `feature/frontend-recording-control` |
| Chủ trì | Trung — IT |
| Phụ thuộc | 02, 04, 08 |
| Ước lượng | 1–2 ngày |
| Theo dõi | [PROGRESS.md](PROGRESS.md), dòng 09 |

## Kết quả cần đạt

Người dùng chọn đúng thiết bị, bắt đầu/dừng phiên có xác nhận, theo dõi dữ liệu nhận và tải export. Sessions hiện là placeholder, App chỉ render Dashboard; nhánh này bổ sung đường điều hướng tối thiểu, không làm lại toàn bộ giao diện.

## File dự kiến

`frontend/src/pages/Sessions.tsx`, `App.tsx`, `api/index.ts`, API/session types mới, hook polling session/recording, shared selected device/session state, test UI. `History.tsx` chỉ triển khai nếu cần cho recording list đã chốt; không mở rộng thành phân tích event khoa học.

## Checklist màn hình và state

- [ ] Thêm navigation Dashboard / Sessions; giữ bảng màu và components đang dùng.
- [ ] Dùng cùng device/session selection với 02; không có hai selector đưa dashboard và nút Stop tới hai thiết bị khác nhau.
- [ ] List thiết bị có last-seen và data origin; backend connected khác device live.
- [ ] Start form có device và ID phiên hợp lệ; participant ID giả danh tuỳ nhu cầu đã chốt.
- [ ] Nút Start gửi request một lần, có pending/disabled và xử lý 409/422 theo backend.
- [ ] Khi backend nhận yêu cầu, hiển thị STARTING/chờ ACK; chỉ hiện RECORDING sau ACK thiết bị, không đoán từ HTTP 200.
- [ ] Stop hiển thị STOPPING/draining, số batch đang chờ khi có dữ liệu; STOPPED không mặc định recording complete.
- [ ] Mất thiết bị hoặc timeout -> hiển thị incomplete/aborted reason đúng; có thao tác tiếp theo theo API, không bấm Start lặp tạo nhiều phiên.
- [ ] Hiển thị elapsed theo acquisition metadata, batch/sample counts và missing/gap indicator; không dùng thời gian browser như clock nguồn đo.
- [ ] Danh sách phiên có filter/pagination, nguồn DEVICE/SYNTHETIC, trạng thái lifecycle và recording completeness.
- [ ] Detail xem summary/manifest và tải export; không load toàn raw array để dựng list.
- [ ] Poll/refetch backend theo chu kỳ cấu hình hoặc sự kiện được hỗ trợ; tránh busy loop, cleanup khi đổi trang.
- [ ] Refresh browser khôi phục trạng thái từ backend; localStorage không là nguồn thật cho session active.
- [ ] `VITE_API_BASE_URL`/WS URL phù hợp máy mở dashboard. Nếu truy cập bằng máy khác trong LAN, localhost mặc định không trỏ về laptop server; document cấu hình build/CORS cần thiết.
- [ ] Có loading/empty/error, keyboard labels và trạng thái nút đủ rõ; không hiển thị nguyên stack trace cho người dùng.
- [ ] Badge synthetic vẫn rõ; không thêm metric model/SpO2 chưa có API version tương ứng.

## Ma trận kiểm thử

| Tình huống | Kết quả mong đợi |
|---|---|
| Không thiết bị / thiết bị chưa gửi | Empty/waiting rõ, không báo recording giả |
| Start thành công nhưng ACK chậm | STARTING, không double submit |
| Start conflict / validation error | Thông báo phù hợp, giữ form sửa được |
| Stop có backlog / timeout | STOPPING -> complete hoặc incomplete theo backend |
| Refresh/chuyển trang/đổi device | Selected session nhất quán, polling/socket không rò rỉ |
| Recording synthetic/real | Badge/filter/export nguồn đúng |
| Export tải lỗi / session lớn | UI xử lý lỗi và không giữ raw lớn trong memory |
| Mobile browser / keyboard | Các thao tác chính vẫn dùng được |

Dùng mock API cho test UI có kiểm soát, sau đó simulator và board cho integration. Lưu bằng chứng browser thực tế, không đánh PASS chỉ từ `npm run build`.

## Điều kiện merge

- [ ] TypeScript/build + tests lifecycle UI pass; visual test có ghi thiết bị/browser.
- [ ] Không có optimistic state báo đã thu trước ACK hoặc báo complete khi còn gap.
- [ ] Required checks pass; contract/README sử dụng được cập nhật.
- [ ] Commit gợi ý: `feat(frontend): control and inspect recording sessions`.

## Rollback

Nếu UI gặp vấn đề, API vẫn có thể thao tác bằng công cụ dev theo contract; không tự thay state DB để chữa giao diện. Trở về dashboard không stop một session ngoài ý muốn.

## Nhật ký / kết quả thực hiện

| Ngày / commit | Task | Command / bằng chứng | Kết quả / blocker |
|---|---|---|---|
| — | — | — | Chưa thực hiện |
