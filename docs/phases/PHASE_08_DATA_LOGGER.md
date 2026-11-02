# Giai đoạn 08 — Ghi dữ liệu

## Trạng thái

NOT_STARTED

## Người phụ trách

Trung — IT

## Mục tiêu

Lưu các batch raw thật có chung mốc thời gian và thông tin phiên.

## Lý do

Tạo đầu vào kiểm tra được cho bước thu thập dữ liệu.

## Phụ thuộc

Giai đoạn 07

## Đầu vào

Luồng mẫu thật, API raw-batch và ID phiên.

## Công việc

- [ ] Làm đúng phạm vi đã thống nhất.
- [ ] Chạy các kiểm thử và lưu bằng chứng.
- [ ] Cập nhật tài liệu giai đoạn, tiến độ, thay đổi và quyết định liên quan.

## File dự kiến thay đổi

backend/app/services/raw_storage.py; backend/app/api/v1/raw_data.py

## Lưu ý triển khai

Raw đi HTTP; điều khiển và bản tổng kết đi MQTT. Lưu file batch bất biến, SQLite lưu chỉ mục. Chỉ xác nhận sau khi file/chỉ mục nhất quán; giữ null, nguồn dữ liệu và bản ghi cũ. Xem [quy tắc nhận dữ liệu](../contracts/INGESTION_V1.md).

## Kiểm thử

Start/Stop; retry, trùng/xung đột, đến sai thứ tự, lỗi giữa lúc ghi; tổng kết MQTT đến trước/sau raw HTTP; mất từng đường truyền, đầy bộ đệm và xuất lại đối chiếu số mẫu/hash/đơn vị/timestamp.

## Điều kiện nghiệm thu

- [ ] Có bằng chứng thật cho mục tiêu.
- [ ] Các kiểm thử bắt buộc đều đạt.
- [ ] Cập nhật tiến độ và rủi ro trước khi chuyển tiếp.
- [ ] Phân biệt STOPPED với recording_complete khi thiếu mẫu, mất batch hoặc hết thời gian chờ.
- [ ] Có số đo tốc độ, đồng bộ, RAM và bộ đệm thật; không thay bằng kết quả giả lập.

## Đầu ra

Phần triển khai có thể review, kết quả kiểm thử và tiến độ đã cập nhật. Không tự chuyển sang giai đoạn sau khi chưa có yêu cầu.

## Rủi ro

File ghi dở, hết dung lượng hoặc lệch đặc tả.

## Xử lý lỗi và khôi phục

Giữ file gốc; kiểm tra từng batch và dùng phiên mới khi cần.

## Kết quả

Chưa thực hiện.

## Bằng chứng hoàn thành

Chưa có bằng chứng nghiệm thu.

## Kế hoạch chi tiết

Xem [kế hoạch tích hợp](../integration/README.md), [tiến độ](../integration/PROGRESS.md) và [đặc tả API](../API_CONTRACT.md). Tài liệu không thay đổi trạng thái nghiệm thu.

## Giai đoạn tiếp theo

Giai đoạn 09 — Thu thập bộ dữ liệu

