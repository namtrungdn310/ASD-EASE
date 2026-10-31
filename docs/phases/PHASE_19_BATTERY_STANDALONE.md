# Giai đoạn 19 — Chạy độc lập bằng pin

## Trạng thái

NOT_STARTED

## Người phụ trách

Tân — Tự động hoá

## Mục tiêu

Chạy ESP32 bằng nguồn đeo đã kiểm chứng, không dùng USB laptop.

## Lý do

Chế độ thi đấu cần nguồn độc lập.

## Phụ thuộc

Giai đoạn 18, Giai đoạn 00

## Đầu vào

Pin, ổn áp, mạch sạc an toàn và firmware tích hợp.

## Công việc

- [ ] Làm đúng phạm vi đã thống nhất.
- [ ] Chạy các kiểm thử và lưu bằng chứng.
- [ ] Cập nhật tài liệu giai đoạn, tiến độ, thay đổi và quyết định liên quan.

## File dự kiến thay đổi

ai/edge_firmware/...; docs/HARDWARE_PROFILE.md

## Lưu ý triển khai

Đo công suất, thời gian chạy và khởi động lại; không mặc định board có mạch sạc.

## Kiểm thử

Khởi động khi ngắt USB, đo thời gian chạy và thử sụt nguồn có kiểm soát.

## Điều kiện nghiệm thu

- [ ] Có bằng chứng thật cho mục tiêu.
- [ ] Các kiểm thử bắt buộc đều đạt.
- [ ] Cập nhật tiến độ và rủi ro trước khi chuyển tiếp.

## Đầu ra

Phần triển khai có thể review, kết quả kiểm thử và tiến độ đã cập nhật. Không tự chuyển sang giai đoạn sau khi chưa có yêu cầu.

## Rủi ro

Rủi ro pin, sụt nguồn, quá nhiệt hoặc thời gian chạy thiếu.

## Xử lý lỗi và khôi phục

Ngắt pin an toàn; thử nguồn bàn và xem nhật ký khởi động lại.

## Kết quả

Chưa thực hiện.

## Bằng chứng hoàn thành

Chưa có bằng chứng nghiệm thu.

## Giai đoạn tiếp theo

Giai đoạn 20 — Trình diễn không dây

