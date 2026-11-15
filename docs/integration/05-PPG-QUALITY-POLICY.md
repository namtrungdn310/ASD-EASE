# Bước 3: cấu hình thử chất lượng được chốt trước benchmark

Kết quả sau khi chạy: đã chọn mức chặt và kiểm qua vòng mới sau khóa cấu hình; các ngưỡng bên dưới không đổi. [Báo cáo, ca không đạt và giới hạn](05-PPG-QUALITY-EVALUATION.md). Chưa nạp firmware mới.

Ngày2026-11-06. Đây là chính sách thử offline, **chưa phải firmware hoặc ngưỡng đã kiểm định**. Dùng ý tưởng kiểm hình dạng sóng theo template và kiểm khoảng nhịp, tham khảo [PPG-quality của tác giả](https://ppg-quality.readthedocs.io/en/latest/functions/assess_ppg_quality/). Các con số dưới là lựa chọn kỹ thuật của dự án, không gán chúng cho công bố tham khảo.

## Cấu hình cố định trước khi chấm

MSPTDfastv2 trên cùng sóng đã lọc C++ như bước2, cửa sổ quá khứ8s, kiểm lại4s gần nhất. Cần ít nhất5 đỉnh/4 khoảng nhịp; dải40..200bpm, khoảng nhịp0,3..1,5s. Đỉnh sát nhau dưới15 mẫu được gom bằng cách giữ đỉnh cao hơn. Không clamp HR hoặc dùng tham chiếu để chọn kênh.

Template là32 điểm pha sau bỏ đường nối hai đầu mỗi sóng và chuẩn hoá norm. Mỗi nhịp được chấm với template từ các nhịp còn lại, không tự góp vào template của nó. Năng lượng phổ được tính trong0,5..4Hz; phần quanh tần số HR ứng viên và hai hài tiếp theo dùng bề rộng±0,15Hz. Đây không phải SNR đã hiệu chuẩn.

| Điều kiện | Cân bằng | Chặt |
|---|---:|---:|
| CV khoảng nhịp tối đa | 0,18 | 0,12 |
| Trung vị tương quan template tối thiểu | 0,85 | 0,90 |
| Phân vị20 tương quan template tối thiểu | 0,65 | 0,75 |
| Tỷ lệ năng lượng phổ tối thiểu | 0,55 | 0,65 |

Cả hai giữ sàn biên độ tương đương4counts, yêu cầu HR8s/4s lệch không quá12%, đỉnh cuối còn mới trong1,5 lần trung vị RR+50ms/tối đa3s. Hai cửa sổ liên tiếp cùng đoạn, cách không quá1,5s và HR lệch không quá12% mới công nhận. Cửa sổ chồng nhau không phải bằng chứng độc lập. Mất mẫu, không đủ lịch sử, đổi đoạn hoặc không đạt quality phải xoá xác nhận; không lấp số cũ.

Hai kênh đạt nhưng bất đồng thì từ chối; còn lại ưu tiên IR rồi RED. Chế độ `hybrid` giữ nguyên kết quả C++ đang valid, chỉ dùng kết quả quality đã xác nhận khi bộ C++ không có số. Cơ chế này không sửa những lỗi đã được C++ công nhận; phải báo hạn chế đó.

Kiểm thử trước benchmark cho thấy có pha của sóng sạch40bpm chỉ còn4 đỉnh sau xử lý biên, không đủ điều kiện5 đỉnh. Giữ nguyên policy đã chốt và báo từ chối ở nhánh quality; hybrid vẫn giữ HR40 hợp lệ từ bộ C++. Không sửa expected của một ca lỗi thành PASS đo chính xác hoặc nới ngưỡng để che giới hạn này.

## Cách chọn và điều kiện trước khi cân nhắc nạp

- Bộ01–10 BIDMC,4 file người thật và30 lượt nhiễu ở bước2 đã xem là **bộ phát triển**. Không gọi chúng là test độc lập.
- Hai cấu hình chỉ được so như đã chốt; không quét hàng chục ngưỡng để làm file cổ tay đẹp hơn.
- Ứng viên cần không tạo thêm HR trên1.410 cửa sổ nhiễu đã chốt; không tăng số cửa sổ sai trên10bpm so đối chứng ở bộ tham chiếu. MAE tổng trên phần chấp nhận không vượt đối chứng quá0,2bpm và p95 không tăng quá0,5bpm. Phải có thêm cửa sổ tham chiếu đạt để có lý do đổi, đồng thời báo từng cửa sổ mới và sai số của chúng.
- Nếu ứng viên đạt vòng phát triển, chốt một cấu hình rồi mới kiểm BIDMC11–15 và seed nhiễu mới. Không chỉnh ngưỡng sau khi xem vòng này. Không đạt thì giữ firmware, ghi kết quả thất bại thay vì bỏ ca khó.
- Khi nhiều cấu hình cùng đạt, ưu tiên MAE trên phần tham chiếu nhận thêm thấp hơn, rồi số cửa sổ nhận thêm lớn hơn; không dùng số cổ tay chưa có đáp án để chọn cấu hình.
- File cổ tay chưa có HR tham chiếu: chỉ báo độ sẵn có/biến thiên, không lấy số trông hợp lý làm đáp án.
- Chỉ sau khi qua kiểm phần mềm mới đánh giá bản C++/heap/stack/thời gian trên ESP; thời gian NumPy laptop không thay số đo board.

Kiểm độ đều có thể loại nhịp không đều; nhiễu tuần hoàn giống sóng mạch có thể lọt. Chưa dùng chất lượng này làm kết luận y khoa, phần trăm chất lượng MQTT hoặc nhãn train đúng. Đánh giá có thể kết luận chưa có ứng viên đủ điều kiện, không bắt buộc nạp một thay đổi.
