# Chuỗi đo firmware 0.3.2

Đây là mốc0.3.2 trước khi đo board. **Bản hiện tại0.3.10** có profile6515/ID0x74, phục hồi FIFO PPG, chip200Hz/averaging4/FIFO50Hz, contact hysteresis và HR8s/4s hai kênh có xác nhận. Đã nạp/đo board nhưng HR cổ tay chưa đạt; xem [bằng chứng và hành vi mới](../integration/05-SENSOR-RECOVERY.md). Không dùng giới hạn ID0x68, rollover tắt hoặc trung vị/EMA HR của mốc này để mô tả bản đang chạy.

Cập nhật 2026-11-06. Đây là cấu hình phát triển đã kiểm thử phần mềm, chưa phải tuyên bố độ chính xác trên cổ tay. Yêu cầu của Trung là tối ưu code; việc hoàn thiện vỏ không chặn triển khai phần mềm.

## Phần giữ nguyên

- MAX30102 SDA8/SCL9, MPU6050 SDA5/SCL11, GSR ADC1/GPIO7; nguồn đã xác nhận trước là 3V3.
- Acquisition profile danh định 50/50/20 Hz, window1000 ms. Telemetry1.1, sáu topic MQTT, control1.0, phiên tự động và cách chạy `npm run dev` giữ nguyên.
- Telemetry vẫn là snapshot mỗi giây, không thay raw theo lô của nhánh6/7. Các mẫu xử lý cục bộ ở bản này chưa được lưu đầy đủ để train.
- `signal_quality=0` giữ nghĩa chưa có bộ ước lượng; không dựng phần trăm chất lượng từ trạng thái driver.

## PPG/MAX30102

| Tham số | Giá trị và lý do |
|---|---|
| Chip/rate FIFO | 100 Hz, average2 → 50 Hz danh định; không tăng rate khi backend/profile chưa đổi |
| LED/ADC | 0x1F, hai kênh đỏ/IR, 411µs/18bit, 4096nA; chưa tự tăng LED để vượt ngưỡng |
| FIFO | Đọc trực tiếp phần cứng; tối đa31 mẫu/lượt, mỗi giao dịch tối đa30 byte; tránh ring SparkFun4 phần tử |
| Kiểm tra cấu hình | Đọc lại average, rollover, mode, rate, pulse width, ADC range và LED current; khác dự kiến thì báo lỗi |
| Mất/tràn/lỗi | Kiểm tra overflow trước pop; reset thuật toán khi lỗi lô/nguồn/gap; không nối RR qua khoảng mất |
| Ngưng sinh mẫu | Quá500ms không có mẫu mới → ngừng coi driver sẵn sàng, thử khởi tạo lại sau3s |
| Lọc | Tách DC cũ; Butterworth bậc2/cutoff4Hz thay2,5Hz để giảm suy hao fundamental3,33Hz ở200bpm |
| HR | Giới hạn RR suy từ40..200bpm, không dùng chặn cố định360/400ms và luật loại nửa RR trước |
| Độ trễ hiển thị | Trung vị5 BPM + EMA0,35 theo nhịp; 90% bước của riêng EMA khoảng6 nhịp, chưa tính trung vị |
| Hợp lệ | Cần đủ nhịp, tiếp xúc theo ngưỡng, không clipping/gap và nhịp hợp lệ còn mới; chưa phải chứng nhận HR đúng |

Các giá trị lọc mới là điểm xuất phát có test tín hiệu tổng hợp, chưa chứng minh tốt hơn trên mọi dạng sóng/cổ tay. Bỏ luật half-RR tránh khóa khi nhịp tăng nhưng làm thay đổi rủi ro đếm đỉnh phụ; cần so với tín hiệu tham chiếu, không tuyên bố loại hết dicrotic notch hoặc nhiễu chuyển động. Ngưỡng IR50000 và AC50 vẫn cần kiểm tra sau khi nạp.

`rawHeartRate` giữ tên tương thích nhưng là trung bình BPM gần nhất, không phải chuỗi rawRR. SpO2 vẫn chỉ debug; công thức/clamp không biến nó thành kết quả đã kiểm chứng. Bỏ các mảng PPG không được dùng để giảm RAM.

## IMU/MPU6050

- Chỉ nhận WHO_AM_I=0x68 của profile6050. Mã0x70/0x71/0x98 hoặc không đọc được ID không được âm thầm dùng chung hệ số/nhiệt độ/FIFO. Nếu module đang dùng trả mã khác, lấy log để bổ sung profile đúng; không nới kiểm tra chỉ để có số.
- Reset/wake theo state machine, không chờ `delay(50/15)` trong nhánh phục hồi. Các giao dịch I2C vẫn đồng bộ và có timeout50ms, chưa gọi toàn bộ driver là bất đồng bộ.
- DLPF5 khoảng10Hz, SMPLRT_DIV19 →50Hz; đọc lại thanh ghi, dùng đúng cấu hình thang đo. Băng thông thấp hơn Nyquist25Hz giảm nguy cơ alias nhưng không bảo đảm loại hết alias vì bộ lọc có độ dốc hữu hạn.
- FIFO accel+temperature+gyro XYZ (`FIFO_EN=0xf8`), 14 byte/mẫu; đọc mọi mẫu của lô tối đa8 mẫu. Không nhân snapshot thành nhiều mẫu. Tràn/quá backlog/lỗi I2C thì bỏ lô và khởi tạo lại; không gửi lại dữ liệu cũ thành live.
- EMA mặc định1,0 vì chip đã lọc10Hz; tránh tầng EMA cũ cắt còn khoảng2,3Hz. Trục Y/Z chỉ đảo một lần. Gia tốc vẫn bao gồm trọng lực.
- Tự lấy lệch gyro một lần sau100 mẫu liên tục trong điều kiện gần đứng yên: norm gia tốc gần g, gyro nhỏ và phương sai thấp. Giữ yên vài giây sau bật hoặc khởi tạo lại cảm biến; khi chưa đủ điều kiện thì CALIBRATING, vector/score MQTT null. Không tự học lại trong chuyển động sau khi đã chốt offset; chỉ reconnect Wi-Fi không làm mất offset.
- Kiểm tra đứng yên chỉ là heuristic: quay đều chậm không thể luôn phân biệt với bias bằng IMU đơn lẻ. Ngưỡng100 mẫu/0,35m/s²/10°/s/độ lệch chuẩn là cấu hình kỹ thuật phát triển, chưa đo tối ưu. Không coi đây là hiệu chuẩn gia tốc sáu mặt hoặc bù drift nhiệt đầy đủ.
- `rawG*_deg` là sau đổi đơn vị/hệ trục, trước bù bias; `g*_deg` gửi Dashboard là sau bù bias rồi EMA. Giữ raw để còn phân tích đúng. Score motion-rms-v1 vẫn dùng sáu trục trước bù bias theo định nghĩa cũ.
- ADC/IMU chạm rail thì không công nhận số đo như bình thường. Khoảng đo ±2g/±250°/s vẫn có thể thiếu với cử động mạnh; chỉ đổi cùng profile, hệ số, giới hạn và kiểm thử.

## GSR

- Đặt rõ attenuation3 của ADC1 và lấy bộ đặc tính eFuse ESP32-S3 một lần. Dùng `esp_adc_cal_raw_to_voltage` đổi đúng mẫu raw đã lấy, không đọc một mẫu khác và không dùng `raw×3300/4095`.
- `gsr.raw` vẫn là trung bình8 lần ADC12bit trước EMA, làm tròn nguyên, 20Hz danh định. Không gọi burst8 lần là notch50Hz hoặc lấy mẫu đều160Hz.
- Khi không có bộ hiệu chuẩn eFuse được SDK chấp nhận: raw vẫn truyền được, không công bố mV/µS hợp lệ. Khi có eFuse, điện áp đã qua hiệu chuẩn chip; vẫn cần đo đối chiếu điện áp/module thật.
- ADC chạm4095 hoặc điện áp vượt vùng kỹ thuật150..3100mV thì báo trạng thái tương ứng, xóa baseline. Các mức này chưa chứng minh phát hiện đeo/hở/chập cho mọi vị trí biến trở.
- Baseline dùng mẫu điện áp trước EMA: bỏ1 giây đầu, cửa sổ5 giây, ít nhất80 mẫu, độ lệch chuẩn≤50mV. Không đủ hoặc nhiễu lớn thì chờ lại; gap>200ms làm bỏ cửa sổ đang học. Đây là baseline kỹ thuật, không phải hiệu chuẩn mạch sangµS.
- **Mặc định `GSR_CONDUCTANCE_CALIBRATED=false`: µS/điện trở/delta từ mô hình mạch chưa kiểm chứng không được gửi như hợp lệ.** Nội bộ dùng NaN cho số chưa biết; serializer chặn trường này nên MQTT `gsr.delta=null`, còn `gsr.raw` vẫn hiển thị. Không thay bằng0.
- Muốn bật mô hình điện dẫn phải xác minh module/biến trở và các hằng số bằng điện trở chuẩn, sau đó mới bật cờ và lưu bằng chứng. Không dùng công thức ví dụ Arduino10bit của hãng trực tiếp cho ESP12bit. Bỏ nhãn SCR tự động bằng ngưỡng2µS; chưa có detector phản ứng sinh lý.

## Thời gian và log

- Vòng đọc poll hai FIFO theo lịch mục tiêu10ms; GSR theo lịch50ms giữ pha. Khi lỡ slot không gọi ADC nhiều lần để giả bù mẫu. MQTT đếm IMU theo số mẫu FIFO mới, không đếm số lần gọi `read()`.
- Đồng hồ mẫu monotonic64bit, khoảng mẫu danh định theo FIFO. Neo lại khi lệch/gap lớn; xử lý millis32bit quay vòng. Chưa có timestamp cạnh INT chính xác hoặc đồng hồ chung giữa ba chip, chưa dùng RR cho HRV.
- Log định kỳ chạy task riêng ưu tiên thấp, stack6KiB, queue length1/latest-only. Task không gọi I2C, chỉ nhận snapshot copy; Serial chậm không buộc sensing chờ toàn bản log. Có thể bỏ log trung gian. Log khởi tạo/lỗi thưa vẫn có trong driver; ảnh hưởng thật và heap/stack cần đo.
- `[PPG-DAQ]` cho count, backlog/gap/overflow/I2C/clip và IR/RED/AC. `[IMU-DAQ]` cho count/gap/I2C/clip, trạng thái bù và offset. `lostMin` chỉ là cận dưới bộ đếm bão hòa31, không phải tổng mất chính xác. `n/ms` phải tính bằng chênh lệch trong cùng đoạn đo, loại giai đoạn startup/retry.
- Cách chạy hàng ngày và phiên tự động giữ nguyên. Nạp firmware sẽ reboot ESP, vì thế có boot/phiên tự động mới.

## Kiểm thử và giới hạn bằng chứng

`check_sensor_drivers.py` biên dịch chính các driver sản xuất và serializer, thay Wire/ADC/clock bằng fake. Kiểm tra dạng sin40/60/100/150/180/200bpm, bước60→120, lô4/8/16 mẫu, clipping/overflow, timestamp wrap, MPU cấu hình/bias/cache/lô/mã ID, ADC không có calibration và baseline nhiễu. Xuất10 gói SYNTHETIC từ snapshot driver qua serializer C++ và Pydantic runtime.

Fake SparkFun chỉ thay phần setup, fake ADC có đường quy đổi biết trước; các test này không chứng minh ghi thanh ghi/hiệu chuẩn eFuse thật đã chạy trên board. Test FIFO riêng28 ca và protocol/schema39 ca vẫn cần đạt. Có ba build: bản dùng header local, bản MQTT kiểm tra không secret và bản Serial-only kiểm tra không secret.

## Nguồn kỹ thuật

- [MAX30102 datasheet: FIFO/overflow/rate/LED](https://www.analog.com/media/en/technical-documentation/data-sheets/MAX30102.pdf).
- [TDK register map MPU6000/6050: divider, DLPF, FIFO, WHO_AM_I](https://invensense.tdk.com/wp-content/uploads/2015/02/MPU-6000-Register-Map1.pdf).
- [Espressif ADC S3/IDF4.4: calibration](https://docs.espressif.com/projects/esp-idf/en/v4.4/esp32s3/api-reference/peripherals/adc.html). Dùng API tương ứng SDK đang cài, không nâng sang API IDF5/6.
- [Seeed Grove GSR: hiệu chỉnh biến trở và đo điện trở](https://wiki.seeedstudio.com/Grove-GSR_Sensor/).
