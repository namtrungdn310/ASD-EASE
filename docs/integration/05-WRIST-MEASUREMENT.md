# Đo tại cổ tay: triển khai và kiểm chứng từng bước

**Kế hoạch hiện hành:** [tìm nguyên nhân và cải thiện thuật toán HR](05-HR-ROOT-CAUSE-PLAN.md). Trung chốt chỉ đặt nhẹ cụm lên cổ tay, không đè xuống; thuật toán không áp ngưỡng quá khắt khe làm mất nhịp thật trong tín hiệu yếu. Chỉ tối ưu HR; GSR/IMU giữ nguyên. Các mốc phiên bản và bảng tiến độ bên dưới là hồ sơ lịch sử, không phải checklist hiện hành.

**Cập nhật cách đặt, 2026-11-07:** Trung xác nhận lật toàn bộ đế tròn, đặt mặt có ô quang của mạch xanh MAX30102 áp nhẹ vào da cổ tay, không dùng ngón tay ép. Cổ tay nhỏ nhưng toàn bộ mạch xanh nằm trong phạm vi cổ tay; ESP32 và MPU nhô ra ngoài một phần. Giữ cách đặt này làm điều kiện thiết kế/thử. Không mặc định hai mạch kia đang kê hở MAX30102 chỉ từ ảnh.

Đã kiểm log các lượt gần nhất: cả45 lần chụp trạng thái đều qua cổng tiếp xúc/ổn định và cổng chuyển động của firmware. Các cổng này dựa trên tín hiệu/cấu hình, không phải phép đo lực ép hoặc chứng minh đường quang tiếp xúc hoàn hảo. Lý do HR bị từ chối còn phải phân biệt giữa đặc điểm sóng thu được và điều kiện của thuật toán; chưa kết luận lỗi riêng phần cứng hay phần mềm. Board hiện0.3.13-led10 làm đối chiếu, HR cổ tay chưa đạt; xem [kết quả mới nhất](05-WRIST-SAMPLING-TRIAL.md). Các mốc phiên bản dưới là lịch sử.

**Bước3 đã chọn ứng viên offline `hybrid_strict`.** Nó tăng kết quả trên một file cổ tay6/32→13/32, chưa giúp file không ấn và chưa có HR tham chiếu. Vòng kiểm mới có43 cửa sổ tham chiếu nhận thêm, không thêm lỗi lớn/nhiễu. Board vẫn0.3.11; cần port C++ và đo tài nguyên trước bản thử bước4. [Kết quả và cấu hình đã chốt](05-PPG-QUALITY-EVALUATION.md).

**Đã xong đối chiếu offline bước2:** giữ board0.3.11; chưa chọn bộ HR mới. MSPTD tạo thêm ứng viên trên cổ tay nhưng cũng tạo nhiều số trên nhiễu không có nhịp. Bước3 cần lớp chất lượng tín hiệu trước quyết định nạp, không chọn theo độ kín biểu đồ. [Kết quả và giới hạn](05-PPG-ALGORITHM-EVALUATION.md). Chưa nghiệm thu HR cổ tay.

**Bản hiện tại 0.3.11:** theo thứ tự Trung chọn, đang làm bước1 chẩn đoán lỗi đọc. Giữ thuật toán HR/LED/lấy mẫu như0.3.10; chưa chuyển bước chọn thuật toán mới hoặc nghiệm thu cổ tay. Xem [log và kết quả quan sát](05-PPG-I2C-DIAGNOSIS.md). Các mốc dưới là lịch sử.

Đã đo cổ tay45s trên bản này:2.252 mẫu liên tục, không phát sinh I2C hoặc khoảng mất6s; WS41 GSR/41 IMU nhưng4 HR71,7..74,2bpm, so với34/41 ở đầu ngón tay. **Chưa đạt HR cổ tay ổn định**, chưa có nhịp tham chiếu để chấm sai số. Đang dùng file đã lưu đánh giá bước2; chưa yêu cầu giữ tay đo thêm.

**Cập nhật 0.3.10, 2026-11-06:** đã nạp COM7/hash verified; sửa lỗi nhận nửa nhịp. Đo đầu ngón tay 45s sau xác nhận có 41 frame DEVICE/41 GSR/41 IMU nhưng 0 HR, kèm lỗi đọc gây mất 6,2s. **HR chưa đạt kể cả lượt thử đầu ngón tay**; chưa quy lỗi cho vị trí đeo hoặc module. Giữ cụm cố định. Xem [bằng chứng mới nhất](05-SENSOR-RECOVERY.md). Các mốc dưới là lịch sử.

**Bản hiện tại0.3.9, đã nạp/đo:** đã triển khai thu/lọc/đánh giá tín hiệu yếu và chọn IR/RED. Giữ nguyên cụm theo yêu cầu Trung; không yêu cầu tháo bo/đổi dây. Bốn build và kiểm thử phần mềm đạt. Lượt35s có30 frame WS/30 IMU nhưng0 HR hợp lệ; **HR cổ tay chưa đạt nghiệm thu**, không tuyên bố code đã làm số đo ổn định. Xem [bằng chứng0.3.9](05-SENSOR-RECOVERY.md). Các phiên bản dưới giữ lịch sử.

**Bản đang chạy0.3.8:** đã nạp, thay bộ bắt đỉnh dễ nhận nhiễu bằng ước tính HR theo cửa sổ8s có kiểm tra chu kỳ. Chưa nghiệm thu HR cổ tay; số đo bị từ chối vẫn để null. Đang so sánh đầu ngón tay/cổ tay với sóng thô. Xem [bằng chứng và giới hạn](05-SENSOR-RECOVERY.md). Các mốc cũ bên dưới giữ làm lịch sử.

**Hiện tại0.3.5, đã nạp trên máy Trung:** sửa profile IMU6515/ID0x74 và vòng phục hồi FIFO PPG. Hai vector đã qua WS thật; PPG đã có cửa sổ đọc≈50Hz, còn kiểm tra HR cổ tay. Chi tiết [khôi phục cảm biến](05-SENSOR-RECOVERY.md). Các mốc0.3.2/0.3.1 dưới đây giữ làm lịch sử, không phải trạng thái bản đang chạy.

Cập nhật 2026-11-06. Trung xác nhận ưu tiên **tối ưu code**; mẫu gá đeo chỉ minh họa, không phải điều kiện để tiếp tục sửa phần mềm. Firmware hiện tại **0.3.2**, chưa nạp/đo lại board. Chi tiết và giới hạn tại [chuỗi đo0.3.2](../contracts/SENSOR_ACQUISITION_0_3_2.md).

## Kiểu đeo đã thống nhất

- ESP32-S3 Super Mini, MPU6050 và MAX30102 cố định trên đế tròn. Khi đo lật mặt có cảm biến xuống da; các lượt gần nhất dùng mặt trong cổ tay theo xác nhận trước khi đo.
- Mắt quang MAX30102 áp vào da; hai điện cực Grove GSR đặt ở hai ngón tay.
- Theo xác nhận2026-11-07, toàn bộ mạch xanh nằm trong phạm vi cổ tay, hai mạch còn lại nhô ra ngoài một phần; đặt nhẹ, không ép cụm mạch bằng ngón tay.
- USB cấp nguồn/nạp/log; dữ liệu Dashboard vẫn qua Wi-Fi → MQTT → backend → WebSocket.
- Giữ nguyên chân đã xác nhận: MAX SDA8/SCL9; MPU SDA5/SCL11; GSR ADC7.
- Ảnh mặt dưới Trung gửi: ba bo và đầu nối đều hướng ra phía da. Chưa đo độ cao; phải kiểm tra mắt quang có thật sự chạm da khi đeo. Che phần mạch/chân dẫn điện bằng mặt đỡ cách điện, chừa cửa sổ mắt quang; không siết cả cụm để ép linh kiện vào da.

## Tiến độ

| Bước | Việc cần đạt | Trạng thái |
|---|---|---|
| 1 | FIFO PPG, clock, lọc và dải HR nhất quán | Code đạt28 ca FIFO và37 ca driver chung; chưa đo board |
| 2 | FIFO IMU50Hz/10Hz, kiểm tra cấu hình, bù lệch gyro khi đứng yên | Đã triển khai/test bằng fake, chưa đo board |
| 3 | ADC eFuse GSR, baseline ổn định, chặn µS/delta chưa hiệu chuẩn | Đã triển khai/test; raw ADC vẫn truyền |
| 4 | Lịch lấy mẫu và log riêng, hồi quy MQTT/backend/WS/frontend | Code đã có, xem kết quả kiểm tra bên dưới |
| 5 | Nạp bản mới và đo thực tế từng bước | Chưa nạp; không chờ hoàn thiện vỏ để bàn giao code |
| 6 | Chốt tham số theo dữ liệu tham chiếu, xác minh độ chính xác tại cổ tay | Cần số đo thực, chưa kết luận tối ưu tuyệt đối |

Hoàn thiện phần code độc lập trước; sau đó hướng dẫn từng bước nạp/đo theo yêu cầu Trung. Không tăng LED/giảm ngưỡng hàng loạt hoặc gọi cấu hình là tối ưu khi chưa có số đo. Lưu dữ liệu đo cục bộ; không đưa thông tin sinh lý cá nhân vào Git.

## Kết quả code0.3.2 — 2026-11-06

- PASS28 ca FIFO,37 ca driver C++ sản xuất với fake ngoại vi;10 snapshot từ driver qua serializer/schema runtime. PASS39 ca protocol, backend111, frontend60 và build,9 nhóm MQTT native qua broker/backend/WS thật. Dữ liệu test nguồn SYNTHETIC; không thay board thật.
- PASS4 tổ hợp header. Build cuối sau khi chọn default_envs đã đạt cả ba env trong134,622 giây; chưa có CI trên thay đổi mới.

| Env | RAM static | Flash | Trạng thái |
|---|---:|---:|---|
| esp32s3_supermini | 47.884 byte | 927.585 byte | PASS |
| esp32s3_network_check | 47.884 byte | 927.597 byte | PASS |
| esp32s3_serial_check | 21.340 byte | 332.301 byte | PASS |

Các số trên không gồm toàn bộ tài nguyên runtime; task log có stack6KiB và queue riêng, vẫn cần đo heap/stack khi nạp. Warning macro I2C_BUFFER_LENGTH trong SparkFun vẫn có; không có lỗi build. Hai file schema local của Trung giữ nguyên hash. Chưa nạp/đo bản0.3.2, chưa push/merge, chưa xác nhận kết quả trên máy Tân.

## Mốc lịch sử 0.3.1 — đường đọc PPG

Firmware chuẩn bị: **0.3.1**. Bỏ cờ build ép phiên bản 0.2.0, dùng một nguồn trong `board_config.h`. Pin SparkFun 1.1.2, giữ nguyên tốc độ/LED/ngưỡng/bộ lọc để so sánh trước và sau.

- Đọc FIFO phần cứng trực tiếp, không đi qua ring 4 phần tử của SparkFun. Decoder chỉ hỗ trợ mode RED/IR hiện tại, có kiểm tra lại mode và rollover sau setup.
- Đọc lô tối đa 31 mẫu theo snapshot con trỏ; chia giao dịch tối đa 30 byte. Lô 4/8/16 mẫu không bị mất vì head/tail của ring phần mềm trùng nhau.
- Tắt FIFO rollover. Kiểm tra overflow trước khi pop vì phần cứng xóa bộ đếm khi pop mẫu; phát hiện con trỏ trùng nhưng có cờ gần đầy, lỗi nguồn và lỗi I2C/thiếu byte.
- Khi lô không chắc chắn: không đưa mẫu của lô vào HR, xóa lịch sử nhịp và khởi tạo lại cảm biến theo chu kỳ retry. Có thể mất HR vài giây trong lúc bắt lại; không giữ HR cũ như hợp lệ.
- Khi raw RED/IR chạm toàn thang 18 bit: đếm clip và không công nhận HR từ lô đó. Chưa có bộ ước lượng chất lượng tín hiệu hoàn chỉnh.
- Timestamp từng mẫu hiện vẫn ước tính theo cuối lượt đọc và chu kỳ danh định. Chưa phải timestamp chính xác từ ngắt cảm biến, chưa đủ bằng chứng dùng RR làm HRV.
- Không thay schema MQTT, tốc độ telemetry, session tự động hoặc cách chạy `npm run dev`.

### Dòng log `[PPG-DAQ]`

| Trường | Ý nghĩa |
|---|---|
| `ms` | Thời gian boot khi in dòng, ms |
| `n` | Tổng mẫu RED/IR đã đọc trọn lô từ khi boot, kể cả chưa tiếp xúc da |
| `batchMax` | Lô lớn nhất đã đọc được |
| `pollMax` | Khoảng cách lớn nhất giữa hai lượt poll trong giai đoạn cảm biến sẵn sàng, ms |
| `io` | Lỗi giao dịch I2C trong đường đọc FIFO |
| `overflow` | Số lần phát hiện overflow/đầy không phân biệt được với rỗng |
| `lostMin` | Tổng số mẫu mất tối thiểu mà bộ đếm overflow phần cứng báo; bão hòa 31 mỗi lần đọc, không phải tổng mất chính xác |
| `gaps` | Lô bị hủy do lỗi I2C, nguồn hoặc FIFO không chắc chắn |
| `clip` | Số mẫu có RED hoặc IR bằng 262143 |
| `IR`, `RED` | Mẫu cuối, đơn vị ADC quang; không phải điện áp hay nhịp tim |
| `ac` | Biên độ đỉnh–đáy sau lọc theo driver, chưa phải SNR |
| `hr`, `valid` | HR hiện tại và kết quả kiểm tra của thuật toán hiện tại; không thay so sánh với thiết bị tham chiếu |
| `fw` | Phiên bản bản nạp |

`overflow=0`, `lostMin=0`, `valid=1` không tự chứng minh không mất mẫu hoặc HR đúng. Tính tốc độ từ chênh lệch `n`/`ms` giữa hai dòng, so cùng khoảng đo; không lấy số mẫu chia toàn bộ thời gian boot có khởi tạo/retry. Cần so cả khi bật/tắt log và Wi-Fi ở bước nghiệm thu.

### Kiểm tra phần mềm

```powershell
.\.venv\Scripts\python.exe scripts/check_ppg_acquisition.py
.\.venv\Scripts\python.exe scripts/check_sensor_drivers.py
.\.venv\Scripts\python.exe scripts/check_firmware_protocol.py
.\.venv\Scripts\python.exe -m platformio run -d ai/edge_firmware -e esp32s3_supermini -e esp32s3_network_check -e esp32s3_serial_check
.\.venv\Scripts\python.exe .github/scripts/check-firmware-headers.py
```

Test C++ dùng transport giả để thử decoder/batch/wrap/I2C/overflow; không thay kiểm tra Wire trên ESP thật. Chưa nạp hoặc xác nhận số đo mới chỉ vì build thành công.

Kết quả local 2026-11-05: 28 ca FIFO, 39 ca protocol/schema, 4 tổ hợp header và hai env PlatformIO đều đạt. Env dùng header local: RAM static 47.868 byte, flash 920.201 byte; env network-check: RAM static 47.868 byte, flash 920.213 byte. Đây là kích thước build, không phải heap/stack đo lúc chạy. Có warning `I2C_BUFFER_LENGTH` được định nghĩa lại trong thư viện SparkFun; code ứng dụng dùng burst tối đa 30 byte, không phụ thuộc giá trị macro đó. Chưa có CI trên thay đổi mới, chưa nạp, chưa đánh giá độ chính xác.

## Bước kế tiếp trên thiết bị

Không yêu cầu sửa mẫu gá trước khi tiếp tục code. Bước thực tế tiếp theo là nạp bản mới; chưa chỉnh biến trở GSR hoặc thay dây điện. Khi đo thì giữ tiếp xúc quang ổn định và tránh chân dẫn điện tì vào da.

Nạp riêng bản **esp32s3_supermini**, không nạp các env `_check`. `default_envs` cũng đã trỏ về bản dùng thật để tránh nạp lần lượt các cấu hình test. Đóng Serial Monitor trước khi nạp. COM7 vẫn được phát hiện ngày2026-11-06; kiểm tra lại nếu cắm sang cổng khác.

```powershell
.\.venv\Scripts\python.exe -m platformio run -d ai/edge_firmware -e esp32s3_supermini -t upload --upload-port COM7
```

Giữ cụm mạch đứng yên vài giây sau reboot để chốt lệch gyro. Chạy `npm run dev` như trước; phiên tự mở và dữ liệu vẫn đi qua Wi-Fi. Sau khi nạp thành công mới hướng dẫn ghi/đọc log kiểm tra, không coi kết quả build là phép đo thật.

Tiếp theo mới đo nền giữ yên tại cổ tay, rồi mới đổi thông số theo tín hiệu. Nếu đang giữ phiên theo dõi, nạp sẽ reboot ESP và tạo boot/phiên tự động mới; đó là hành vi mong đợi.

## Tài liệu đối chiếu

- [MAX30102 datasheet: FIFO, bộ đếm overflow và hai kênh quang](https://www.analog.com/media/en/technical-documentation/data-sheets/MAX30102.pdf).
- [ADI: lưu ý tín hiệu PPG ở cổ tay](https://ez.analog.com/optical_sensing/a/documents/do19523/how-can-ppg-signal-quality-be-improved-when-measured-on-the-wrist). Hướng dẫn cụ thể cho MAX30101, không coi LED xanh là tính năng của MAX30102.
- [ESP32-S3 ADC và hiệu chuẩn](https://docs.espressif.com/projects/esp-idf/en/v4.4/esp32s3/api-reference/peripherals/adc.html).
- [Seeed Grove GSR: biến trở, điện cực và hiệu chỉnh](https://wiki.seeedstudio.com/Grove-GSR_Sensor/).
