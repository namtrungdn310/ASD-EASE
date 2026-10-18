# 04 — Backend quản lý vòng đời phiên và điều khiển thiết bị

| Thuộc tính | Giá trị |
|---|---|
| Nhánh | `feature/backend-session-lifecycle` |
| Chủ trì | Trung — IT |
| Phụ thuộc | 03 đã chốt contract |
| Ước lượng | 1–2 ngày |
| Theo dõi | [PROGRESS.md](PROGRESS.md), dòng 04 |

## Kết quả cần đạt

Backend biết phiên thuộc thiết bị/nguồn nào, phân biệt yêu cầu bắt đầu/dừng với ACK thực tế, và cung cấp session-control cho firmware. Có fake-device/simulator để kiểm thử trước khi firmware networking xong.

## File / phạm vi dự kiến

- `backend/app/schemas/session.py`, `api/v1/sessions.py`, `services/session_service.py`, `db/models.py`.
- Endpoint session-control/device-status mới đặt trong module API/service rõ ràng; registration trong `main.py` nếu thêm router.
- `schemas/telemetry.py`/telemetry service chỉ thay để áp dụng chính sách phiên đã chốt; không thay thuật toán dự đoán.
- `ai/simulator/mock_device.py`, backend tests/fixtures; migration SQLite có version và hướng dẫn.
- Contract, Phase 07/08, changelog, tracker khi implementation thay đổi.

## Checklist triển khai

- [ ] Đưa examples ở 03 thành fixtures executable; ghi rõ fixture, không gắn nhãn dữ liệu board thật.
- [ ] Chuẩn hoá ID với độ dài/allowlist, chặn separator/dot traversal; ràng buộc device/origin ở mọi API liên quan.
- [ ] Thêm state, origin, command generation/boot identity và metadata thời gian đúng contract. Một device không có hai phiên đang mở kể cả request đồng thời.
- [ ] Phân biệt `requested_at`, thời điểm ACK thu nhận và wall-clock metadata; timestamp stream không lấy từ thời điểm nhận HTTP.
- [ ] `/sessions/start` lặp cùng yêu cầu xử lý theo contract, xung đột khác device/origin trả lỗi rõ; không tạo hàng DB trùng.
- [ ] Implement poll session-control và device-status ACK; polling không tự tạo/update phiên bất ngờ.
- [ ] ACK STARTING -> RECORDING đúng command; command cũ/lặp không reset epoch.
- [ ] Stop chuyển STOPPING; giữ deadline drain hữu hạn, final batch ID và tiêu chí đóng phiên; bổ sung ở 06/07 phần kiểm tra đủ raw.
- [ ] Chốt trạng thái incomplete/aborted riêng với time stopped; mất ACK/timeout không báo hoàn tất thành công.
- [ ] Reboot/boot ID đổi không cho timestamp reset trong cùng recording; không nhập batch từ boot cũ vào phiên mới.
- [ ] Áp dụng ràng buộc session cho telemetry có session_id; telemetry không session phải theo policy ở 03, không tự gán vào phiên khác.
- [ ] Thêm migration SQLite để nâng DB đã tồn tại, có backup/rollback và test; `create_all()` không tự thêm cột vào bảng cũ.
- [ ] Metadata cũ thiếu origin/state được giữ là legacy/unknown hoặc migration có căn cứ; không đoán DEVICE từ ID để làm đầy dữ liệu.
- [ ] Cập nhật simulator tạo/đóng phiên, ID mỗi lần replay không vô tình tái dùng phiên đã đóng; giữ nhãn SYNTHETIC.
- [ ] Tách env/storage/test DB trong tests; không chạy test trên DB/volume người dùng.

## Ma trận kiểm thử

| Tình huống | Kết quả mong đợi |
|---|---|
| Start -> poll -> ACK -> stop -> final ACK | State chuyển đúng, command generation ổn định |
| Start đồng thời cho một device | Một phiên active, request còn lại có kết quả theo contract |
| ACK lặp, ACK command cũ, ACK sai device | Không reset thời gian hoặc cập nhật nhầm phiên |
| Unknown session / khác origin | HTTP status đúng, không ghi dữ liệu |
| Stop khi chưa ACK start; không ACK stop | Transition/timeout rõ ràng, không treo vô hạn |
| Reboot ở giữa phiên | Phiên cũ có dấu gián đoạn, clock mới có phiên mới |
| Restart backend / migrate DB cũ | Không mất metadata, trạng thái phục hồi có quy tắc |
| Simulator regression | Replay/start/stop pass với contract mới |

## Điều kiện merge / đầu ra cho nhánh 05

- [ ] API control có examples và tests, dùng được từ fake-device.
- [ ] Metadata session và migration đã kiểm tra trên DB tạm mô phỏng DB cũ.
- [ ] Firmware có endpoint, payload và error semantics đủ cụ thể để viết client.
- [ ] Bộ test backend/AI hiện có được cập nhật có chủ đích và pass; không nới validation chỉ để test cũ xanh.
- [ ] Commit gợi ý: `feat(backend): manage device session lifecycle and acknowledgements`.

## Rollback

Backup DB trước migration, không xoá DB để chữa mismatch. Nếu quay lại phiên bản cũ, dùng migration ngược đã thử hoặc phục hồi backup; giữ raw recording độc lập. Không cấp permission/firewall hoặc thay network toàn máy trong nhánh này.

## Nhật ký / kết quả thực hiện

| Ngày / commit | Task | Command / bằng chứng | Kết quả / blocker |
|---|---|---|---|
| — | — | — | Chưa thực hiện |
