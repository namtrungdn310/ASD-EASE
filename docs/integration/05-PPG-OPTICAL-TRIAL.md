# Thử cấu hình quang MAX30102

Ngày2026-11-06. HR cổ tay chưa đạt sau khi thử mặt ngoài, mặt trong và che sáng. Không kết luận module hỏng, tiếp xúc chắc chắn sai hoặc thuật toán đã tối ưu. Chưa có HR tham chiếu.

## Phép thử hiện tại

Bản hiện tại0.3.10 có baseline và env thử `esp32s3_ppg_led10` tự báo `0.3.10-led10`. Bản thử chỉ khác baseline cùng phiên bản ở RED/IR LED0x1F (~6,2mA)→0x32 (~10mA). Dòng danh định không phải phép đo dòng thật của module; hãng lưu ý sai lệch giữa các linh kiện.

Cả hai bản0.3.10 dùng ADC4096nA/18bit, pulse411µs, chip200Hz/averaging4/FIFO50Hz. Bộ xử lý HR hai kênh được mô tả tại [khôi phục cảm biến](05-SENSOR-RECOVERY.md). Không thay GPIO, credential, schema1.1 hoặc luồng ESP→MQTT→backend→WebSocket. LED cao hơn không tự chứng minh tín hiệu hoặc HR chính xác hơn. Khi so ảnh hưởng LED, so hai env cùng phiên bản; không so0.3.8-led10 với0.3.10 mặc định rồi quy toàn bộ khác biệt cho LED.

Env mặc định vẫn `esp32s3_supermini`, dòng6,2mA. Lệnh chạy web không nạp lại firmware. Chạy lệnh upload bình thường sẽ quay về bản mặc định; luôn xem firmware_version để biết board đang dùng bản nào. Sau reboot phiên AUTO đổi theo boot, không nối timestamp0 vào phiên cũ.

## Kiểm tra và nạp

Từ root repo, đóng Serial monitor/capture trước khi upload:

```powershell
$env:CXX = 'C:\msys64\ucrt64\bin\g++.exe' # Chỉ ví dụ đường compiler trên máy Trung
.\.venv\Scripts\python.exe scripts/check_sensor_drivers.py --ppg-led10
.\.venv\Scripts\python.exe -m platformio run -d ai/edge_firmware -e esp32s3_ppg_led10
.\.venv\Scripts\python.exe -m platformio run -d ai/edge_firmware -e esp32s3_ppg_led10 -t upload --upload-port COM7
```

Máy khác tự dùng đường Python/compiler/COM thực tế. Chưa có board vẫn chạy test ngoại vi giả; không ghi hardware PASS từ test này.

Quay về baseline khi thử không cải thiện hoặc cần đối chiếu:

```powershell
.\.venv\Scripts\python.exe -m platformio run -d ai/edge_firmware -e esp32s3_supermini -t upload --upload-port COM7
```

## Cách đối chiếu

Đặt cùng vị trí cổ tay, giữ lực tiếp xúc và điều kiện ánh sáng tương tự. Chờ qua thời gian ổn định/đủ cửa sổ trước khi so. Thu35s qua `scripts/capture_ppg_trace.py`; Dashboard vẫn nhận MQTT, USB chỉ chẩn đoán. Ghi frame HR/IMU thật qua WS, clip/I2C/gap/discard/contact restart, tốc độ mẫu theo counter, bộ nhớ và thời gian xử lý. Dữ liệu người thật chỉ lưu local bị Git bỏ qua.

Nếu tiếp xúc hoặc mức nền thay đổi nhiều giữa hai lượt, không coi đây là phép so A/B kiểm soát đầy đủ. Có thêm số HR không đồng nghĩa đúng hơn; cần đối chiếu tham chiếu độc lập để đánh giá sai số. Không tự bật bản thử làm mặc định hoặc nâng dòng tiếp chỉ vì chưa ra số.

## Trạng thái

0.3.8-led10 đã build/nạp COM7/hash verified11,344s. Sau Trung xác nhận đặt lại cổ tay/che sáng: thu1.753 mẫu/35s, khoảng20ms, không trace drop/thời gian lùi. WS30 frame DEVICE/30 IMU,0 HR. IR174966..175603/RED94449..94972, không clip; contact/settled giữ1 và restarts giữ34. Counter io/clip0, overflow/gaps32/discard63 từ startup không tăng trong lượt. LoopGap/pollMax25ms, xử lý HR tối đa2,571ms. Dòng cao hơn tăng DC nhưng lượt này chưa cho thấy HR tốt hơn; không kết luận lợi ích từ một lần đo hoặc giả định dòng thực bằng10mA.

Replay tạm bỏ sàn biên độ trên file LED10mA vẫn0/24 cửa sổ đạt chu kỳ (tương quan8s tối đa khoảng0,533); không đổi firmware theo phép replay. Đã đưa board về0.3.8 baseline/hash verified11,388s trước khi phát triển0.3.9. Raw/log/plot chỉ lưu local bị Git bỏ qua.

Native cả hai bản0.3.9:71 ca HR,49 ca driver,12 snapshot/schema đạt;0/2400 cửa sổ benchmark chỉ nhiễu được chấp nhận. Build4 env đạt; chưa đo0.3.9-led10, không tự động nạp nó. Mặc định vẫn6,2mA, chưa nghiệm thu HR cổ tay và chưa có CI mới.

## Nguồn

[MAX30102 datasheet, bảng8/trang20](https://www.analog.com/media/en/technical-documentation/data-sheets/MAX30102.pdf): thanh ghi LED1_PA/LED2_PA điều chỉnh dòng; mã0x1F danh định6,2mA,0x3F danh định12,6mA. Mã0x32 được chọn làm mức thử khoảng10mA giữa hai mức này, không phải mức tối ưu hãng bảo đảm cho cổ tay.
