# Giai đoạn 15 — Xuất mô hình

## Trạng thái

NOT_STARTED

## Người phụ trách

Trung — IT

## Mục tiêu

Xuất mô hình nhỏ đã được duyệt, kèm đầy đủ thông tin nguồn.

## Lý do

ESP32 cần bộ tham số có thể dùng lại và cho kết quả nhất quán.

## Phụ thuộc

Giai đoạn 14

## Đầu vào

Mô hình đã chọn và thứ tự đặc trưng cố định.

## Công việc

- [ ] Làm đúng phạm vi đã thống nhất.
- [ ] Chạy các kiểm thử và lưu bằng chứng.
- [ ] Cập nhật tài liệu giai đoạn, tiến độ, thay đổi và quyết định liên quan.

## File dự kiến thay đổi

ai/src/export/...; ai/edge_firmware/include/model_generated.h

## Lưu ý triển khai

Sinh mã/tham số, giữ phiên bản và thứ tự đặc trưng; không tải joblib không tin cậy.

## Kiểm thử

Lưu/tải lại rồi đối chiếu trên bộ đầu vào cố định bằng Python.

## Điều kiện nghiệm thu

- [ ] Có bằng chứng thật cho mục tiêu.
- [ ] Các kiểm thử bắt buộc đều đạt.
- [ ] Cập nhật tiến độ và rủi ro trước khi chuyển tiếp.

## Đầu ra

Phần triển khai có thể review, kết quả kiểm thử và tiến độ đã cập nhật. Không tự chuyển sang giai đoạn sau khi chưa có yêu cầu.

## Rủi ro

Sai thứ tự, sai độ chính xác số hoặc phép toán không được hỗ trợ.

## Xử lý lỗi và khôi phục

So từng tham số và kết quả với mô hình gốc.

## Kết quả

Chưa thực hiện.

## Bằng chứng hoàn thành

Chưa có bằng chứng nghiệm thu.

## Giai đoạn tiếp theo

Giai đoạn 16 — Suy luận trên thiết bị

