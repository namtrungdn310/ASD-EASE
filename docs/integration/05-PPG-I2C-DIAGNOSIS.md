# Bước 1: tìm lỗi đọc MAX30102

Ngày 2026-11-06. Bản chẩn đoán **0.3.11**, kế tiếp 0.3.10. Giữ nguyên LED mặc định 0x1F, chip 200Hz/averaging4/FIFO50Hz, bộ HR, TTL và backoff 3s. Chưa chuyển sang bước chọn thuật toán HR hoặc nghiệm thu cổ tay.

## Bổ sung gì?

- `MAX30102Sensor.h/.cpp`: lưu lỗi I2C gần nhất, thanh ghi, byte yêu cầu/nhận, mã trả về khi gửi; lưu lần khởi tạo thành công/thất bại và thời gian tới mẫu đầu sau phục hồi.
- `main.cpp`: in `[PPG-IO]` và `[PPG-INIT]` từ bản chụp ở task log sẵn có, khoảng một lần mỗi giây. Không in trong giao dịch I2C, không thêm trường MQTT, không thay lấy mẫu bằng USB.
- `capture_ppg_trace.py`: cho phép lưu thêm đúng hai loại log trên. Không lưu SSID/password hoặc dòng CONFIG.
- Tests: thêm lỗi cấu hình, probe mờ của thư viện, FIFO thiếu byte và chuỗi lỗi đọc→khởi tạo thất bại→thành công. Không tạo lỗi trên board bằng cách rút dây hoặc tắt nguồn khi đo.

## Đọc log

`[PPG-IO] events/at`: số lỗi được ghi và millis của lỗi gần nhất. Lỗi được giữ sau phục hồi; thấy một dòng lặp lại không có nghĩa phát sinh lỗi mới. `reg=0xFF` nghĩa không biết/không áp dụng, không phải đã đọc thanh ghi FF.

| phase | Đang làm gì |
|---:|---|
| 0 | Chưa ghi lỗi |
| 1 | Probe qua thư viện |
| 2 | Đọc lại cấu hình sau setup |
| 3 | So cấu hình đọc lại với giá trị yêu cầu |
| 4 | Đọc metadata hoặc FIFO trong lúc lấy mẫu |
| 5 | Pop/bỏ FIFO hỏng để phục hồi |
| 6 | Watchdog không có mẫu |

| kind | Lỗi |
|---:|---|
| 0 | Chưa ghi lỗi |
| 1 | `endTransmission(false)` trả mã khác 0; `code` giữ nguyên mã Wire |
| 2 | `requestFrom` trả thiếu byte; đối chiếu requested/received |
| 3 | Hết byte khi rút dữ liệu nhận dù request báo đủ |
| 4 | Thư viện báo probe thất bại nhưng không trả giao dịch cụ thể |
| 5 | Giá trị cấu hình không khớp; expected/observed là giá trị sau mask |
| 6 | Watchdog không có mẫu; không suy ra đã NACK |
| 7 | Cờ power-reset được nhận từ thanh ghi trạng thái |

`[PPG-INIT] attempts/ok/failed` đếm mọi lần gọi begin, kể cả startup. `started/duration/maxDuration/lastRecovery/retryMs` đều ms. `lastRecovery` chỉ chốt khi có mẫu mới đầu tiên sau lỗi, chưa phải có HR hợp lệ trở lại; startup thành công bình thường giữ 0. Không xoá lịch sử lỗi khi khởi tạo lại thành công.

Giao dịch bên trong `MAX30105::begin/setup` vẫn do thư viện quản lý. Nếu probe thất bại, chỉ ghi phase1/kind4, không bịa thanh ghi hoặc mã NACK. Setup ghi cấu hình được thẩm định bằng readback; chưa có mã lỗi riêng cho từng lệnh ghi nội bộ.

## Kiểm chứng phần mềm

Đạt 76 ca HR, 56 ca driver và 12 snapshot qua serializer/schema ở cả baseline và LED10mA; 32 ca FIFO, 39 ca protocol. Có ca tái hiện:

```text
t=0: đọc trạng thái thất bại, vô hiệu HR
t=3.000ms: begin thất bại ở readback 0x08
t=6.000ms: begin thành công
t=6.020ms: mẫu mới đầu tiên; lastRecovery=6020
```

Đây là clock/I2C giả lập. Nó chứng minh có thể phân biệt chuỗi phục hồi hai lần thử, chưa chứng minh lỗi 6,221s trên board lần trước có cùng nguyên nhân. Không rút ngắn backoff hoặc giữ HR cũ để che khoảng mất.

## Trạng thái board

Đã build4 env/4 tổ hợp header và nạp baseline COM7/hash verified11,199s. RAM56116B/flash931553B. Hash bộ HR khớp bản benchmark0.3.10, xác nhận không thay thuật toán. Chưa CI/commit/push mới.

Lượt đầu không cần tiếp xúc da, 45s: init1/ok1/failed0, duration16ms; `[PPG-IO] events=0` từ đầu tới cuối. PPG510→2712 mẫu trong12864→56873ms, khoảng50,03Hz; io/clip0. Overflow/gap42 đã có trước lúc bắt đầu ghi và không tăng, không tuyên bố startup không mất mẫu. Network wifi/mqtt/sync1, fail/drop0, invalid1 từ startup; loopGap/pollMax27ms, heapMin184612B, stack watermark3612 theo API framework. WebSocket nhận5 frame DEVICE0.3.11/có phiên và đủ5 IMU.

Log local: `backend/storage/local/ppg-io-0311-c1a584df.json`. Chưa tái hiện lỗi đọc cũ, chưa kết luận nguyên nhân đã được xử lý. Không tự tạo lỗi bằng tháo dây.

### Lượt đầu ngón tay có xác nhận trên 0.3.11

Trung xác nhận đã đặt ngón tay. Thu45s được2.251 mẫu, khoảng timestamp lớn nhất40ms, không trace drop/timestamp lùi. Không có khoảng mất6s. `[PPG-IO] events=0`; init vẫn1/ok1/failed0, duration16ms, không phải khởi tạo lại.

PPG7666→9868 mẫu trong155866→199871ms (khoảng50,04Hz). io/clip0; overflow/gaps42/discarded73 có từ trước lượt và không tăng. Contact/settled giữ1, restarts16 không tăng. Serial45 dòng có36 dòng HR hợp lệ, gồm31 chọn IR và5 chọn RED;9 dòng không có HR nằm ở đầu lượt và một đoạn ngắn về cuối. Không gọi toàn bộ9 dòng là warmup vì chưa có bằng chứng cho đoạn cuối.

WS cùng lượt nhận41 frame DEVICE0.3.11/có phiên, đủ41 GSR/41 IMU, **34 frame HR68,5..74,6bpm**. Thời điểm ghi Serial và WS khác nhau, không dùng34/41 và36/45 làm cùng một mẫu số. Các số này chứng minh có kết quả live, chưa chứng minh sai số vì chưa có nhịp tham chiếu.

Thời gian xử lý HR lớn nhất4960µs; loopGap/pollMax27ms. Network wifi/mqtt/sync1, fail/drop0; invalid1 giữ từ startup. HeapMin cuối183248B, stack watermark3612, log stack3332 theo API framework. IMU io/overflow/gaps0; clip7 đã có trước lượt và không tăng. Chưa nghiệm thu độ ổn định dài hạn hoặc không rò bộ nhớ.

File local: `ppg-20261106-174444-63d1de.csv/.json` và `ppg-0311-finger-ws-ef4948f2.json` trong thư mục được Git bỏ qua. Bộ HR có cùng SHA256 với0.3.10: kết quả tốt hơn ở lượt này không được quy cho thay thuật toán, thay LED hoặc bản chẩn đoán. Điều kiện tiếp xúc/môi trường/lượt đo khác, chưa tách từng yếu tố.

**Kết thúc lượt kiểm tra bước1:** phần ghi lỗi/tái hiện giả lập/quan sát board đã làm; nguyên nhân lỗi6,221s cũ vẫn chưa xác định vì chưa tái hiện. Giữ log để bắt nếu lỗi quay lại. Không đánh dấu lỗi I2C đã sửa dứt điểm. Có thể dùng đoạn mới không mất mẫu để đánh giá thuật toán offline ở bước2; chưa cần nạp đổi bộ HR hoặc thử cổ tay ngay.

### Lượt cổ tay cùng bản 0.3.11

Sau xác nhận Trung đã chuyển về vị trí cổ tay dự định đeo và che sáng, thu45s được2.252 mẫu, khoảng timestamp20ms, không trace drop/timestamp lùi. `[PPG-IO] events=0`; init vẫn1/ok1/failed0, không khởi tạo lại. PPG17875→20077 trong359867→403864ms, khoảng50,05Hz. io/clip0; overflow/gap42/discarded73 giữ từ startup, không tăng.

WS nhận41 frame DEVICE0.3.11/có phiên, đủ41 GSR/41 IMU nhưng chỉ **4 HR:74,2;72,2;71,7;71,9bpm**. Cùng firmware và cấu hình, lượt đầu ngón tay ngay trước đó là34/41. Đây là hai lượt đo khác vị trí/thời điểm, chưa có tham chiếu nên không kết luận sai số hoặc nguyên nhân vật lý cụ thể.

Serial45 dòng có5 dòng HR, nằm cuối lượt (mốc thiết bị389872,398867,399871,402866,403864ms). Chỉ kênh IR đạt ở các mốc này; tương quan8s cả lượt cao nhất IR0,673, RED0,432. Các mẫu đầu chưa đủ lịch sử cửa sổ, những mốc không đạt tiếp theo không bị lấp bằng HR cũ. Contact/settled giữ1, restarts61 không tăng: không có bằng chứng cổng tiếp xúc cứ reset trong chính lượt này.

Network wifi/mqtt/sync1, fail/drop0, invalid1 từ startup; loopGap/pollMax27ms, maxRateProcessing5008µs; heapMin183248B, network stack watermark3612/log stack3332 theo API framework. IMU io/overflow/gaps0; clip11 đã có trước lượt và không tăng. Không có khoảng mất6s trong lượt này.

File local `ppg-20261106-174808-5adb40.csv/.json`, WS `ppg-0311-wrist-ws-dfb91e47.json`. **HR cổ tay vẫn chưa đạt độ sẵn có mong muốn.** Lượt này khoanh vùng hiện tượng HR bị từ chối khi đọc mẫu và đường truyền vẫn hoạt động; không quy cho lỗi I2C đã thấy ở lượt cũ, không tự kết luận module hỏng. Bước tiếp đánh giá bộ xử lý trên các file đã lưu, không yêu cầu Trung giữ tay thêm ngay.

### Lặp lại cổ tay: giữ cố định, chỉ chạm da và không ấn

Theo yêu cầu Trung, đo thêm45s trước bước đánh giá thuật toán, cùng firmware0.3.11 và cấu hình. Có2.252 mẫu, khoảng timestamp20ms, không trace drop/timestamp lùi. WS41 frame DEVICE/có phiên, đủ41 GSR/41 IMU nhưng **0/41 HR**.

`[PPG-IO] events=0`, init1/ok1/failed0 không đổi; io/clip PPG0, overflow/gaps42/discarded73 giữ từ trước lượt. PPG30237→32439 trong606867→650868ms (khoảng50,04Hz), không xuất hiện khoảng mất6s.

Contact/settled giữ1 ở cả45 dòng, restarts79 không tăng trong lượt. Tương quan8s lớn nhất IR0,378/RED0,350; tương quan4s lớn nhất IR0,558/RED0,596. Bộ hiện tại yêu cầu tối thiểu0,60 cùng các kiểm tra còn lại, nên không có HR được chấp nhận. Không suy từ việc contact=1 rằng đã nhận mạch đập, cũng không dùng ngưỡng hiện tại để kết luận tín hiệu thật chắc chắn không có nhịp.

IR86.440..110.257, RED62.824..84.312. Những số này chỉ là mức counts đã thu, không phải HR hoặc bằng chứng sai số. Network wifi/mqtt/sync1, fail/drop0, invalid1 từ startup; heapMin183248B, stack watermark3612, loopGap/pollMax27ms. IMU io/overflow/gaps0, clip11 không tăng.

File local `ppg-20261106-175215-0ab533.csv/.json`, WS `ppg-0311-wrist-repeat-ws-b603b4b6.json`. Hai lượt cổ tay lần lượt4/41 và0/41, ngón tay34/41. Chưa có nhịp tham chiếu và mỗi lượt có điều kiện tiếp xúc khác nhau, không kết luận việc không ấn là nguyên nhân duy nhất. Đã đủ dữ liệu để đối chiếu offline tiếp; không tiếp tục yêu cầu giữ tay chỉ để lặp lại một kết quả chưa đạt.
