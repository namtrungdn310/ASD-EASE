# Vì sao HR từ dao động thành không hiển thị?

Ngày 2026-11-06. Đây là kết quả chẩn đoán, chưa phải nghiệm thu HR. Board giữ bản 0.3.10; lượt kiểm tra này không đổi ngưỡng, cấu hình hoặc nạp firmware mới.

## Đối chiếu trên cùng dữ liệu

Lấy nguyên hàm bắt đỉnh, trung vị và EMA từ commit `330f92c`, kèm header/cấu hình ở chính commit đó. Chạy offline trên cùng timestamp và RED/IR đã thu; so với `processing/ppg_rate.h` hiện tại. Tái tạo cờ tối thiểu hai nhịp và TTL 3s cho kết quả cũ, reset cả hai sau khoảng mất mẫu; không giả lập lại toàn bộ FIFO/driver/mạng. Đây là thuật toán trong commit lưu trữ, không khẳng định tái hiện chính xác mọi bản thử 0.3.3–0.3.7 chưa commit.

| Đầu vào | Mốc kiểm tra có dữ liệu | Bộ bắt đỉnh cũ có HR | Bộ cửa sổ hiện tại có HR |
|---|---:|---:|---:|
| Đầu ngón tay vừa thu, file 022934 | 39 | 30, khoảng 73–95 bpm | 0 |
| Đầu ngón tay file 012205 | 34 | 28, khoảng 77–97 bpm | 6, khoảng 74–78 bpm |
| Đầu ngón tay file 020430 | 44 | 36, khoảng 72–82 bpm | 1, khoảng 74 bpm |
| Cổ tay file 020011 | 34 | 19, khoảng 94–106 bpm | 0 |
| SYNTHETIC: sóng sạch 80 bpm/60s | 59 | 58, khoảng 80–81 bpm | 47, khoảng 80 bpm |
| SYNTHETIC: nhiễu trắng, không có nhịp/60s | 59 | 58, khoảng 78–119 bpm | 0 |
| SYNTHETIC: nhiễu màu, không có nhịp/60s | 59 | 44, khoảng 67–114 bpm | 0 |
| SYNTHETIC: sóng phẳng/60s | 59 | 0 | 0 |

Mỗi mốc cách khoảng 1s khi có mẫu. Mẫu mất không được bù; không tính mốc không có dữ liệu thành kết quả hợp lệ. Bộ hiện tại cần khoảng 13s cho tiếp xúc và xác nhận cửa sổ đầu, nên độ sẵn có trên sóng sạch bao gồm thời gian chờ này. Bộ cũ được chấm theo giá trị trung vị/EMA còn mới, không phải mỗi giây phát hiện một nhịp mới. Số mốc replay khác số frame live do thời điểm bắt đầu và trạng thái bộ lọc khác nhau.

Các ca tổng hợp dùng seed17; đây là ví dụ hồi quy hữu hạn, không đại diện mọi nhiễu. Cả RED/IR nhiễu có tương quan theo cách sinh; không coi là hai phép kiểm độc lập. Không gửi dữ liệu replay lên Dashboard hoặc DB.

## Kết luận có bằng chứng

1. Việc đổi bộ xử lý làm HR không còn hiển thị trên file mới nhất: cùng sóng, bộ cũ có số nhưng bộ hiện tại từ chối hết. Không được quy toàn bộ cho vị trí cổ tay hoặc thao tác đặt tay.
2. Bộ cũ có thể tạo số trông hợp lý từ nhiễu không có nhịp. Vì vậy, việc ban đầu có số chưa chứng minh đo đúng; không chọn lại bộ cũ chỉ vì biểu đồ kín hơn.
3. Bộ hiện tại không hỏng hoàn toàn: tính đúng sóng sạch 80 bpm và có kết quả trên một số đoạn đo cũ. Tuy nhiên, chưa đáp ứng lượt đo đầu ngón tay mới nhất. Không có HR tham chiếu nên chưa phân biệt được bao nhiêu cửa sổ là từ chối đúng và bao nhiêu là bỏ sót tín hiệu thật.
4. Đối chiếu BIDMC có ECG-HR đã tìm được lỗi nửa nhịp và giúp sửa 0.3.10; kết quả đó không thay kiểm chứng MAX30102 trên người. Xem [phương pháp và giới hạn](05-PPG-REFERENCE-BENCHMARK.md).

## Lỗi đọc riêng biệt

Trong file mới nhất, phần đầu khoảng 33s có tiếp xúc và không tăng lỗi đọc nhưng vẫn không có HR. Sau đó mới xuất hiện một lỗi giao dịch, khoảng mất 6,221s, rồi đọc lại. GSR/IMU/mạng vẫn chạy. Vì vậy lỗi đọc giải thích khoảng gián đoạn nhưng chưa giải thích toàn bộ HR trống.

Code hiện đánh dấu dữ liệu không hợp lệ, xoá lịch sử HR và thử khởi tạo lại sau 3s. Khởi tạo/thẩm định không đạt sẽ chờ lượt tiếp; log hiện tại chưa ghi giao dịch/thanh ghi và lần thử cụ thể nên chưa xác định nguồn gây khoảng 6,2s. Không kết luận hỏng mạch, nguồn, dây hoặc lỗi thư viện khi chưa có bằng chứng; không rút ngắn backoff hoặc lấp số cũ để che khoảng mất.

## Bằng chứng local và phần còn thiếu

Harness chẩn đoán: `backend/storage/local/compare_ppg.py`; báo cáo: `ppg-processing-comparison.json`. Có hash từng file và header hiện tại, giữ kết quả từng mốc. Cả script/file đo đều bị Git bỏ qua vì chứa đường dẫn và dữ liệu local; chưa phải công cụ CI. Các đoạn thuật toán được lấy từ repo, không sửa implementation sản phẩm để tạo kết quả so sánh.

Chưa có kết luận tối ưu hoặc nghiệm thu HR. Bước kỹ thuật tiếp theo cần chẩn đoán giao dịch I2C lỗi cụ thể và đánh giá thay đổi bộ HR trên dữ liệu có tham chiếu, đồng thời báo tỷ lệ có số và sai số. Không tiếp tục hạ ngưỡng chỉ để khớp những file chưa có đáp án; không yêu cầu tháo cụm theo yêu cầu hiện tại của Trung.
