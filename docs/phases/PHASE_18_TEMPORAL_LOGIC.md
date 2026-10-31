# Giai đoạn 18 — Logic trạng thái theo thời gian

## Trạng thái

NOT_STARTED

## Người phụ trách

Trung và Tân

## Mục tiêu

Thêm logic thời gian để chuyển NORMAL/ATTENTION/UNCERTAIN ổn định.

## Lý do

Dự đoán tức thời dễ nhiễu và chưa phù hợp phát cảnh báo.

## Phụ thuộc

Giai đoạn 17

## Đầu vào

Điểm dự đoán và cờ chất lượng đã đối chiếu.

## Công việc

- [ ] Làm đúng phạm vi đã thống nhất.
- [ ] Chạy các kiểm thử và lưu bằng chứng.
- [ ] Cập nhật tài liệu giai đoạn, tiến độ, thay đổi và quyết định liên quan.

## File dự kiến thay đổi

ai/edge_firmware/src/state/...

## Lưu ý triển khai

Ghi rõ ngưỡng vào/ra và thời gian giữ trạng thái; chất lượng kém có thể chuyển UNCERTAIN.

## Kiểm thử

Thử chuỗi chuyển trạng thái, phục hồi, hiệu chuẩn và mất dữ liệu.

## Điều kiện nghiệm thu

- [ ] Có bằng chứng thật cho mục tiêu.
- [ ] Các kiểm thử bắt buộc đều đạt.
- [ ] Cập nhật tiến độ và rủi ro trước khi chuyển tiếp.

## Đầu ra

Phần triển khai có thể review, kết quả kiểm thử và tiến độ đã cập nhật. Không tự chuyển sang giai đoạn sau khi chưa có yêu cầu.

## Rủi ro

Kẹt trạng thái, chậm quá mức hoặc ngưỡng chưa được kiểm chứng.

## Xử lý lỗi và khôi phục

Phát lại chuỗi chuẩn và ghi lý do chuyển trạng thái.

## Kết quả

Chưa thực hiện.

## Bằng chứng hoàn thành

Chưa có bằng chứng nghiệm thu.

## Giai đoạn tiếp theo

Giai đoạn 19 — Chạy độc lập bằng pin

