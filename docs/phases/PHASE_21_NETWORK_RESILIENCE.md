# Giai đoạn 21 — Khả năng phục hồi kết nối

## Trạng thái

NOT_STARTED

## Người phụ trách

Trung và Tân

## Mục tiêu

Chứng minh vẫn thu mẫu/suy luận khi mất Wi-Fi và gửi lại telemetry mới sau kết nối.

## Lý do

AI trên thiết bị không được phụ thuộc mạng.

## Phụ thuộc

Giai đoạn 20

## Đầu vào

Luồng xử lý trên thiết bị và LAN thi đấu đã hoạt động.

## Công việc

- [ ] Làm đúng phạm vi đã thống nhất.
- [ ] Chạy các kiểm thử và lưu bằng chứng.
- [ ] Cập nhật tài liệu giai đoạn, tiến độ, thay đổi và quyết định liên quan.

## File dự kiến thay đổi

ai/edge_firmware/src/communication/...

## Lưu ý triển khai

Giới hạn hàng đợi/retry và tách thời gian gửi khỏi lấy mẫu.

## Kiểm thử

Ngắt/nối Wi-Fi trong khi quan sát bộ đếm lấy mẫu/trạng thái và bộ nhớ.

## Điều kiện nghiệm thu

- [ ] Có bằng chứng thật cho mục tiêu.
- [ ] Các kiểm thử bắt buộc đều đạt.
- [ ] Cập nhật tiến độ và rủi ro trước khi chuyển tiếp.

## Đầu ra

Phần triển khai có thể review, kết quả kiểm thử và tiến độ đã cập nhật. Không tự chuyển sang giai đoạn sau khi chưa có yêu cầu.

## Rủi ro

Lệnh chặn, hàng đợi vô hạn hoặc kết nối lại quá dồn dập.

## Xử lý lỗi và khôi phục

Tắt gửi, xem bộ nhớ/thời gian và giới hạn trạng thái retry.

## Kết quả

Chưa thực hiện.

## Bằng chứng hoàn thành

Chưa có bằng chứng nghiệm thu.

## Giai đoạn tiếp theo

Giai đoạn 22 — Kịch bản trình diễn

