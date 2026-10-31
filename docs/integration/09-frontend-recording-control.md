# 09 — Giao diện điều khiển và xem phiên

| Mục | Nội dung |
|---|---|
| Nhánh | `feature/frontend-recording-control` |
| Phụ trách | Trung — IT |
| Phụ thuộc |02/04/08 |
| Ước lượng |1–2 ngày |
| Tiến độ |[Dòng09](PROGRESS.md) |

## Kết quả và phạm vi

Chọn thiết bị, Start/Stop có xác nhận, xem bản ghi và tải file. Sessions/History hiện mới giữ chỗ; thêm điều hướng tối thiểu, không làm lại giao diện.

Theo [kiến trúc](MQTT_ARCHITECTURE.md), browser chỉ HTTP/WS tới backend. Không cài MQTT trong browser hoặc đưa credential vào VITE_*/bundle.

File dự kiến: pages/Sessions.tsx, App.tsx, api/index.ts, kiểu phiên/API, hook hỏi trạng thái và lựa chọn thiết bị/phiên dùng chung. Chỉ làm History khi cần danh sách đã thống nhất, chưa phân tích nghiên cứu.

## Công việc

- [ ] Điều hướng Dashboard/Sessions, giữ phong cách/component hiện có.
- [ ] Cùng lựa chọn device/session với02, nút Stop không trỏ thiết bị khác dashboard.
- [ ] List có lần nhận gần nhất/nguồn. Tách HTTP/WS, broker, presence, tuổi mẫu và trạng thái ghi; online không tự là live.
- [ ] Form Start có ID/thiết bị hợp lệ, ID người giả danh nếu cần.
- [ ] Gửi Start một lần, chờ/disable, xử lý409/422 đúng.
- [ ] HTTP nhận yêu cầu chỉ hiện STARTING; RECORDING sau ACK thiết bị, không đoán từ200/PUBACK.
- [ ] Broker mất/backend xử lý lỗi thì hiện chờ/quá hạn/lý do từ API, không tự thêm trạng thái nghiệp vụ.
- [ ] Stop hiện STOPPING/gửi nốt và số batch chờ khi API có; STOPPED không mặc định đủ.
- [ ] Thiết bị mất/timeout báo thiếu/ABORTED, không bấm lặp tạo nhiều phiên.
- [ ] Thời lượng theo mốc thu, số mẫu/batch và gap; không lấy đồng hồ browser làm nguồn.
- [ ] List có lọc/phân trang/nguồn/trạng thái và mức đủ dữ liệu.
- [ ] Detail có tổng kết/bản mô tả/tải file, không tải toàn raw cho list.
- [ ] Hỏi lại API theo chu kỳ cấu hình hoặc sự kiện, không vòng liên tục; dọn khi đổi trang.
- [ ] Hỏi định kỳ ở đây là browser tra cứu, không khôi phục firmware polling. WS mở nhưng thiếu telemetry vẫn stale theo02.
- [ ] Refresh lấy trạng thái thật từ backend; localStorage không quyết định phiên đang mở.
- [ ] API/WS URL và CORS đúng máy LAN, localhost browser khác máy không là laptopserver.
- [ ] Có loading/rỗng/lỗi, nhãn bàn phím rõ; không lộ stack trace.
- [ ] Giữ nhãn SYNTHETIC, không thêm SpO2/metric mô hình khi API chưa hỗ trợ.

## Kiểm thử

| Ca | Kết quả |
|---|---|
| Chưa thiết bị/dữ liệu | Rỗng/chờ rõ, không phiên giả |
| Start ACK chậm | STARTING, không gửi đôi |
| HTTP/WS còn, broker mất/presence cũ | Chờ/quá hạn/stale đúng |
| Broker mất, bản ghi cũ còn | Xem/tải được qua HTTP |
| Start xung đột/sai dữ liệu | Báo rõ, sửa form được |
| Stop còn batch/timeout | Đủ/thiếu theo backend |
| Refresh/đổi trang/thiết bị | Lựa chọn nhất quán, không rò polling/socket |
| Giả lập/thật | Nhãn/lọc/xuất nguồn đúng |
| Tải lỗi/phiên lớn | Báo lỗi, không giữ raw lớn trong RAM |
| Màn hình nhỏ/bàn phím | Thao tác chính dùng được |

Dùng API giả có kiểm soát trước, rồi simulator/board. Build không thay ảnh/nghiệm thu browser.

## Nghiệm thu và khôi phục

- [ ] TypeScript/build/tests trạng thái đạt; có bằng chứng trình duyệt/thiết bị.
- [ ] Không báo đã thu trước ACK hoặc đủ khi còn gap.
- [ ] Không credential/kết nối MQTT trong bundle; API/WS là nguồn trạng thái.
- [ ] CI và tài liệu đạt.
- [ ] Commit gợi ý: `feat(frontend): điều khiển và xem phiên thu`.

UI lỗi vẫn thao tác API theo đặc tả; không sửa tay DB. Rời trang không tự Stop phiên ngoài ý muốn.

## Nhật ký

| Ngày/commit | Việc | Bằng chứng | Kết quả |
|---|---|---|---|
|—|—|—|Chưa thực hiện|
