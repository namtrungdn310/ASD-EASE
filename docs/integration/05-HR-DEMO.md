# HR demo: ưu tiên hiển thị đều, chấp nhận số tương đối

**Đã có hướng thay thế mới hơn:** ESP hiện nạp0.3.18-tracker. Xem [theo dõi chu kỳ, kết quả cổ tay và cách chạy](05-HR-CYCLE-TRACKER.md). Tài liệu này giữ mô tả và kết quả của0.3.16-demo để rollback, không phải trạng thái mới nhất.

Ngày 2026-11-07. Trung đổi mục tiêu trước mắt sang demo HR tương đối, ít nhảy trên FE. Đây là tiêu chí hiển thị mới; không đổi kết luận của [vòng kiểm sai số trước](05-HR-WEAK-SIGNAL-EXPERIMENT.md) hoặc tự coi nhịp bình thường 60–100 bpm là đáp án.

## Cách hoạt động

- Profile riêng `esp32s3_hr_demo`, firmware `0.3.16-demo`. Giữ cảm biến/LED danh định 10 mA, chip 200 Hz/gộp 4, FIFO 50 Hz; không đổi dây, GSR/IMU hoặc schema API.
- Vẫn dùng cửa sổ 8 giây, kiểm mỗi giây. Demo chấp nhận đỉnh tự tương quan từ 0,25 thay vì 0,60, tỷ số công suất/nhiễu proxy từ 1 thay vì 2. Cửa sổ gần 4 giây là điểm cộng, không phủ quyết cả cửa sổ 8 giây. Hai kênh đều rõ nhưng bất đồng vẫn bị loại.
- Xác nhận hai ứng viên liên tiếp, lệch tối đa 25%; median ba ứng viên mới rồi EMA 0,30 để giảm nhảy. Dải tính giữ 40–200 bpm, không ép về 60–100. Bộ này có thể nhầm nửa/gấp đôi nhịp hoặc nhận nhiễu; không dùng HR demo làm nhãn chuẩn để train.
- Tắt worker MSPTD strict ở riêng profile demo. Bản đối chứng và các profile khác giữ chính sách cũ. Không sửa công suất Wi-Fi hoặc khẳng định đã giải quyết sự kiện nóng.
- Mất tiếp xúc, lỗi đọc, clip, gap hoặc cửa sổ không có bằng chứng thì HR không được công nhận. Reset xóa trạng thái làm mượt. Chỉ đọc cache không đổi timestamp, không tính HR mới từ số cũ.
- Dashboard ghi **Nhịp tim ước tính** và **Bản demo · số đo tương đối**. Khi telemetry mới không có HR, thẻ được giữ số gần nhất tối đa 10 giây, kèm **Nhận cách đây … giây · đang tìm lại nhịp**. Tuổi tính từ timestamp gói có HR gần nhất, không phải timestamp từng nhịp mạch. Hết 10 giây thì để trống; mất kết nối hoặc clock lùi không kéo dài số giữ.
- Việc giữ số chỉ ở thẻ FE. Telemetry/DB vẫn nhận null, biểu đồ giữ khoảng trống; không nối thêm điểm hoặc gán nguồn SYNTHETIC thành DEVICE. Gói dữ liệu vẫn được gửi theo nhịp khoảng một giây khi MQTT/phiên đã đồng bộ, độc lập việc HR có kết quả hay không.

HR được làm mượt sẽ phản ứng chậm hơn vài giây, ngoài độ trễ vốn có của cửa sổ 8 giây. Không gọi số này là nhịp tức thời chính xác. Demo không bảo đảm có HR ở mọi giây khi sóng quang chưa đủ rõ.

## Kết quả phần mềm và replay

Đã chạy PpgRate C++ thực tế, cùng bốn raw không sửa mẫu. Đây là replay phát triển đã xem, không có đáp án HR cổ tay. Mỗi trace có 34 lần đánh giá của state machine; không tráo với 32 cửa sổ của báo cáo offline cũ.

| Trace | HR mới, đối chứng | HR mới, demo | Thẻ có số nếu giữ tối đa 10 giây và ghi tuổi |
|---|---:|---:|---:|
| A1 | 0/34 | 2/34 | 12/34 |
| B1 | 0/34 | 19/34 | 32/34 |
| A2 | 0/34 | 0/34 | 0/34 |
| B2 đo lại | 0/34 | 10/34 | 16/34 |

Số giữ trên thẻ không phải HR mới. Dù nới điều kiện, A2 vẫn không có số; không có cơ sở hứa chỉ phần mềm sẽ phủ kín mọi lượt cổ tay. Các ứng viên trên raw thật nằm khoảng 40–82 bpm nhưng chưa biết đúng hay sai.

Trên 588 cửa sổ nhiễu trắng/có màu, demo nhận **18 cửa sổ** thuộc bốn ca nhiễu có màu, trong khi đối chứng không nhận. Đây là đánh đổi của demo đã ghi nhận, không giấu để gọi là bộ đo chính xác. Các ca sạch 40–200 bpm vẫn được kiểm theo nhịp gốc, không ép về vùng nghỉ.

Kiểm đã đạt:

- 31 ca demo C++: dải nhịp sạch, timestamp, flat, reset, gap và xung đột hai kênh.
- 76 ca PpgRate đối chứng; 89 ca driver và 12 snapshot qua serializer/schema, ở cả profile mặc định và demo.
- 10 ca hybrid selector và 8 ca driver/hybrid cũ; bốn tổ hợp header.
- Frontend 61 test và build đạt; có ca kiểm tuổi số giữ, hết hạn, mất kết nối, clock lùi và không sửa telemetry/points. Build có cảnh báo bundle lớn đã có, không lỗi biên dịch.
- Hai build `esp32s3_ppg_led10` và `esp32s3_hr_demo` đạt. Demo dùng static RAM 56.204 byte, program flash 932.669 byte; đây không phải số đo heap/stack/nhiệt khi chạy thật.

Bằng chứng local: `backend/storage/local/ppg-demo-replay.json`, các log `ppg-demo-*.log`. Báo cáo có source/input hashes, số HR mới và số thẻ giữ riêng. Chưa chạy CI GitHub từ xa.

## Nạp và dùng

```powershell
# Build/nạp bản demo khi ESP sẵn sàng ở COM7:
.\.venv\Scripts\python.exe -m platformio run -d ai/edge_firmware -e esp32s3_hr_demo -t upload --upload-port COM7

# Dùng hằng ngày, giữ Wi-Fi/host đã cấu hình:
npm run dev
```

Không thay default_envs; nạp firmware thường bằng env khác sẽ quay về chính sách của env đó. Rollback dùng `-e esp32s3_ppg_led10` thay cho `-e esp32s3_hr_demo`; không thay credential hoặc xóa DB.

Đã nạp demo trên COM7, esptool kiểm hash thành công. Đã bật lại hotspot laptop chia sẻ Wi-Fi quán, mở launcher và nhận **5 frame DEVICE `0.3.16-demo` qua WebSocket**, GSR/IMU đủ, cùng một phiên tự động. Khoảng timestamp 1.002/1.002/1.005/1.002 ms. HR 0/5 trong lượt kiểm kết nối; chưa phải lượt cổ tay sẵn sàng.

## Bước vật lý tiếp theo

Một lượt cổ tay 45 giây trên cùng cách đặt nhẹ, không đè. Chỉ yêu cầu đặt tay khi backend/WS đã sẵn sàng; thu xong báo thả tay ngay, rồi ghi số HR mới, khoảng trống và số giữ ở FE riêng. Chưa kết luận HR ổn định hoặc đúng tương đương trước lượt này.

### Lượt cổ tay demo đã thu

Trung xác nhận đặt nhẹ, sẵn sàng; thu xong đã báo thả tay trước khi phân tích. Raw `ppg-20261107-161019-282878.csv/.json`: **2.251 mẫu, 45,016 giây, complete**, không lỗi capture/cleanup hoặc trace dropped, timestamp không lùi; một khoảng tối đa 40 ms. I2C/overflow/gap/clip/ALC không tăng trong log.

WebSocket `ppg-demo-wrist-20261107-161019-374937.json`: **14 gói, HR 0/14**, GSR/IMU đủ 14/14, một phiên. Không ghi thành 45 gói hoặc nói FE đã có HR ổn định. NET ban đầu wifi/mqtt/sync=1 nhưng cuối lượt sync=0, publish fail tăng 0→1, error=32774; cảm biến vẫn thu raw tới hết. Broker có kết nối lại/timeout trong cùng giai đoạn; chưa xác định nguyên nhân kết nối, không quy do thuật toán hoặc ánh sáng từ mã lỗi này.

Đầu lượt còn thời gian chờ cửa sổ sạch sau chuyển động; về cuối guard cho phép HR nhưng tự tương quan vẫn thấp. Không có số HR để thẻ FE giữ lại. Profile demo chưa đáp ứng hiển thị HR đều ở lượt thực này, dù một số replay cũ có thêm số.

Đã kết thúc giữ tay; Trung cắm lại và để mạch trên bàn theo hướng dẫn để kiểm riêng kết nối 70 giây, không yêu cầu đo HR đồng thời. Chưa tự hạ thêm ngưỡng vì một lượt thất bại.

**Phân tích thêm:** log driver có HR ở 9/45 bản chụp: một bản 40 bpm, tám bản 71,3–72,8 bpm; chúng đến sau khi WS dừng nhận gói. Vì vậy HR 0/14 phía WS không có nghĩa driver không tạo HR trong cả lượt. Những số này vẫn chưa có tham chiếu; không sửa thành “HR đúng”. Replay nguyên raw, không có motion guard của lượt thật, cho 12/34 cửa sổ demo; đối chứng 0/34. Lưu `ppg-demo-live-trace-replay.json`.

Kiểm mạch trên bàn 70 giây sau khi Trung cắm lại: **68 gói DEVICE, max gap nhận ở laptop 1,078 giây, không lỗi capture**. Bằng chứng `ppg-demo-table-network-20261107-161540-39f7de.json`. Chưa kết luận da/đế tròn làm suy tín hiệu Wi-Fi; khác boot/thời điểm cũng là yếu tố. Chuẩn bị một lượt cổ tay nữa với laptop gần cụm, chưa đổi firmware hoặc thông số HR, để kiểm dữ liệu có lên FE cùng lúc không.

### Lượt cổ tay thứ hai, laptop ở gần

Trung xác nhận laptop cách tay khoảng 30–50 cm, đặt nhẹ như trước; thu đủ 45 giây và báo thả tay ngay. Không thay firmware hay thông số giữa hai lượt demo.

- Raw `ppg-20261107-161819-856c88.csv/.json`: **2.251 mẫu, complete, 45,0 giây**, không lỗi capture/cleanup, không trace dropped, timestamp không lùi; khoảng tối đa 40 ms.
- WS `ppg-demo-wrist-20261107-161819-3422b4.json`: **45 gói DEVICE, GSR/IMU 45/45, một phiên, HR 0/45**. Khoảng nhận lớn nhất 1,078 giây; có thời gian nhận từng frame để tái kiểm.
- NET wifi/mqtt/sync luôn 1 trong 45 bản chụp, fail/drop/error 0; invalid 2 đã có từ trước và không tăng. Không sửa backend để nhận gói chưa đồng bộ.
- Driver cũng HR 0/45, cổng chuyển động mở 36/45 bản chụp. Contact/settled có, I2C/overflow/gap/clip/ALC không báo lỗi; tự tương quan một số cửa sổ 4 giây còn đạt khoảng 0,32 nhưng cả cửa sổ 8 giây chưa tạo ứng viên đủ điều kiện. Không kết luận không có mạch sinh lý từ việc thuật toán chưa tách được.

**Kết luận hiện tại:** đã hoàn tất code/nạp demo và kiểm đường truyền liên tục ở lượt 45 giây này. Chưa đạt HR luôn có số trên cách đặt cổ tay hiện tại. Có thêm khả năng hiển thị ở replay và HR trên driver ở lượt trước, nhưng chưa lặp lại đủ để gọi ổn định. Không tiếp tục yêu cầu đặt tay hoặc thay tham số trong cùng vòng này, không điền số tùy ý vào HR để phủ kín FE. Khi chưa có một ước tính nào, cơ chế giữ số ở FE cũng không có số để giữ.

Giao diện vẫn mở qua `npm run dev`; bản demo hiện có trên ESP. Đã lưu đủ bằng chứng và giữ cách rollback. Chưa commit/push/merge, chưa xác nhận sai số HR hoặc khắc phục nguyên nhân nóng.
