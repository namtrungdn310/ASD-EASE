# Bản thử lấy mẫu400Hz cho cổ tay

Cập nhật 2026-11-07. **Lượt cổ tay 0.3.15-wristdense đã hoàn tất: 0/39 frame có HR**, dù lấy mẫu, mạng và các cổng kiểm tra đều hoạt động. Cấu hình 400 Hz/avg8 chưa cho thấy cải thiện trong lượt này. Đã quay về bản đối chiếu 0.3.13-led10, 200 Hz/avg4/LED10mA. Chưa chọn cấu hình cổ tay tối ưu; không yêu cầu đo thêm ở thời điểm này.

## Vì sao thử

Lượt10mA đầu có15/39 frame WS chứa HR79–85,1bpm; lượt lặp10mA sau xác nhận lại không có HR dù sensing/mạng/contact/guard ổn định. Vì vậy chưa thể chọn10mA là cấu hình đo cổ tay đáng tin cậy. Đã dừng việc tăng LED sau ba mức6,2/10/12,4mA.

Bản thử này giữ dòng LED10mA và thuật toán, chỉ tăng số lần lấy mẫu trên chip để có thêm mẫu trung bình cho mỗi giá trị FIFO. Ý định là giảm thành phần nhiễu không tương quan; chưa có bằng chứng cải thiện trên da thật hoặc phục hồi được tín hiệu quang đã mất.

## Thay đổi cụ thể

| Thông số | Đối chiếu0.3.13-led10 | Bản thử0.3.15-wristdense |
|---|---|---|
| Env | `esp32s3_ppg_led10` | `esp32s3_wrist_dense` |
| RED/IR danh định | 10mA,0x32 | Giữ nguyên |
| Sample rate trên chip | 200Hz | 400Hz |
| Số mẫu trung bình | 4 | 8 |
| FIFO/API acquisition profile | 50Hz | Giữ50Hz |
| FIFO_CONFIG0x08 | 0x5F | 0x7F |
| SPO2_CONFIG0x0A | 0x2B | 0x2F |
| Pulse/ADC | 411µs/18bit/4096nA | Giữ nguyên |
| HR/filter/quality/guard | Cấu hình đã kiểm trước đó | Giữ nguyên |
| Telemetry | Khoảng1gói/s, schema1.1 | Giữ nguyên |

Các env cũ và default6,2mA giữ hành vi trước đó. Driver chỉ cho phép hai cặp200/4 và400/8, có static_assert và đọc lại đúng thanh ghi; không chấp nhận cấu hình còn sót của profile khác. Không đổi GPIO, Wi-Fi/credential, API/topic, backend/frontend hoặc dataset thực để ép qua validation.

MAX30102 cho phép400Hz với411µs ở modeRED+IR (datasheet bảng11); averaging8 có mã011 (bảng3). [Nguồn chính thức](https://www.analog.com/media/en/technical-documentation/data-sheets/MAX30102.pdf). Đây là cấu hình hợp lệ, không phải bằng chứng tối ưu cho cổ tay. Xung LED mỗi giây nhiều hơn nên điện năng trung bình có thể tăng; chưa đo điện năng/nhiệt trên module. Theo dõi PWR_RDY/I2C/overflow/clip khi thử.

## Code và kiểm thử

- `board_config.h`, `platformio.ini`: profile thử riêng, version riêng để không trộn dữ liệu với0.3.13/0.3.14.
- `ppg_init.h`, `MAX30102Sensor.cpp`: ghi/kiểm đúng hai profile, vẫn một giao dịch mỗi bước, không chờ trong vòng lấy mẫu.
- `check_sensor_drivers.py`: thêm `--ppg-wrist-dense`. Bản0.3.14 có83 ca driver/12 snapshot qua serializer/schema đạt ở4 profile; bản sửa đồng hồ thêm6 ca, cả89 ca/12 snapshot ở4 profile đều đạt. 76 ca HR giữ nguyên đạt.
- 34 FIFO,8 tích hợp hybrid,10 selector,95 parity Python/C++ đạt. Không sửa policy để nhận thêm HR.
- `simulate_wrist_ppg.py --dense`: sinh mô hình400Hz rồi average8 thành50Hz; seed801/809 đạt các kiểm tra kỹ thuật. Mô hình nhiễu trắng có kiểm phương sai khi average8 so với4; không giả cùng mức giảm cho nhiễu chuyển động/ánh sáng.
- Mô phỏng vẫn có **1 ca nhận nhầm nhiễu quang tuần hoàn khi IMU yên**; báo cáo giữ `KNOWN_LIMITATION_FALSE_POSITIVE`. Không coi mô phỏng là nghiệm thu HR trên người hoặc dùng HR tham chiếu làm input.

0.3.14 đã build7 env/4 tổ hợp header,39 protocol đạt; nạp COM7/hash verified11,638s. Bản0.3.15 build cuối7 env/4 tổ hợp header đạt, RAM tĩnh79.252/327.680 byte, flash945.049/1.310.720 byte. Nạp COM7/hash verified12,103s; log `ppg-0315-build-final.log`, `ppg-0315-upload.log`. Giữ6 tên check CI; chưa CI từ xa/commit/push.

## Khoảng nhảy timestamp ở lượt kiểm đầu

Trace0.3.14 `ppg-20261107-003712-016910.csv/.json`:20s/998 mẫu, không rơi trace, có bước34508→34590ms (82ms), gap counter0→1. I2C/overflow/clip/discarded đều0, pollMax19ms, loopGap10ms; init1 lần thành công148ms, bước tối đa975µs. WS15s nhận14 frame0.3.14-wristdense, đủ GSR/IMU; chưa có tiếp xúc quang/HR.

Kiểm code phát hiện SampleClock bám mãi lưới20ms: tốc độ cảm biến lệch nhẹ có thể tích lũy sai số pha quá60ms rồi bị gọi là gap. Kiểm native đã tái hiện hiện tượng này với dòng mẫu liên tục có chu kỳ20,05/20,10ms. Tuy nhiên chưa có timestamp phần cứng nên không khẳng định chắc khoảng82ms thực tế chỉ do trôi đồng hồ.

Bản0.3.15 bật theo dõi trôi nhỏ **chỉ cho PPG profile400Hz**, IMU và các profile200Hz giữ cách gán thời gian cũ:

- Mỗi lô điều chỉnh pha chậm tối đa1ms, vẫn giữ khoảng20ms giữa các mẫu trong cùng lô; timestamp không vượt thời điểm đọc, không chèn hoặc lặp mẫu để bù.
- Giữ ngưỡng phát hiện sai số pha lớn; kiểm thêm thời gian giữa hai lần thực sự có mẫu và số mẫu FIFO. Khoảng dừng lớn với quá ít mẫu vẫn bị đánh gap, thay vì bị bù mất.
- Kiểm native gồm trôi nhanh/chậm, backlog4 mẫu kèm jitter, timestamp bất khả thi, gap400ms và khoảng dừng70ms chỉ có1 mẫu. Dòng liên tục không bị gap giả; các ca gián đoạn thật vẫn bị loại.
- Timestamp vẫn là ước lượng từ thời điểm đọc/FIFO, không phải giờ lấy mẫu phần cứng hoặc bằng chứng đo HRV. Chưa phân biệt chắc mất1 slot ngắn với độ trễ polling chỉ từ thông tin này.

Sau nạp bản sửa cần kiểm lại ít nhất55s trước khi yêu cầu áp cổ tay. Nếu gap vẫn xuất hiện, giữ bằng chứng và chưa coi sensing đã đạt; không nới ngưỡng HR để né lỗi.

## Kiểm55s trên0.3.15 trước đo cổ tay

Trace `ppg-20261107-004836-64cf9f.csv/.json`:55s/2.746 mẫu PPG (xấp xỉ50Hz), không rơi trace và không có timestamp lặp/lùi. Mốc ước lượng cách nhau17–21ms, không còn bước82ms trong lượt này; không khẳng định mọi nguyên nhân gap đã hết hoặc rate đúng50,000Hz.

- I2C/overflow/gap/clip/ALC/discarded đều0 từ boot tới cuối quan sát; PPG pollMax20ms, loopGap11ms. Init1 lần thành công146ms qua nhiều vòng, stepMax1.003µs.
- Log xác nhậnLED50/chip400/FIFO50, không tiếp xúc quang. IMU đã lấy bias, không lỗi/gap/overflow/clip, guardStill/allowHr1. Self-test hybrid đạt, chưa có cửa sổ đo người gửi worker.
- Heap thấp nhất148.640 byte, worker stack còn3.140 byte. WS50s nhận49 frame DEVICE/ESP32-001, đúng version0.3.15-wristdense, đủ49 GSR/IMU; mqtt/sync1, fail/drop/error0. File `ppg-0315-health-ws.json` giữ local.
- Code cuối:7 build/4 header,89 ca driver/12 snapshot ở4 profile,76 ca HR,34 FIFO,8 tích hợp hybrid/10 selector/95 parity đạt. Mô phỏng seed701 profile200 và801/809 profile400 chạy lại có hash nguồn mới; vẫn giữ ca nhận nhầm nhiễu tuần hoàn.

## Lượt cổ tay 0.3.15 sau xác nhận

Trace `ppg-20261107-005649-2c614d.csv/.json`: 45 giây, 2.246 mẫu PPG, timestamp 16–21 ms, không lặp/lùi hoặc rơi trace. Đã báo người dùng thả tay ngay sau lượt. Timestamp là ước lượng, không dùng số mẫu chia thời gian để khẳng định chip chạy chính xác tuyệt đối 50 Hz.

- I2C/overflow/gap/clip/ALC/discarded đều 0, init chỉ một lần thành công. Loop gap 13→14 ms; PPG pollMax 20 ms. Bước nhảy 82 ms của bản0.3.14 chưa xuất hiện lại trong lượt55s và lượt45s này.
- Contact/settled giữ1, restarts16→16. IMU đã lấy bias, không lỗi/gap/overflow; clip12 có từ trước lượt và không tăng. Guard `Still`, allowHr=1, score0,0045→0,0035; không phải cổng chuyển động chặn HR.
- Cả45 dòng Serial valid=0; worker completed11→55, accepted giữ0. Nhãn quang `CHUA_TACH_DUOC_NHIP` cả lượt. Bộ baseline và quality đều chưa công nhận kết quả.
- WS nhận39 frame `0.3.15-wristdense`, đủ39 GSR và39 vector IMU, **0 HR**; MQTT/sync1, error/fail/drop0. File `ppg-0315-wrist-20261107-005730-ws.json` giữ local. Không phải HR bị mất ở frontend hoặc mạng.
- IR179.924–186.394, RED103.746–106.703. Có phản xạ không chứng minh có nhịp đủ rõ. Không đủ bằng chứng từ lượt này để phân biệt nhịp thật bị bỏ sót với nhiễu được loại đúng, vì chưa có nhịp tham chiếu đồng bộ.
- Heap thấp nhất148.640 byte; worker stack còn3.124 byte, max wall163.160µs/cửa sổ, xử lý baseline tối đa5.011µs. Không ghi đè cửa sổ chờ.

## Trạng thái cuối đợt thử

Đã thử ba mức LED, lặp lại10mA và thử thêm400Hz/avg8. Một lượt10mA có15/39 HR, các lượt cổ tay còn lại chưa có HR; **chưa có cấu hình cho kết quả đủ lặp lại**. Không tiếp tục tăng LED hoặc nới quality gate từ các kết quả chưa có tham chiếu.

Đã quay về `esp32s3_ppg_led10`, firmware `0.3.13-led10`, 200Hz/avg4/LED10mA, hash verified11,556s; log `ppg-0313-final-control-upload.log`. Cấu hình lấy mẫu dày và sửa đồng hồ của0.3.15 vẫn có trong repo để kiểm tra/tái hiện, chưa được chọn làm mặc định.

Kiểm sau khi quay về: `ppg-20261107-010129-af5566.csv/.json`,20s/1.000 mẫu/max20ms, không rơi trace; không I2C/overflow/gap/clip/ALC, init1 lần thành công147ms qua nhiều vòng, stepMax1.462µs. Loop gap10ms. WS15s nhận14 frame đúng0.3.13-led10, đủ GSR/IMU; không tiếp xúc quang, HR trống phù hợp. File `ppg-final-control-health-ws.json` giữ local.

**Đã kiểm chứng phần code, lấy mẫu và truyền dữ liệu trong các lượt trên; mục tiêu HR cổ tay chưa đạt.** Phần còn thiếu để đánh giá/chọn thuật toán có cơ sở là nhịp tham chiếu đồng bộ và kiểm tra độ lặp lại của tín hiệu quang ở kiểu đeo thực tế. Chưa kết luận chip hỏng, phần cứng chắc chắn phải thay, hoặc chỉ sửa code chắc chắn sẽ giải quyết. Chưa nghiệm thu nhánh5, chưa CI từ xa/commit/push.

## Thứ tự thử và giới hạn

1. Hoàn tất build/headercheck, nạp bản thử rồi kiểm lấy mẫu, readback/counters và WS đúng version; người dùng chưa cần áp tay.
2. Chỉ khi mạng/sensing/IMU sẵn sàng mới yêu cầu xác nhận đặt nhẹ vào đúng vị trí cổ tay để thu45s. Theo dõi đồng thời số mẫu, quá sáng, trạng thái contact/motion, nguồn HR và các khoảng null.
3. So với các lượt cũ về khả năng có kết quả, độ liên tục và lỗi lấy mẫu. Nếu có kết quả phải kiểm lặp trước khi chọn profile. Chưa có nhịp tham chiếu thì không kết luận độ chính xác.

Chỉ thử thêm profile này ở bước hiện tại; chưa mở rộng sang tăng LED hoặc nới ngưỡng HR. Chưa thể gọi phần đo cổ tay hoặc nhánh5 hoàn tất.
