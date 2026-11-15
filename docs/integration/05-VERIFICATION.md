# Kiểm tra nhánh 5

## Kết quả đo cổ tay0.3.15 và khôi phục đối chiếu — 2026-11-07

**HR cổ tay chưa đạt:** bản400Hz/avg8/LED10mA sau xác nhận thu45s/2.246 mẫu, timestamp16–21ms, không lỗi I2C/gap/overflow/clip/ALC. Contact/guard ổn định, WS39 frame đủ GSR/IMU nhưng0 HR. Đã quay về0.3.13-led10/200Hz/avg4/hash verified11,556s; kiểm20s/1.000 mẫu và14 frame WS GSR/IMU đạt. Không chọn cấu hình tối ưu hoặc nới quality gate khi chưa có tham chiếu; phần code/build đạt không thay nghiệm thu HR. [Bằng chứng và giới hạn](05-WRIST-SAMPLING-TRIAL.md).

## Bản thử400Hz/avg8 và đồng hồ PPG — 2026-11-07

Lượt lặp10mA/200Hz0/39 HR dù sensing/contact/guard ổn định. Đã thêm profile400Hz/avg8, giữLED10mA/FIFO50Hz/thuật toán. Bản0.3.14 kiểm đầu có bước nhảy82ms, đã thay bằng0.3.15 theo dõi trôi nhỏ riêngPPG400Hz, có kiểm native tái hiện gap giả và phát hiện khoảng dừng thật.

PASS7 env/4 header,89 ca driver/12 snapshot ở4 profile,76 HR/34 FIFO/8 hybrid/10 selector/95 parity; mô phỏng701/801/809 giữ rõ1 ca nhận nhầm còn mở. Nạp0.3.15 COM7/hash verified12,103s. Kiểm55s chưa áp da:2.746 mẫu, timestamp17–21ms, không gap/I2C/overflow; WS49 frame đúngversion, đủGSR/IMU, guard mở. Chờ xác nhận đo người, chưa nghiệm thu HR cổ tay hoặc CI từ xa. [Chi tiết và giới hạn](05-WRIST-SAMPLING-TRIAL.md).

## Đủ ba mức LED, chờ kiểm tra lặp — 2026-11-07

Lượt cổ tay12,4mA45s/2.251 mẫu/max20ms: không lỗi/gap/clip/ALC, contact/guard ổn định, WS đủ39 GSR/IMU nhưng0 HR. Replay baseline/quality/hybrid0/32. Đã quay về0.3.13-led10/hash verified11,938s; kiểm sau nạp20s/1.001 mẫu và14 frame WS GSR/IMU đạt. Chờ xác nhận đo lặp10mA; chưa chọn mức tối ưu từ một lượt15/39 HR trước đó. [So sánh và bằng chứng](05-WRIST-PROFILE.md).

## Phục hồi và chế độ cổ tay 0.3.13 — 2026-11-06

Lượt10mA đã đo45s/2.252 mẫu/max20ms, không lỗi I2C/gap/clip/ALC, contact/guard ổn định. WS39 frame có15 HR79–85,1bpm, đủ39 GSR/IMU; chưa liên tục hoặc có tham chiếu. Đã nạp0.3.13-wrist12/hash verified12,489s, kiểm trước áp da20s/1.001 mẫu và14 frame WS GSR/IMU đạt; chờ xác nhận đo người12,4mA. [Chi tiết các mẫu số và giới hạn](05-WRIST-PROFILE.md).

Đã đo6,2mA sau xác nhận:45s/2.252 mẫu, không lỗi/gap/ALC, contact/guard ổn định, HR valid0 cả lượt. MQTT timeout làm WS không nhận frame trong lượt; sau đó tự khôi phục, WS13 frame GSR/IMU. Đã nạp0.3.13-led10/hash verified23,422s, kiểm20s/1.001 mẫu không lỗi, WS14 frame GSR/IMU. Chờ xác nhận đo cổ tay10mA, chưa thử12,4mA. Không lấy mẫu số39 frame của lượt trước để chấm lượt bị mất mạng. [Trace và giới hạn](05-WRIST-PROFILE.md).

PASS 6 env/4 header, 81 ca driver với 12 snapshot ở mỗi mức LED 6,2/10/12,4 mA, 76 ca HR, 34 FIFO, 8 tích hợp hybrid/10 selector/39 protocol; công cụ offline và parity chạy lại đạt. Mô phỏng còn ca nhận nhầm nhiễu quang tuần hoàn khi IMU yên. Sau khi cắm lại USB, nạp COM7/hash verified22,026s. Board45s chưa áp da:2.251 mẫu, không lỗi/gap/overflow; init một lần, bước tối đa1.438µs; WS39 GSR/39 IMU firmware0.3.13. Cổng chuyển động đã mở khi IMU yên. Chưa tái hiện lỗi bus cũ hoặc đo HR cổ tay bản mới, chưa CI mới. [Bằng chứng và bước chờ](05-WRIST-PROFILE.md).

## Bước 4: C++ và board 0.3.12 — 2026-11-06

PASS: 10.800 cửa sổ parity Python/C++, 10 ca selector/snapshot, 8 ca driver với worker giả lập, 76 ca công cụ offline, 95 ca parity tổng hợp chạy lại; 5 build/4 tổ hợp header và hồi quy driver/HR/FIFO/protocol. Đã nạp COM7, hash verified. Self-test ESP đạt; WS nhận đủ GSR/IMU. Đầu ngón tay: 38/39 frame có HR 77,2–88,3 bpm. Cổ tay: 0/39 HR, replay từ chối, **chưa đạt mục tiêu đo cổ tay**. Mỗi lượt 45 giây thu 2.251 mẫu không tăng lỗi/gap; lỗi I2C/init chặn khoảng 1 giây đã xảy ra giữa hai lượt, chưa xử lý xong. Chưa có nhịp tham chiếu hoặc CI từ xa mới. [Số đo và giới hạn](05-PPG-FIRMWARE-TRIAL.md).

## Bước 3: chất lượng tín hiệu offline — 2026-11-06

Đã chọn `hybrid_strict` qua vòng phát triển và vòng BIDMC11–15/seed mới sau khóa source/policy. Vòng mới tăng43 cửa sổ, MAE0,6234→0,6238bpm, không thêm lỗi trên10bpm/không nhận nhầm1457 cửa sổ nhiễu/phẳng. Tổng76 ca công cụ offline đạt, có native C++ pipeline và hồi quy quyết định. Chưa port/nạp bộ mới hoặc đo tài nguyên ESP; board vẫn0.3.11. HR cổ tay chưa nghiệm thu, file cổ tay cuối vẫn0 HR. [Bằng chứng và giới hạn](05-PPG-QUALITY-EVALUATION.md).

## Bước 2: benchmark thuật toán offline — 2026-11-06

Đã chạy4 trace/10 BIDMC/38 ca tổng hợp, cùng lọc C++ và cùng mốc chấm. PASS47 ca bản chuyển+6 ca chấm, native harness Werror. Kết quả không đủ để thay bộ HR bằng ứng viên MSPTD chưa quality gate; không chấm accuracy file cổ tay khi chưa có tham chiếu. Firmware giữ0.3.11, chưa nạp/CI/commit mới ở bước này. [Phương pháp và kết quả](05-PPG-ALGORITHM-EVALUATION.md).

## Chẩn đoán 0.3.11 — 2026-11-06

PASS4 build/4 header,76 ca HR,56 ca driver/12 snapshot ở hai mức LED,32 FIFO/39 protocol. Nạp COM7/hash verified11,199s. Không đổi bộ HR, LED, lịch lấy mẫu hoặc backoff. Quan sát45s không tiếp xúc và45s đặt ngón tay đều không phát sinh lỗi I2C/init lại. Lượt ngón tay2.251 mẫu, WS41 GSR/41 IMU/34 HR68,5..74,6bpm; chưa có nhịp tham chiếu. Startup overflow/gaps42 vẫn được giữ, không tăng trong lượt. Chưa xác định nguyên nhân lỗi6s cũ, chưa tuyên bố đã sửa dứt điểm hoặc nhánh5 hoàn tất. [Bằng chứng bước 1](05-PPG-I2C-DIAGNOSIS.md).

## Bản 0.3.10 — 2026-11-06

Đã sửa ca nhận nửa nhịp do biên độ xung xen kẽ. PASS 76 ca HR, 49 ca driver/12 snapshot ở baseline và LED10mA; 32 FIFO, 39 protocol, 4 header, 4 build. Nạp COM7/hash verified 11,199s. [Đối chiếu BIDMC](05-PPG-REFERENCE-BENCHMARK.md) có cải thiện nhưng vẫn 14 cửa sổ sai trên 10 bpm; không thay nghiệm thu cổ tay. Đo đầu ngón tay 45s sau xác nhận: 1.942 mẫu, có lỗi đọc và khoảng mất 6.221ms; WS 41 GSR/41 IMU nhưng 0 HR. **HR chưa đạt**, chưa có CI mới. [Chi tiết và giới hạn](05-SENSOR-RECOVERY.md). Các mốc dưới là lịch sử.

## Tín hiệu yếu/hai kênh0.3.9 — 2026-11-06

PASS4 build/4 tổ hợp header,71 ca HR,49 ca driver/12 snapshot qua schema ở hai mức LED,32 FIFO/39 protocol. Benchmark hữu hạn chỉ nhiễu0/2400 cửa sổ được chấp nhận; không gọi đây là độ chính xác trên người. Đã nạp0.3.9 baseline COM7/hash verified13,544s. Lượt cổ tay35s:1.752 mẫu,30 frame WS DEVICE/30 IMU,0 HR; contact ổn định, không tăng lỗi đọc/overflow/gap trong lượt; xử lý HR tối đa4,93ms. **HR chưa đạt nghiệm thu**, không có tham chiếu. Không thay dây/gá hoặc credential. [Chi tiết](05-SENSOR-RECOVERY.md).

## HR theo cửa sổ0.3.8 — 2026-11-06

Lượt che sáng quanh cảm biến:1.752 mẫu/35s,30 frame WS DEVICE/30 IMU,0 HR; không trace drop/timestamp lùi hoặc lỗi I2C/clip/gap mới. Có6 lần contact restart nên chưa coi đây là phép so ánh sáng được kiểm soát đầy đủ. Bản thử LED10mA riêng đang chuẩn bị, chưa nghiệm thu HR. Xem [phép thử quang](05-PPG-OPTICAL-TRIAL.md).

Lượt tiếp theo, mặt trong cổ tay cùng cấu hình:1.753 mẫu/35s,30 frame WS DEVICE/30 IMU,0 HR hợp lệ. Không trace drop/thời gian lùi hoặc tăng counter lỗi trong lượt; xử lý HR tối đa từ boot4,625ms. Contact có nhưng chu kỳ chưa đủ rõ; **chưa nghiệm thu HR cổ tay**, chưa xác định nguyên nhân quang/tiếp xúc. Chi tiết tại [nhật ký đo](05-SENSOR-RECOVERY.md).

PASS ba build và4 tổ hợp header;16 ca cửa sổ C++,49 ca driver/12 snapshot schema,39 ca protocol. Nạp COM7/hash verified11,220s. Đầu ngón tay:1.753 mẫu/35s,30 frame WS DEVICE,7 có HR73,2..78,8,30 có IMU. Cổ tay:1.753 mẫu/35s,30 frame/30 IMU nhưng0 HR; chưa đủ chu kỳ ngay cả replay bỏ điều kiện biên độ. Hai lượt không trace drop/timestamp lùi hoặc tăng counter lỗi; HR xử lý tối đa4,233ms. **Chưa nghiệm thu độ ổn định/độ chính xác HR**, chưa có tham chiếu. Xem [bằng chứng và giới hạn](05-SENSOR-RECOVERY.md). Các phiên bản dưới giữ lịch sử.

## Cổng tiếp xúc HR0.3.6 — 2026-11-06

Đã nạp COM7, ba build và4 tổ hợp header đạt; driver46 ca/11 snapshot schema, FIFO32/core39 đạt. Không tăng TTL3s. Kiểm tra12 dòng sau nạp: IR624..651/contact0 nên chưa nghiệm thu HR cổ tay. Xem [kết quả0.3.6](05-SENSOR-RECOVERY.md); các mốc0.3.5/0.3.2 bên dưới giữ lịch sử.

## Khôi phục cảm biến0.3.5 — 2026-11-06

- PASS build ba env, header kiểm tra riêng sau build;32 ca FIFO,41 ca driver và11 snapshot/schema,39 ca protocol. Thêm ca ID0x74/ACCEL_CONFIG2, metadata riêng, bỏ lô sau overflow và phục hồi bắt nhịp.
- Nạp0.3.5 thật qua COM7/hash verified; PPG và IMU có cửa sổ≈50,04Hz. Không che các counter PPG startup138 gap/overflow và169 discard; trong cửa sổ ổn định không tăng. Đã thấy IMU qua WS thật; kết quả HR cổ tay còn chờ tiếp xúc ổn định, chưa đánh dấu độ chính xác đạt.
- Chi tiết số đo/giới hạn và nguồn đối chiếu tại [05-SENSOR-RECOVERY.md](05-SENSOR-RECOVERY.md). Các mốc0.3.2 và số ca cũ bên dưới giữ làm lịch sử.

## Tối ưu code đo0.3.2 — 2026-11-06

| Bài | Kết quả local |
|---|---|
| `python scripts/check_ppg_acquisition.py` | PASS28 ca decoder/FIFO C++ |
| `python scripts/check_sensor_drivers.py` | PASS37 ca chạy driver thật với fake I2C/ADC/clock;10 snapshot qua serializer C++ và schema backend |
| `python scripts/check_firmware_protocol.py` | PASS39 ca core/control/telemetry |
| Backend `pytest -q` | PASS111; warning phụ thuộc Starlette/anyio có sẵn |
| Frontend `npm test` và `npm run build` | PASS60 và build; cảnh báo bundle>500kB có sẵn |
| MQTT `check_mqtt_integration.py --native-firmware` | PASS9 nhóm qua Mosquitto/backend/WS thật, dữ liệu SYNTHETIC |
| Header compatibility | PASS4 tổ hợp |
| Board với firmware0.3.2 | NOT_RUN: chưa nạp, chưa đo tại cổ tay, chưa xác nhận heap/stack/tốc độ/độ chính xác mới |
| CI GitHub cho thay đổi mới | NOT_RUN: chưa push lượt tối ưu này |

Ba env PlatformIO đã build đạt ở lượt sửa code; kết quả build cuối sau thay đổi `default_envs` được ghi tại [tiến độ](05-WRIST-MEASUREMENT.md). Sai khác kiểu tham chiếu `unsigned long`/`uint32_t` được phát hiện khi build ESP và đã sửa bằng timestamp32bit rõ kiểu; không thay test để bỏ qua lỗi. Có warning macro I2C_BUFFER_LENGTH của thư viện SparkFun, không sửa vendor và không coi đây là lỗi build. Không dùng các bài phần mềm làm bằng chứng HR/EDA chính xác.

Chi tiết hành vi, cấu hình và giới hạn: [chuỗi đo0.3.2](../contracts/SENSOR_ACQUISITION_0_3_2.md). Các mục bên dưới là mốc trước tối ưu; kết quả board cũ không tự áp dụng cho0.3.2.

## Buổi 2026-11-05 trên máy Trung

Lượt phiên tự động: launcher bật theo đúng target DEVICE, backend tự tạo AUTO-… sau sync và nhận ACK thật để RECORDING trên ESP32-001. Cursor trong DB theo session mới và cookie→WS nhận3 frame DEVICE tiếp tục tăng timestamp; không POST Start từ browser/công cụ thử. Backend111/frontend60 tests/build PASS. [Cách chạy và mốc phiên](05-AUTOMATIC-SESSIONS.md); raw/export chưa hoàn tất.

Lượt UI mới nhất: trạng thái thiết bị hai nhãn theo freshness, khung AI chờ/kết quả/lịch sử và bố cục toàn chiều rộng đã triển khai. Frontend58 tests/build PASS; HTTP module và3 frame DEVICE schema1.1 thật PASS. Model trên board vẫnnone, chỉ kiểm thử khung có AI bằng fixture test đúng nguồn; không ghi AI production PASS. Chưa kiểm tra pixel/viewport thật do browser tool không có kết nối.

Lượt phục hồi realtime mới nhất: frontend54/backend101 tests và build đạt. Đã rebuild backend, login cookie mới→WS6 lần có DEVICE đầu0,375..0,985 giây từ WS open; ping/pong6/6 và12 gói cách nhau1002 ms. [Chi tiết cơ chế/giới hạn](05-REALTIME-RECOVERY.md). Chưa tái hiện đúng phiên browser gây hard refresh, không coi kiểm thử transport là bằng chứng toàn bộ UI không thể kẹt.

Lượt giao diện mới: ảnh Trung đã có gia tốc/tốc độ xoay thật trên Dashboard. Đã thống nhất toàn màn hình theo docs/design/DASHBOARD.md; frontend46 tests/build đạt, HTTP và3 frame DEVICE schema1.1 đủ vector sau đổi UI đạt. Các bài bố cục trực quan375/768/1440px NOT_RUN vì browser runtime không khả dụng; không gọi DOM tests là QA pixel. Start/Stop/lỗi/tài nguyên trên board vẫn cần nghiệm thu riêng.

Lượt mới nhất: ảnh Trung xác nhận HR/GSR đã hiện trên Dashboard, trạng thái tiếng Việt. Sau yêu cầu tách chuyển động, đã thêm telemetry1.1/firmware0.3.0, hai ô/biểu đồ gia tốc m/s² và tốc độ xoay degrees/s; backend99, frontend44/build, native39, firmware2 env/header4 đạt. Backend đã rebuild trên máy Trung. **Chưa nạp0.3.0/chưa nghiệm thu trục thật**; các mốc số lượng tests cũ trong bảng dưới là lịch sử. Browser tool không khả dụng cho lượt giao diện mới, tests DOM không thay kiểm tra bố cục trực quan.

Native C++→broker/backend/WS thật đạt8 nhóm với dữ liệu SYNTHETIC, có kiểm tra sáu trục1.1 âm/0 và giữ đơn vị. Backend sau rebuild vẫn nhận3 frame thật DEVICE/schema1.0/firmware0.2.0; board cần nạp0.3.0 để có trục mới.

Base dev46d4e2d, nhánh `fix/esp32-local-mqtt-integration`. Board hiện ở Trung: ESP32-S3 Super Mini, MAX30102, MPU6050, Grove GSR. Đã nhận COM7/USB303A:1001, đọc flash4 MB/PSRAM2 MB và nạp SUCCESS. Backend sync1, đã nhận3 frame DEVICE/ESP32-001/session=null thật qua WS. Nghiệm thu toàn nhánh chưa hoàn tất: đang đọc Serial, còn Dashboard/StartStop/lỗi/rate/tài nguyên thật.

Đã bổ sung hồi quy trên receiver production: từ chối sensor topic ngoài hợp đồng, không broadcast khi chưa sync/DB lỗi, chống trùng/cũ và giữ login cookie. Các ca mới đã bắt được lỗi trước khi sửa.

| Bài local 2026-11-05 | Kết quả |
|---|---|
| Backend pytest | PASS72 |
| Protocol C++ → Pydantic | PASS30 |
| Firmware hai env | PASS2; serial-only flash322541 byte, network-check flash915965 byte; chưa là RAM/rate runtime |
| Headers | PASS4 |
| Native C++ → Mosquitto/API/DB/WS | PASS7 nhóm, WS dùng cookie HttpOnly sau HTTP login |
| Frontend | PASS26 và build đạt |
| Compose config --quiet | PASS |
| Nhận USB | Đã nhận COM7, USB303A:1001 theo output Trung gửi |
| Đọc chip/flash | Esptool xác nhận S3 rev0.2, flash4 MB XMC, embedded PSRAM2 MB/AP_3v3; chưa kiểm tra RAM runtime |
| Dây/nguồn | Trung xác nhận GPIO đúng bảng,3 cảm biến3V3, chung GND; chưa đo điện áp |
| Hotspot và dịch vụ local | Laptop172.20.10.3 trên iPhone; broker1883/BE8000 healthy, login MQTT backend/esp32 và WS cookie đạt; backend sync0 |
| Build cấu hình Wi-Fi thật | PASS esp32s3_supermini; RAM47180/flash915953 byte, file local không được track |
| Upload COM7 | PASS theo log Trung gửi, SUCCESS21.78 giây/hash verified |
| ESP → MQTT → backend → WS | PASS kết nối/live ngoài phiên:3 frame DEVICE/ESP32-001, session=null, tăng timestamp, khoảng1002 ms; evidence local bị Git bỏ qua |
| Serial mạng/cảm biến | wifi/mqtt/sync1; lỗi/drop0 trong24.1 s; GSR/IMU driver VALID, PPG NO_FINGER. Chờ thử ngón tay |
| PPG với ngón tay | Ảnh Trung gửi có PPG VALID/HR, cùng GSR/IMU VALID. Chỉ smoke test; chưa đánh giá ổn định hoặc độ chính xác |
| Launcher một lệnh | PASS trên máy Trung từ root/frontend, đồng bộ dependency/cache, stop/start giữ dữ liệu; chưa chạy trực tiếp máy Tân |
| Tự mở phiên local | PASS bridge→cookie HttpOnly→3 frame DEVICE thật, cả sau stop/start broker/backend; không nhập token. Origin ngoài/file private bị chặn |
| Hồi quy lượt auto-dev | Backend77, frontend41, build TypeScript/Vite/audit0. Browser tool không khả dụng; chưa thay bằng chứng UI trực quan |
| Metrics ban đầu | HeapMin201764 byte, stack watermark3780 byte, loopGap10 ms; processed rates khoảng50.08/49.75/19.92 Hz. Chưa đủ F17 hoặc đối chiếu mất mẫu FIFO |
| Metrics lần chụp tiếp | Uptime khoảng116–117 s, heapMin202632/stackWater3780 byte, loopGap106 ms; F17 còn cần đối chứng/phân tích spike, chưa PASS |
| Cả3 cảm biến, Dashboard, Start/Stop và lỗi/tài nguyên | Chưa nghiệm thu; đang đọc Serial, không thay bằng frame WS |

Chưa có CI cho lượt sửa local này. Bảng 2026-11-03 bên dưới là lịch sử.

Theo dõi thao tác thực tại [05-LOCAL-BRINGUP.md](05-LOCAL-BRINGUP.md).

## Bằng chứng 2026-11-03

Ngày 2026-11-03, Windows, Python3.12. Code hoàn thiện tại d1101c5 trên nhánh `feature/firmware-telemetry-client-completion`, base dev `1e73aea`. Board ở chỗ Tân, serial discovery trên máy này trả [].

**WAITING_HARDWARE cho nghiệm thu.** Code và tài liệu được bàn giao qua [PR #15 vào dev](https://github.com/namtrungdn310/ASD-EASE/pull/15) theo yêu cầu Trung; kết quả CI/head/merge tra trực tiếp tại PR. Bảng local dưới đây không thay bằng chứng CI.

## Kết quả local

| Bài | Kết quả | Phạm vi |
|---|---|---|
| PlatformIO esp32s3_supermini | PASS | Build/link mặc định mạng tắt, không cần secret |
| PlatformIO esp32s3_network_check | PASS | Compile/link đủ ESP-MQTT/TLS bằng cấu hình build-only, không tự kết nối |
| Header compatibility | PASS4/4 | Các thứ tự include chung/cũ |
| Native C++ protocol | PASS30 tests | Core/serializer production → schema Pydantic runtime; clock/transport giả |
| Native C++ qua Mosquitto | PASS7 nhóm | Paho làm transport test, core C++ xử lý JSON/phiên; broker/API/DB/WS thật, dữ liệu SYNTHETIC |
| Backend pytest | PASS61 | Gồm chặn topic cũ/sai nguồn |
| AI pytest | PASS15 | Hồi quy hiện có |
| Frontend tests/build/audit | PASS26, build đạt, audit0 | React/jsdom; chưa là kiểm tra browser bằng board |
| HTTP transport | PASS19 frame | HTTP/simulator → WS thật, gồm nối lại; không board |
| Compose mặc định/LAN | PASS | config --quiet; bind IP cụ thể đúng1 port, chọn đúng thư mục credential; không in secret |
| MQTT simulator Python | PASS7 nhóm | Bài hồi quy riêng qua broker thật, không thay core C++ |

Static size ở lần build cuối:
- Mạng tắt: RAM20636/327680 byte, flash322293/1310720 byte.
- Build-check mạng: RAM47180/327680 byte, flash913889/1310720 byte.
- Đây là kích thước link, chưa tính/đo heap, task stack, queue và TLS runtime trên board. Không suy RAM còn đủ cho07 từ các số này.

Cảnh báo hiện có: frontend bundle khoảng590 kB vượt ngưỡng500 kB; không làm build lỗi. Python có cảnh báo deprecation của dependency. Không sửa dependency không liên quan để che cảnh báo.

## F01–F19

PASS_SW chỉ nghĩa phần mềm được kiểm tra. NOT_RUN_HW nghĩa chưa chạy trên ESP32 thật; không dùng PASS_SW thay nghiệm thu phần cứng.

| ID | Kết quả | Bằng chứng đã có / việc Tân cần xác nhận |
|---|---|---|
| F01 | PASS_SW | Hai env PlatformIO; không cần network_config.h/credential thật. |
| F02 | PASS_SW | Native harness compile chính session_protocol.cpp và xuất JSON; InboundTelemetry/control.py kiểm tra thực. Không dùng fixture Python thay serializer. |
| F03 | PASS_SW; NOT_RUN_HW | Test tuổi HR/PPG/GSR/NaN/0/baseline/null và CALIBRATING; cần tháo cảm biến/chờ TTL trên board. |
| F04 | NOT_RUN_HW | Chưa ESP32/LAN/SUBACK; code ESP-MQTT đã link. Credential DEVICE riêng/profile50/50/20 được Registry kiểm tra và account thật thử ACL trong broker test. |
| F05 | PASS_SW; NOT_RUN_HW | Core ngoài phiên dùng boot timestamp/session=null sau sync. Chờ DEVICE thật→DB/WS/Dashboard. |
| F06 | PASS_SW; NOT_RUN_HW | Core + broker thật Start→ACK→DB RECORDING→WS. Chờ ESP-MQTT/cảm biến thật. |
| F07 | PASS_SW; NOT_RUN_HW | Topic/pending_command trùng chỉ Start một lần, epoch giữ; chờ lặp thật trên board. |
| F08 | PASS_SW; NOT_RUN_HW | Profile/ID/boot/connection/request/generation/lease; lệnh sai không Start. Chờ thiết bị thật. |
| F09 | PASS_SW; NOT_RUN_HW | Stop zero-batch/raw-disabled, DB complete=false đúng. Chờ Stop vật lý và đo độ trễ. |
| F10 | PASS_SW; NOT_RUN_HW | STOP trước START confirmation, START cũ tới muộn không làm ghi lại; chờ board. |
| F11 | NOT_RUN_HW | Chưa thử Wi-Fi sai/mất/khôi phục khi cảm biến đang đọc; cần đo rate/gap/bộ nhớ. |
| F12 | PASS_SW; NOT_RUN_HW | Broker thật restart, core giữ epoch/đồng bộ; LWT nonce mới có native test. Chờ ESP-MQTT reconnect/LWT thật. |
| F13 | PASS_SW; NOT_RUN_HW | Backend thật restart khi broker còn, DB/ACK/phiên phục hồi, sync lại. Chờ board. |
| F14 | PASS_SW; NOT_RUN_HW | Khởi tạo core boot mới không giữ Start/epoch; chờ reboot ESP32 đang thu và log backend. |
| F15 | NOT_RUN_HW | Serializer có test null/stale; chưa tháo cảm biến khi MQTT vẫn tốt. |
| F16 | PASS_SW; NOT_RUN_HW | Broker thật chặn anonymous/sai password/cross-device; native chặn retained/nonce cũ/quá gói/JSON trùng/sai số. Chờ SDK auth/ACL/TLS/retained thật. |
| F17 | NOT_RUN_HW | Chưa có số đo sensing/network/Serial, heap/stack/timing; không điền số danh định làm số đo. |
| F18 | NOT_RUN_HW | Frontend26 tests đạt nhưng chưa ảnh browser nhận ESP32 thật. |
| F19 | PASS_SW local; CI xem PR | Backend/AI/frontend/firmware/header/HTTP/native MQTT đạt theo bảng; cả6 check được theo dõi tại PR #15 trên head cuối. |

## Lệnh tái hiện

PowerShell tại root, venv đã cài requirements backend/AI và PlatformIO. Native cần g++/clang++ C++17; Windows máy này dùng C:\msys64\ucrt64\bin\g++.exe (thêm thư mục vào PATH), Linux CI dùng g++ có sẵn.

```powershell
.\.venv\Scripts\python.exe -m platformio run -d ai/edge_firmware
.\.venv\Scripts\python.exe .github/scripts/check-firmware-headers.py
.\.venv\Scripts\python.exe scripts/check_firmware_protocol.py
.\.venv\Scripts\python.exe scripts/check_mqtt_integration.py --native-firmware
.\.venv\Scripts\python.exe scripts/check_mqtt_integration.py
.\.venv\Scripts\python.exe .github/scripts/check-mock-transport.py
Push-Location backend
..\.venv\Scripts\python.exe -m pytest -q
Pop-Location
Push-Location ai
..\.venv\Scripts\python.exe -m pytest -q
Pop-Location
npm --prefix frontend test
npm --prefix frontend run build
npm --prefix frontend audit --omit=dev
docker compose config --quiet
```

Bài MQTT tạo container/port/DB/secret tạm riêng, dọn đúng container khi xong; không dùng hoặc sửa dữ liệu nhóm. Hai chế độ MQTT dùng cùng bài7 nhóm, một chế độ simulator Python, một chế độ core C++ với Paho transport test. Chưa chạy phần radio/driver ESP-MQTT trên ESP32.

## Mẫu điền nghiệm thu board

Tân bổ sung ngày, SHA firmware/backend/frontend, board/flash/PSRAM thực, dây, SSID đã che, IP/port, profile, firmware version; không lưu password/token. Mỗi Fxx ghi thao tác, kết quả mong đợi/thực tế, log/ảnh đã che secret và PASS/FAIL.

Đo cùng cửa sổ60 s: số PPG/IMU/GSR được xử lý, khoảng trống lớn nhất, lỗi FIFO, Start/Stop latency, heapMin, stack watermark byte, queue/outbox; so mạng tắt/mạng bật/Serial giảm. Nếu fail, giữ log và lỗi, không sửa schema/ngưỡng hoặc đánh PASS bằng kết quả mô phỏng.
