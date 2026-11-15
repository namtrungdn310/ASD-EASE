# Cổ tay: phục hồi I2C, mức đo và mô phỏng

Cập nhật 2026-11-07. Đợt thử đã có đủ ba mức LED, lượt lặp10mA và cấu hình400Hz/avg8: **chưa có cấu hình cổ tay cho kết quả đủ lặp lại**. Lượt0.3.15 nhận đủ GSR/IMU nhưng0/39 HR, không lỗi đọc/gap. Đã quay về **0.3.13-led10, 200Hz/avg4/LED10mA** làm đối chiếu; không chọn đây là mức tối ưu. [Kết quả cuối và phần còn thiếu](05-WRIST-SAMPLING-TRIAL.md). Cụm mạch giữ cố định theo yêu cầu Trung; HR cổ tay chưa nghiệm thu.

**Làm rõ cách đặt từ Trung,2026-11-07:** lật cả đế tròn, áp nhẹ mặt có ô quang của MAX30102 vào da; toàn bộ mạch xanh nằm trong phạm vi cổ tay, ESP32/MPU nhô ra ngoài một phần. Không dùng ngón tay ép xuống. Đây là điều kiện thử cần giữ; giả thuyết hai mạch kia kê hở cảm biến chưa có bằng chứng, không dùng làm kết luận hoặc yêu cầu sửa gá. Cổng IR/contact và motion đã cho phép trong các lượt thu nhưng không đo trực tiếp lực/đường quang; vẫn cần phân tích tín hiệu và điều kiện lọc, chưa quy riêng nguyên nhân cho cơ khí.

## 1. Sửa phục hồi I2C

`processing/ppg_init.h` thay chuỗi `SparkFun.begin/setup` trong driver MAX30102 bằng các bước: đọc PART_ID → reset → kiểm reset qua nhiều vòng → ghi từng thanh ghi → đọc lại → xóa cờ trạng thái. Mỗi lần gọi chỉ làm một giao dịch, lỗi thì dừng ngay; không tiếp tục hàng chục giao dịch đều timeout.

- Giữ bus do main khởi tạo, không gọi lại `Wire.begin()` trong driver. Không thay chân GPIO/clock/timeout của bus hoặc cấu hình cảm biến khác.
- Reset bị kẹt có deadline 100 ms nhưng không chặn chờ 100 ms; các lần poll tách theo sensing. Mỗi giao dịch vẫn phụ thuộc timeout Wire 50 ms và nền tảng thực tế; không gọi đây là I/O hoàn toàn bất đồng bộ.
- Retry sau lỗi vẫn 3 giây. Thời gian một lần init gồm nhiều vòng không phải thời gian chặn vòng lặp. `stepMaxUs` ghi riêng thời gian một bước.
- Ghi đúng thanh ghi, số byte và mã Wire. `recoveryCause` giữ lỗi mở đầu kể cả các lần thử sau tiếp tục lỗi. Không còn chỉ dựa vào `ProbeFailed` chung chung.
- `begin()` có thể trả UNAVAILABLE khi đang khởi tạo, giống driver IMU; dùng `isInitializing()` để phân biệt với lỗi thực. Không tính pending là một lần thất bại.

## 2. Cấu hình quang để so sánh cổ tay

Giữ chip 200 Hz, averaging 4 → FIFO 50 Hz, pulse 411 µs, ADC 4096 nA và cùng bộ HR hybrid đã chốt. Chỉ thay một mức LED mỗi lượt đo:

| Env PlatformIO | RED/IR danh định | Firmware | Vai trò |
|---|---:|---|---|
| `esp32s3_supermini` | 6,2 mA (`0x1F`) | `0.3.13` | Mốc so sánh, giữ mặc định |
| `esp32s3_ppg_led10` | 10 mA (`0x32`) | `0.3.13-led10` | Thử tăng tín hiệu phản xạ |
| `esp32s3_wrist_12ma` | 12,4 mA (`0x3E`) | `0.3.13-wrist12` | Mức thử tiếp theo nếu 10 mA chưa đủ |

Đây là dòng danh định theo register, chưa đo dòng thực trên module. Không tự tăng LED vô hạn khi không có HR; số DC cao cũng không chứng minh sóng mạch rõ. Có cờ quá sáng ALC_OVF hoặc mẫu chạm rail thì HR bị loại và thu lại lịch sử, không gọi lại init I2C chỉ vì lỗi quang.

Chưa chọn mức LED tối ưu từ mô phỏng. Phải so dữ liệu thật ở cùng vị trí/độ tiếp xúc, kiểm clipping/ALC, số cửa sổ hợp lệ và đối chiếu nhịp tham chiếu nếu có. Không đổi LED và thuật toán cùng lúc rồi quy kết cải thiện cho một yếu tố.

## 3. Chẩn đoán và cổng chuyển động

Log `[PPG-WRIST]` phân biệt: thiếu phản xạ, đang ổn định, đang thu cửa sổ, dao động yếu, chưa tách được nhịp, quá sáng, có HR hợp lệ. Có thêm trạng thái IMU chưa sẵn sàng/đang chuyển động/đang thu lại cửa sổ.

`acDcPct` là biên độ RMS tương đương chia DC, chỉ để đối chiếu; không gọi là PI đã hiệu chuẩn hoặc độ chính xác. Mốc 0,02% dùng nhãn dao động yếu, **không hạ ngưỡng chấp nhận HR**.

`WristMotionGuard` mặc định bật trong main:

- Cần IMU hợp lệ, đã lấy gyro bias, score hợp lệ và tuổi không quá 100 ms.
- Score `motion-rms-v1` từ 0,12 trở lên chặn HR. Ngưỡng này là cấu hình kỹ thuật phát triển, chưa được hiệu chuẩn trên người.
- Khi bắt đầu/dừng chuyển động hoặc dữ liệu IMU bị gián đoạn, reset lịch sử HR/generation. Sau khi yên cần cửa sổ sạch 10 giây; bộ HR vẫn cần tự thu đủ mẫu và xác nhận. Mất HR không được giữ số cũ để bù khoảng này.
- GSR/IMU và telemetry vẫn gửi bình thường, chỉ HR=null khi chưa đủ điều kiện. Đây là chế độ đo HR lúc nghỉ, chưa phải bù chuyển động hoặc ước tính HR khi vận động.

IMU không đo được mọi thay đổi tiếp xúc/ánh sáng. Nhiễu quang tuần hoàn giống nhịp nhưng IMU đứng yên vẫn có thể đánh lừa bộ HR; mô phỏng bên dưới giữ rõ ca này.

## 4. Mô phỏng riêng cổ tay

Chạy `scripts/simulate_wrist_ppg.py`. Dữ liệu chỉ ở host/local, gắn `SYNTHETIC`, không publish MQTT và không trình bày là số đo ESP. Harness chạy **driver MAX30102, bộ quality C++ và cổng chuyển động thực**, dùng I2C/clock giả, mô hình worker trễ 150 ms. Không dùng thời gian host thay thời gian CPU ESP.

10 tình huống: ổn định; ghép quang lỏng; phản xạ rất yếu; sóng yếu dù DC cao; không tiếp xúc; ánh sáng lọt/ALC; trượt tiếp xúc; nhiễu do chuyển động không có mạch; nhiễu quang tuần hoàn khi IMU yên; ADC chạm rail. Sinh ở 200 Hz rồi trung bình 4 mẫu để tạo FIFO 50 Hz.

Hệ số ghép quang, nhiễu và ALC là fixture mô phỏng hiện tượng, **không phải mô hình quang học đã hiệu chuẩn**. Không quy thành khoảng cách mm, lực ép hoặc dự đoán độ chính xác ngoài đời. Nhịp gốc dùng chấm kết quả, không đưa vào thuật toán.

- Seed 601 và seed 701 riêng: các kiểm tra kỹ thuật đạt. Ca ổn định/ghép lỏng nhận nhịp 80 bpm; ca không tiếp xúc/chạm rail/chuyển động bị chặn; ca ánh sáng quá mức phải loại HR ở đoạn ALC.
- **Giới hạn còn mở:** nhiễu quang tuần hoàn 80 bpm, không có mạch nhưng IMU yên, vẫn bị nhận thành HR. Report gắn `KNOWN_LIMITATION_FALSE_POSITIVE`, không tính thành đạt độ chính xác. Không điều chỉnh policy chỉ để làm đẹp fixture này.
- Ngưỡng chuyển động thêm ở bước này; chưa đánh giá trên dữ liệu người có IMU đồng bộ/nhịp tham chiếu. Bộ benchmark BIDMC ở bước 3 không có IMU tương ứng nên không dùng để tuyên bố cổng mới đã được kiểm định.

## 5. Thứ tự thử thực tế

1. Build/kiểm driver, nạp 0.3.13 mặc định để xác minh phục hồi và luồng MQTT→BE→WS trước. Không yêu cầu người dùng giữ tay trong lúc sửa/build.
2. Đo cổ tay nghỉ 45 giây bằng mức 6,2 mA, ghi trace/log/WS và cổng chuyển động; không ép cảm biến mạnh để đổi điều kiện đo.
3. Khi có kết quả, mới thử 10 mA cùng vị trí; 12,4 mA chỉ là mức tiếp theo có kiểm soát. Chọn theo bằng chứng; chưa có nhịp tham chiếu thì chỉ kết luận khả năng có kết quả và chất lượng tín hiệu, chưa kết luận sai số.

Hướng dẫn của hãng: [MAX30102 datasheet](https://www.analog.com/media/en/technical-documentation/data-sheets/MAX30102.pdf), [tích hợp quang/cơ cho cổ tay](https://www.analog.com/en/resources/technical-articles/guidelines-for-the-optomechanical-integration-of-heartrate-monitors-in-wearable-wrist-devices.html). Hãng nhấn mạnh ghép quang với da và hạn chế ánh sáng đi thẳng giữa LED/photodiode. Tiếp xúc nhẹ ổn định khác với một khe hở thay đổi liên tục; code không thể tự bù mọi tín hiệu quang đã mất.

## Kết quả triển khai

- PASS 6 env: mặc định, network-check, serial-check, LED10, baseline tắt quality và wrist12.4. Bản mặc định RAM tĩnh 79.236/327.680 byte, flash 944.693/1.310.720 byte. Log local: `ppg-0313-build-final.log`.
- PASS 4 tổ hợp header, 81 ca driver/12 snapshot qua serializer và schema ở cả 3 mức LED; 76 ca HR; 34 ca FIFO; 8 ca tích hợp hybrid; 10 ca selector; 39 ca protocol. Kiểm lại 76 ca công cụ offline và 95 ca parity Python/C++ đạt. Các ca lỗi gồm reset kẹt, sai PART_ID, write timeout, config short-read, retry-backoff, ALC, IMU cũ/NaN/mất clock, chuyển động và thu lại cửa sổ.
- Mô phỏng 601/701 chạy bằng mã cuối, report có hash nguồn: `backend/storage/local/ppg-wrist-simulation-601.json` và `...-701.json`. Mỗi bộ 10 tình huống, giữ rõ 1 giới hạn nhận nhầm nhiễu quang tuần hoàn; không coi toàn bộ là đạt độ chính xác.
- Lượt upload đầu thất bại vì mất COM7. Sau khi Trung cắm lại USB, upload thành công, hash verified, tổng 22,026 giây. Không thay dây cảm biến. Log local: `ppg-0313-upload-retry.log`.
- Giữ 6 tên check CI; chưa chạy CI từ xa/commit/push cho lượt này. Hai file schema người dùng đang sửa giữ nguyên hash. Nhánh 5 và HR cổ tay chưa nghiệm thu.

## Kiểm tra board sau nạp, trước khi áp da

Trace `ppg-20261106-212852-22f82f.csv/.json`: 45 giây, 2.251 mẫu PPG, khoảng cách tối đa 20 ms, không rơi trace. Không có tiếp xúc quang (IR khoảng 419–430), HR trống đúng điều kiện lượt này.

- Init 1 lần thành công, không thất bại; tổng thời gian trải qua các bước 148 ms, bước lâu nhất 1.438 µs. Không so 148 ms trải qua nhiều vòng với thời gian chặn một vòng lặp.
- I2C/overflow/gap/clip/discarded đều 0 và không tăng trong lượt; IMU cũng không lỗi/gap/overflow, đã lấy bias. Lỗi I2C trước đây chưa tái hiện trong lượt này nên chưa coi là đã xử lý mọi nguyên nhân mất bus hoặc kiểm chứng giới hạn timeout vật lý.
- Loop gap tối đa 10 ms; PPG poll gap tối đa 19 ms; heap thấp nhất 149.272 byte. Self-test hybrid đạt, stack còn 3.140 byte, chưa có cửa sổ đo người gửi worker.
- Cổng chuyển động `Still`, allowHr=1, score khoảng 0,0585–0,0587; không chặn vì dữ liệu IMU cũ/thiếu. Điều này chỉ mở cổng, HR vẫn phải qua kiểm tra quang và thuật toán.
- WS thực nhận 39 frame DEVICE/ESP32-001, firmware0.3.13, cùng phiên AUTO theo boot mới; đủ 39 GSR và 39 vector IMU. File `ppg-0313-runtime-ws.json` giữ local, không đưa dữ liệu thật/secret lên Git.

## Cổ tay nhẹ ở mức 6,2 mA

Sau xác nhận của Trung, thu `ppg-20261106-233953-e1715c.csv/.json`: 45 giây, 2.252 mẫu PPG, max interval20ms, không rơi trace. Đã báo thả tay ngay sau lượt.

- Contact/settled giữ1, restarts31→31; không lỗi I2C/overflow/gap/clip/ALC, init chỉ một lần thành công. Bước init tối đa1.375µs, loop gap11→12ms.
- Cổng chuyển động `Still`, allowHr=1; score0,0090→0,0012. IMU clip12 có từ trước lượt, không tăng; không lỗi/gap/overflow trong lượt. Không phải bị cổng chuyển động chặn HR.
- Cả45 dòng log HR valid=0; worker completed10→54, accepted giữ0. Nhãn quang `CHUA_TACH_DUOC_NHIP` cả lượt. Có phản xạ ổn định nhưng chưa nhận được nhịp đủ điều kiện; không hạ ngưỡng để ép có số.
- MQTT trong lượt chưa kết nối, error32774 (`ESP_ERR_ESP_TLS_CONNECTION_TIMEOUT` theo header framework cài local); WS0 frame DEVICE, không được ghi thành0/39 HR. File `ppg-0313-wrist62-20261106-234035-ws.json` giữ bằng chứng không có gói, không chứng minh HR bị mất ở frontend.
- Sau đó mạng tự khôi phục: `ppg-20261106-234157-f67826.csv/.json`20s có1.000 mẫu/max20ms; logmqtt=1/sync=1. WS kiểm15s nhận13 frame0.3.13, đủ13 GSR/13 IMU, không reload browser hoặc đổi auth/firewall. Mã lỗi cũ vẫn nằm trong counter chẩn đoán, không có nghĩa kết nối hiện tại còn lỗi.

## Chuẩn bị mức 10 mA

Đã nạp `esp32s3_ppg_led10`, firmware `0.3.13-led10`, hash verified23,422s; log `ppg-0313-led10-upload.log`. Giữ cùng tần số/averaging/ADC/thuật toán/guard; chỉ đổi RED/IR từ0x1F sang0x32. Chưa kết luận mức10mA tốt hơn.

Kiểm trước áp da: `ppg-20261106-234443-dae4f6.csv/.json`20s có1.001 mẫu, max20ms, không rơi trace; I2C/overflow/gap/clip/ALC đều0. Init1 lần thành công147ms qua nhiều vòng, bước tối đa1.439µs, loop gap11ms. Self-test hybrid đạt, IMU đã lấy bias và cổng chuyển động mở khi yên; chưa có cửa sổ quang đo người. WS15s nhận14 frame `0.3.13-led10`, đủ GSR/IMU, mqtt/sync1 và error0. File `ppg-0313-led10-health-ws.json` giữ local.

## Kết quả cổ tay nhẹ ở mức 10 mA

Sau xác nhận của Trung, thu `ppg-20261106-234815-b0224f.csv/.json`:45s/2.252 mẫu, max20ms, không rơi trace. Đã báo thả tay ngay khi thu xong.

- I2C/overflow/gap/clip/ALC/discarded đều0; init chỉ1 lần thành công. Contact/settled1, restarts103→103; guard `Still`, allowHr1, score0,0003→0,0001. IMU clip11 có từ trước lượt, giữ nguyên, không lỗi/gap/overflow trong lượt.
- WS nhận39 frame `0.3.13-led10`, đủ39 GSR/IMU, trong đó15 frame HR79–85,1bpm. 21 frame đầu chưa HR; đoạn sau có kết quả nhưng vẫn có khoảng trống. File `ppg-0313-wrist10-20261106-234856-ws.json` giữ local. Không coi mức này đã đo liên tục ổn định.
- 45 lần chụp Serial:18 lần valid,27 lần chưa HR; nguồn17 IR baseline,1 RED baseline, không có fallback được chọn ở các lần log này. Worker completed5→49, accepted0→12, queue không ghi đè, max wall164.147µs; các bộ đếm không đồng nghĩa số frame WebSocket.
- IR181.243–184.364, RED110.588–111.067; log biên độ AC/DC khoảng0,029–0,032% ở đầu/cuối. Dao động nhỏ hơn lượt6,2mA nhưng có đoạn tuần hoàn rõ hơn. Không chọn cấu hình chỉ dựa DC cao hoặc biên độ AC lớn.
- MQTT/sync1 cả lượt, error0/fail0/drop0. Loop gap13ms; bước init tối đa1.439µs; heap thấp nhất146.224 byte. Chưa gặp lại lỗi I2C trong lượt này, chưa thay bài tái hiện lỗi bus vật lý.

Replay `ppg-0313-wrist-led-replay.json` dùng cùng policy, từ giây13,32 cửa sổ/trace:6,2mA baseline/hybrid0/32;10mA baseline16/32, hybrid18/32, quality riêng11/32. Không có nhịp tham chiếu nên MAE=null. Replay khởi tạo lại bộ lọc/lịch đánh giá từ đầu trace, không chứng minh khớp từng mốc thời gian của board hoặc thay số frame WS thật. Chưa đủ để quy cải thiện chỉ cho dòng LED vì tiếp xúc giữa các lượt không được đo lực/vị trí chính xác.

## Chuẩn bị mức 12,4 mA

Đã nạp env `esp32s3_wrist_12ma`, firmware `0.3.13-wrist12`, hash verified12,489s, log `ppg-0313-wrist12-upload.log`. Chỉ đổi RED/IR0x32→0x3E, giữ thuật toán/cấu hình còn lại.

Kiểm trước áp da `ppg-20261106-235150-7b5a84.csv/.json`:20s/1.001 mẫu/max20ms, không rơi trace; I2C/overflow/gap/clip/ALC đều0, init1 lần thành công148ms qua các bước, bước tối đa975µs. Loop gap12ms, heap thấp nhất149.828 byte; IMU đã lấy bias, guardStill/allowHr1. WS15s nhận14 frame `0.3.13-wrist12`, đủ GSR/IMU, mqtt/sync1/error0. File `ppg-0313-wrist12-health-ws.json` giữ local.

## Kết quả cổ tay nhẹ ở mức 12,4 mA — 2026-11-07

Sau xác nhận của Trung, thu `ppg-20261107-001619-3698d9.csv/.json`:45s/2.251 mẫu/max20ms, không rơi trace. Đã báo thả tay ngay sau lượt.

- Contact/settled giữ1, restarts259→259; guardStill/allowHr1, score0,0085→0,0036. IMU clip22 có từ trước lượt, không tăng; không lỗi/gap/overflow trong lượt.
- PPG I2C/overflow/gap/clip/ALC/discarded đều0; chỉ1 init thành công, bước tối đa975µs. Loop gap12→13ms. MQTT/sync1/error0 cả lượt; không lỗi publish/drop. HR không bị chặn vì mất mạng hoặc chuyển động.
- WS39 frame `0.3.13-wrist12`, đủ39 GSR/IMU nhưng0 HR. Cả45 dòng Serial valid0; worker completed11→55, accepted giữ0; max wall172.200µs, queue không ghi đè. File `ppg-0313-wrist124-20261107-001700-ws.json` giữ local.
- IR236.378–237.660 (đỉnh khoảng90,7% thang18bit262.143), RED135.723–136.358; chưa chạm rail/ALC. Nền tăng so với10mA nhưng chưa có nhịp đủ điều kiện; không suy rằng tăng LED luôn tăng chất lượng.
- Replay cùng cách chấm từ giây13 cho32 cửa sổ: baseline/quality/hybrid đều0/32, không có tham chiếu. Report `ppg-0313-wrist-led-replay.json` đã bổ sung mức12,4mA; không dùng replay thay số frame WS thực.

## So sánh sơ bộ và kiểm tra lặp lại

| Mức | Thu PPG45s | Serial có HR | WebSocket trong lượt | Replay hybrid sau giây13 |
|---|---|---|---|---|
| 6,2mA | 2.252 mẫu, liên tục | 0/45 lần log | Không có frame do MQTT timeout; không chấm số HR qua WS | 0/32 |
| 10mA | 2.252 mẫu, liên tục | 18/45 lần log | 15/39 frame có HR79–85,1bpm | 18/32 |
| 12,4mA | 2.251 mẫu, liên tục | 0/45 lần log | 0/39 frame có HR | 0/32 |
| 10mA lặp | 2.252 mẫu, liên tục | 0/45 lần log | 0/39 frame có HR | Chưa replay |
| 10mA,400Hz/avg8,0.3.15 | 2.246 mẫu, mốcước lượng16–21ms | 0/45 lần log | 0/39 frame có HR | Chưa replay |

Ba mẫu số là các cách quan sát khác nhau, không gộp thành accuracy. Tiếp xúc giữa các lượt không đo chính xác lực/vị trí, chưa có tham chiếu và chưa lặp lại đủ; chỉ coi10mA là **ứng viên tạm để kiểm tra tiếp**.

Đã nạp lại envLED10, firmware0.3.13-led10, hash verified11,938s; log `ppg-0313-led10-restore-upload.log`. Kiểm sau nạp `ppg-20261107-002044-f547e2.csv/.json`:20s/1.001 mẫu/max20ms, không rơi trace, I2C/overflow/gap/clip/ALC đều0; init1 lần thành công147ms qua các bước, stepMax1.435µs. Loop gap14ms, MQTT/sync1/error0, WS14 frame đủ GSR/IMU. File `ppg-0313-led10-restore-health-ws.json` giữ local.

Lượt kiểm sau nạp có tiếp xúc ở đầu đoạn (logHR72,8bpm), sau đó đầu đo hở; chưa được xác nhận vị trí nên **không tính là lượt đo lặp cổ tay đã nghiệm thu**.

## Kết quả lượt lặp10mA — 2026-11-07

Sau xác nhận đặt nhẹ vào cùng vị trí cổ tay, thu `ppg-20261107-002440-a48381.csv/.json`:45s/2.252 mẫu/max20ms, không rơi trace. Đã báo người dùng thả tay ngay sau lượt.

- I2C/overflow/gap/clip/ALC/discarded đều0, chỉ1 init thành công; loop gap14ms. Contact/settled1, restarts42→42. GuardStill/allowHr1, score0,0047→0,0008; IMU clip4 có từ trước lượt và không tăng, không lỗi/gap/overflow trong lượt.
- WS39 frame0.3.13-led10, đủ39 GSR/IMU, **0 HR**; mqtt/sync1/error0/fail0/drop0. File `ppg-0313-wrist10-repeat-20261107-002521-ws.json` giữ local. Cả45 dòng Serial valid0; worker completed50→94, accepted giữ27 (các lần nhận trước lượt), không nhận thêm trong lượt.
- IR179.232–181.176, RED102.213–103.063. Nhãn42 lần `CHUA_TACH_DUOC_NHIP`,3 lần `DAO_DONG_YEU`; không phải gói mạng bị mất hoặc cổng chuyển động chặn HR.

**Kết luận:** chưa có cấu hình dòng LED nào cho kết quả cổ tay đủ lặp lại. Không chọn10mA là tối ưu từ một lượt có số; không tăng LED thêm hoặc hạ ngưỡng. [Bản400Hz/avg8/0.3.15](05-WRIST-SAMPLING-TRIAL.md) cũng0/39 HR trong lượt đo người. Đã quay về200Hz/avg4/10mA, kiểm lại truyền dữ liệu sau nạp đạt. Bản0.3.15 sửa lỗi trôi đồng hồ được giữ riêng trong repo, chưa chọn làm mặc định. Cần nhịp tham chiếu đồng bộ để đánh giá thuật toán, chưa kết luận đã tối ưu chỉ bằng code.
