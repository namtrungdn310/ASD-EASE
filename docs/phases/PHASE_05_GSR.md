# Giai đoạn 05 — GSR

## Trạng thái

IN_PROGRESS

## Người phụ trách

Tân — Tự động hoá

## Mục tiêu

Thu số đếm ADC của cảm biến GSR đúng cách và an toàn.

## Lý do

Bổ sung tín hiệu điện da, nhưng không coi số đo chưa hiệu chuẩn là độ dẫn chính xác.

## Phụ thuộc

Giai đoạn 00

## Đầu vào

Chân ADC1, điện áp mô-đun và dây nối đã kiểm chứng.

## Công việc

- [ ] Làm đúng phạm vi đã thống nhất.
- [ ] Chạy các kiểm thử và lưu bằng chứng.
- [ ] Cập nhật tài liệu giai đoạn, tiến độ, thay đổi và quyết định liên quan.

## File dự kiến thay đổi

ai/edge_firmware/src/sensors/GSRSensor.cpp

## Lưu ý triển khai

Driver có lấy trung bình ADC, đổi điện áp, EMA, mức nền 5 giây và công thức độ dẫn dựa trên giả thiết mạch. Công thức chưa được nghiệm thu bằng phép đo tham chiếu. Cấu hình hiện tại sau PR #11 là GPIO7, không còn GPIO4; vẫn cần Tân xác nhận dây nối thực.

## Kiểm thử

Build/nạp; kiểm tra hở mạch, chập qua điều kiện thử an toàn và tín hiệu tham chiếu; đo dải giá trị và nhiễu.

## Điều kiện nghiệm thu

- [ ] Có bằng chứng thật cho mục tiêu.
- [ ] Các kiểm thử bắt buộc đều đạt.
- [ ] Cập nhật tiến độ và rủi ro trước khi chuyển tiếp.

## Đầu ra

Phần triển khai có thể review, kết quả kiểm thử và tiến độ đã cập nhật. Không tự chuyển sang giai đoạn sau khi chưa có yêu cầu.

## Rủi ro

Điện áp không an toàn, ADC phi tuyến, ảnh hưởng Wi-Fi hoặc tiếp xúc không ổn định.

## Xử lý lỗi và khôi phục

Ngắt mô-đun; đối chiếu điện áp và chân ADC bằng nguồn tham chiếu.

## Kết quả

Đã đọc phần triển khai từ PR #7; build trên máy đạt. Chưa có biên bản kiểm thử trên board đáp ứng các mục bên trên.

## Bằng chứng hoàn thành

Cần lưu board, commit, cấu hình, mẫu có thứ tự, số đo thời gian và thử ngắt cảm biến. Chưa đủ để đánh dấu DONE.

## Giai đoạn tiếp theo

Giai đoạn 06 — Tích hợp cảm biến

