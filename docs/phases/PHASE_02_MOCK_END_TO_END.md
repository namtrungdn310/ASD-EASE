# Giai đoạn 02 — Kiểm thử toàn luồng bằng dữ liệu giả lập

## Trạng thái

IN_PROGRESS

## Người phụ trách

Trung — IT

## Mục tiêu

Kiểm tra dữ liệu giả lập đi qua HTTP, FastAPI, WebSocket và dashboard React.

## Lý do

Phát hiện lỗi tích hợp trước khi có cảm biến thật.

## Phụ thuộc

Giai đoạn 01

## Đầu vào

Backend/frontend đang chạy bằng Docker hoặc trực tiếp; một phiên dữ liệu giả lập.

## Công việc

- [x] Sinh/lưu phiên giả lập đa cảm biến có thể tái lập.
- [x] Phát lại telemetry và raw tới FastAPI.
- [ ] Xác nhận trực quan giá trị dashboard và nhãn SYNTHETIC DATA; WebSocket tự động đã kiểm tra.

## File dự kiến thay đổi

ai/synthetic/...; ai/simulator/mock_device.py; backend/...; frontend/...; docs/SYNTHETIC_DATA_SPEC.md

## Lưu ý triển khai

Dùng chung đặc tả, ghi nguồn SYNTHETIC; tách việc ngắt đường truyền khỏi việc thu mẫu.

## Kiểm thử

Chạy kiểm thử đặc tả, tái lập dữ liệu và WebSocket; phát lại từng kịch bản, quan sát giá trị và nhãn trên dashboard.

## Điều kiện nghiệm thu

- [x] Kịch bản giả lập đáp ứng đặc tả raw và kiểm thử tái lập.
- [x] Telemetry được nhận và phát qua WebSocket.
- [ ] Dashboard hiển thị đúng trường và nhãn nguồn giả lập trên trình duyệt thật.

## Đầu ra

Phần triển khai có thể review, kết quả kiểm thử và tiến độ đã cập nhật. Không tự chuyển sang giai đoạn sau khi chưa có yêu cầu.

## Rủi ro

Build thành công không chứng minh giao diện đúng; tạm dừng gửi không có nghĩa dừng thu.

## Xử lý lỗi và khôi phục

Đối chiếu nhật ký backend, console trình duyệt, gói WebSocket và timestamp đã lưu.

## Kết quả

Đã kiểm tra sinh/phát lại dữ liệu, raw HTTP, WebSocket và phục hồi sau tạm ngắt gửi. Frontend build và phục vụ HTTP 200; chưa có kiểm tra trực quan bằng trình duyệt điều khiển được, nên giữ IN_PROGRESS.

## Bằng chứng hoàn thành

- AI: 15 tests PASS về kịch bản, đặc tả, tái lập, số mẫu và chuyển tiếp.
- Phát lại giả lập ATTENTION/raw được backend nhận; WebSocket nhận SIM-E2E/SYNTHETIC sau HTTP 202.
- Có file JSONL trong vùng lưu; sau tạm ngắt 2 giây, timestamp tiếp tục đúng thứ tự.
- Frontend build/container PASS, localhost:5173 trả 200; kiểm tra trực quan vẫn NOT_VERIFIED.

## Cập nhật kiểm tra — 2026-10-20

- Frontend 26/26 tests PASS bằng React DOM/jsdom: vòng đời hook, StrictMode, chọn thiết bị và dọn kết nối. Socket/đồng hồ được giả lập; chưa kiểm tra bố cục trình duyệt.
- Kiểm tra riêng HTTP/WebSocket thật: 18/18 gói khớp nguồn, ba kịch bản, từ chối gói sai và nối lại subscriber; dùng DB tạm.
- Backend/frontend container khởi động lại thành công, HTTP 200; chưa chứng minh hiển thị trực quan.
- Công cụ trình duyệt trả `No browser is available`, discovery `[]`; giữ BLOCKED_BROWSER/IN_PROGRESS, không có công bố phần cứng hoặc lâm sàng.
- Xem [bằng chứng nhánh 02](../integration/02-VERIFICATION.md).

## Giai đoạn tiếp theo

Giai đoạn 03 — MAX30102
