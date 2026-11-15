# Bàn giao code nhánh 5

## Bản bàn giao tích hợp ngày 15/11/2026

Nhánh chuẩn bị PR: `feature/device-monitoring-workspace`. Thông tin ở các mục lịch sử bên dưới ghi lại từng lượt đo; không dùng chúng để mô tả bản code hiện tại.

- HR chính: bộ RR khôi phục từ firmware cũ, lọc/trung bình RR; worker cửa sổ chỉ đánh giá chất lượng. Giữ cấu hình thu mẫu, LED và gá phần cứng đang dùng. Rà soát lần này sửa khóa blanking khi tín hiệu sạch đổi 60→120 bpm: cần ba đỉnh xen giữa nhất quán mới bỏ khóa nhịp cũ. Test vẫn chặn đỉnh lẻ; chưa đối chiếu nhịp người sau sửa này.
- Số mẫu thật theo cửa sổ 8 giây đi từ driver qua `sample_count` tới backend/WebSocket/FE. Không đếm số điểm biểu đồ hoặc nhịp HR dự báo. [Quy ước](05-SENSOR-SAMPLE-COUNTS.md).
- `npm run dev` mở dịch vụ/web; chọn thiết bị và bấm Kết nối. Không tự nạp firmware. `npm run device:flash` mới build/nạp cấu hình local. Ngắt kết nối trên web chỉ dừng theo dõi, không tắt cảm biến hay broker.
- Sidebar thu gọn; bốn thẻ cảm biến và dự đoán hiện tại ở trang Thiết bị. Báo cáo AI có biểu đồ/bảng riêng và phân trang. AI chưa có mô hình, khoảng thời gian dự đoán chưa được telemetry cung cấp nên để trống; không tạo cảnh báo giả.
- Không đưa secret, `network_config.h`, DB, raw và log local lên Git. Không coi test sóng tổng hợp hoặc chất lượng 100% là bằng chứng độ chính xác HR cổ tay.

Kết quả kiểm tra chốt và PR/commit được ghi tại [bàn giao phát hành](05-RELEASE-AUDIT.md).

## Lịch sử trước bản bàn giao tích hợp

**Đã chốt HR0.3.23-tracker, 2026-11-08.** Lượt cuối đủ45gói/45giây; sau4gói chờ đầu có41gói HR liên tiếp68,8–76,6bpm, không dùng dự báo. Trung xác nhận giữ bản này. Đã dọn profile nạp thử cũ; mặc định `esp32s3_supermini` và alias `esp32s3_hr_tracker` cùng dùng cấu hình đã đo. Không nạp lại khi dọn, không đổi lõi HR/GSR/IMU. [Kết quả HR](05-HR-TRACK-SWITCH.md), [báo cáo dọn mã](05-CLEANUP-AUDIT.md), [chạy hằng ngày](05-ONE-COMMAND-DEV.md). Chưa có đối chiếu đồng thời để xác nhận sai số cổ tay; chưa push/merge lượt dọn.

## Lịch sử triển khai

**Bản đang nạp mới nhất0.3.20-tracker:** đã kiểm lượt cổ tay cuối45gói/45giây:28gói HR từ ESP,8gói tạm tính ởFE. Sau HR đầu tiên, thẻ/series trình bày nối liền qua các khoảng ngắn; nét đứt và nhãn tách khỏi dữ liệu đo. Chưa hết các số thấp hoặc xác minh sai số; không coi dự báo là HR thật/nhãn train.39core,64FE và kiểm build/nạp/tích hợp đạt. [Cách chạy, file chính, kết quả và giới hạn](05-HR-CONTINUITY.md). Phiên bản/checkpoint phía dưới là lịch sử.

**Bản đang nạp mới nhất:0.3.18-tracker.** Đã triển khai theo dõi nhiều giả thuyết chu kỳ ở task riêng và làm mượt các ước tính mới. Lượt cổ tay cuối:45gói/45giây,17gói có HR,13gói cuối liên tiếp70,3–72,2bpm; GSR/IMU45/45, mạng ổn trong lượt. Còn khoảng thiếu và chưa xác nhận sai số; không dùng HR này làm nhãn chuẩn để train. Code/tests/build/nạp và hai lượt kiểm hướng mới đã xong. [File chính, cách chạy, bằng chứng và rollback](05-HR-CYCLE-TRACKER.md). Các mốc phía dưới là lịch sử, không phải phiên bản đang dùng.

**Kết quả demo mới nhất:** đã thu hai lượt cổ tay trên `0.3.16-demo`; lượt cuối đủ **45 gói/45 giây**, GSR/IMU 45/45, mạng giữ đồng bộ nhưng HR 0/45. Lượt đầu driver có 9 bản chụp HR, song mạng đã ngắt nên FE không nhận. Mạch trên bàn giữ 68 gói/70 giây. Code/kiểm thử/nạp demo hoàn tất, **HR cổ tay hiển thị đều chưa đạt**, chưa thu thêm hoặc đổi ngưỡng tiếp. [Bằng chứng cuối vòng demo](05-HR-DEMO.md). Các mốc “chờ lượt cổ tay” phía dưới là lịch sử.

**Mục tiêu demo mới, 2026-11-07:** Trung chấp nhận HR tương đối, ưu tiên thẻ hiển thị đều. Đã nạp `0.3.16-demo`, giữ bản đối chứng; 61 test FE, 31 ca HR demo, driver/hybrid/header và hai build đạt. Nhận 5 gói DEVICE thật qua WS sau nạp, GSR/IMU đủ và phiên tự mở; chưa có lượt cổ tay sẵn sàng. Thẻ giữ số tối đa 10 giây phải ghi tuổi nhận, không điền raw/telemetry/biểu đồ. [Bàn giao HR demo](05-HR-DEMO.md). Chưa xác nhận sai số hoặc nghiệm thu nhánh 5.

**Checkpoint HR mới nhất, 2026-11-07:** đã thu đủ bốn lượt và chấm hai ứng viên offline. Chưa chọn bản để nạp: A bỏ sót nhịp sạch 40 bpm; B còn nhận nhầm nửa nhịp trên mô phỏng mới, chưa khôi phục HR cổ tay ổn định. Có 41 ca kiểm tra công cụ đạt; không đổi GSR/IMU/schema. [Kết quả và giới hạn](05-HR-WEAK-SIGNAL-EXPERIMENT.md). Các mục dưới là tiến trình trước checkpoint này; chưa nghiệm thu HR/nhánh 5.

**Vòng HR mới, 2026-11-07:** đã dọn các phần thừa xác định được và replay lại raw; đang theo [kế hoạch HR cổ tay](05-HR-ROOT-CAUSE-PLAN.md). Cụm mạch chỉ đặt nhẹ, không đè; xem lại độ chặt của thuật toán thay vì chỉ tăng LED. GSR/IMU giữ nguyên. [Phạm vi dọn mã và kiểm thử](05-CLEANUP-AUDIT.md). Chưa nạp thuật toán mới hoặc nghiệm thu độ chính xác HR thật.

**Hiện tại 2026-11-07: đã quay về0.3.13-led10 trên COM7**, 200Hz/avg4/LED10mA, làm đối chiếu. Lượt cổ tay0.3.15/400Hz/avg8 cũng0/39 HR dù sensing/contact/guard/mạng ổn định; chưa có cấu hình HR đủ lặp lại. Kiểm sau khi quay về20s/1.000 mẫu và14 frame WS GSR/IMU đạt. Code thử/sửa đồng hồ vẫn trong repo;7 build/4 header/89 driver ở4 profile và hồi quy đạt. **HR cổ tay chưa đạt**, cần nhịp tham chiếu để chọn thuật toán có cơ sở; chưa nghiệm thu nhánh5/CI/push. [Bằng chứng cuối đợt thử](05-WRIST-SAMPLING-TRIAL.md), [các mức LED](05-WRIST-PROFILE.md). Các mốc dưới là lịch sử.

**Hiện tại: 0.3.12 đã nạp lên ESP máy Trung.** Bộ hybrid C++ khớp 10.800 cửa sổ với policy Python đã chọn; 5 cấu hình build và kiểm hồi quy đạt. Đầu ngón tay: WS có 38/39 HR 77,2–88,3 bpm. Cổ tay: 0/39 HR, dù thu liên tục và GSR/IMU đủ; replay cùng policy cũng từ chối. Worker tối đa khoảng 175 ms/cửa sổ. Giữa hai lượt có lỗi I2C và init chặn khoảng 1 giây cần xử lý; chưa nghiệm thu cổ tay, độ chính xác hoặc nhánh 5. Xem [bước 4 và bằng chứng](05-PPG-FIRMWARE-TRIAL.md). Các mốc dưới là lịch sử; chưa push/CI mới.

**Bước3 đã chốt ứng viên hybrid lọc chặt ở mức offline**, chưa tích hợp firmware. Có đặc tả cấu hình/hash,2 vòng benchmark và76 ca công cụ local đạt. Không thêm lỗi lớn hoặc nhận nhầm bộ nhiễu mới; HR cổ tay vẫn chưa nghiệm thu. Bước4 cần port C++/đối chiếu/đo tài nguyên trước nạp. Board giữ0.3.11, chưa CI/commit/push mới. [Báo cáo](05-PPG-QUALITY-EVALUATION.md), [đặc tả ứng viên](../contracts/PPG_QUALITY_CANDIDATE_V1.json).

**Bước2 đã đối chiếu offline**, không đổi firmware0.3.11: thêm công cụ C++/NumPy, dữ liệu tham chiếu và53 ca kiểm tra. Ứng viên MSPTD chưa cổng chất lượng chưa đủ điều kiện đưa lên board; HR cổ tay vẫn chưa nghiệm thu. [Báo cáo và bước tiếp](05-PPG-ALGORITHM-EVALUATION.md). Chưa CI từ xa/commit/push mới.

**Bản hiện tại 0.3.11 — bước 1 chẩn đoán I2C:** đã nạp COM7/hash verified; thêm log lỗi giao dịch và từng lần khởi tạo lại. Bộ HR/LED/lấy mẫu giữ như0.3.10. Build4 env/4 header,76 ca HR,56 ca driver/12 snapshot ở hai mức LED,32 FIFO/39 protocol đạt. Chưa kết luận sửa được gián đoạn6s hoặc HR ổn định. Xem [bằng chứng bước 1](05-PPG-I2C-DIAGNOSIS.md). Các mốc dưới là lịch sử.

**Bản hiện tại 0.3.10:** đã nạp COM7/hash verified; sửa ca HR nhận nửa nhịp khi xung lớn nhỏ xen kẽ. Đạt 76 ca HR, 49 ca driver/12 snapshot ở hai mức LED, 32 FIFO/39 protocol, 4 build/4 header. [Đối chiếu có tham chiếu](05-PPG-REFERENCE-BENCHMARK.md) cải thiện nhưng vẫn có lỗi; chưa nghiệm thu HR cổ tay. Giữ cụm cố định, không giữ số HR cũ. Chưa CI mới. Các phiên bản dưới là lịch sử.

**Bản hiện tại0.3.9, đã nạp COM7/hash verified13,544s:** PPG200Hz/averaging4/FIFO50Hz, đánh giá tín hiệu yếu theo mức nhiễu, chọn IR/RED và xác nhận hai cửa sổ. Bốn build/4 tổ hợp header,71 ca HR/49 ca driver/12 snapshot schema,32 FIFO/39 protocol đạt. Đo board35s:1.752 mẫu,30 frame WS DEVICE/30 IMU,0 HR; không tăng lỗi lấy mẫu trong lượt. **Code đã triển khai; HR cổ tay chưa đạt**, chưa có tham chiếu để kết luận độ chính xác. Trung yêu cầu giữ cụm cố định, chỉ sửa code. [Bằng chứng và giới hạn](05-SENSOR-RECOVERY.md). Các mục dưới giữ lịch sử.

**Bản đang chạy0.3.8:** đã nạp COM7/hash verified. HR kiểm tra chu kỳ trên cửa sổ8s/cập nhật1s, không giữ số cũ khi cửa sổ bị từ chối. Ba build,16 ca cửa sổ,49 ca driver/12 snapshot schema và39 ca protocol đạt. Lượt đầu ngón tay:7/30 frame WS có HR73,2..78,8; đủ30 vector IMU, xử lý HR tối đa4,1ms. Chưa nghiệm thu HR cổ tay hoặc độ chính xác. Xem [bằng chứng và giới hạn](05-SENSOR-RECOVERY.md). Các phiên bản dưới là lịch sử.

## Bản đang chạy0.3.5 — 2026-11-06

Đã nạp COM7 và sửa hai lỗi thực tế sau0.3.2: profile IMU6515/ID0x74 và vòng lặp phục hồi FIFO PPG. Vector IMU đã qua WebSocket nguồn DEVICE, PPG có cửa sổ đọc≈50Hz; còn xác minh HR cổ tay sau khi đặt đúng mắt quang. Build3 env,32 ca FIFO,41 ca driver/11 snapshot schema và39 ca protocol đạt. Chưa push/CI/merge. Xem [khôi phục cảm biến](05-SENSOR-RECOVERY.md); các mốc0.3.2 dưới đây là lịch sử.

## Code đo0.3.2 — 2026-11-06

Đã tối ưu code độc lập với mẫu vỏ: FIFO PPG/IMU, clock/lịch đọc, log task riêng, kiểm tra cấu hình/mất mẫu, HR40..200bpm nhất quán và GSR dùng ADC eFuse. IMU cần giữ yên vài giây khi khởi động để lấy lệch gyro; GSR raw vẫn lên Dashboard, delta/µS chưa hiệu chuẩn để null. Chi tiết [chuỗi đo0.3.2](../contracts/SENSOR_ACQUISITION_0_3_2.md), [bước nạp/đo](05-WRIST-MEASUREMENT.md). Chưa nạp hoặc xác nhận độ chính xác bản mới trên board, chưa push/merge lượt này.

Các bản `_check` chỉ dùng build; mặc định PlatformIO đã chọn `esp32s3_supermini` để tránh nạp nhầm cấu hình thử. MQTT/phiên tự động và `npm run dev` giữ nguyên.

Cập nhật mới 2026-11-05: Trung đã giữ board/cảm biến. Sau PR #17, đang sửa trên `fix/esp32-local-mqtt-integration`; xem [phân tích thay đổi](05-REVIEW-PR17.md) và [bước đang làm](05-LOCAL-BRINGUP.md). Đã nạp COM7 thành công, backend sync1 và WS nhận3 frame DEVICE thật. Đang đọc Serial, còn Dashboard/StartStop/lỗi/tài nguyên thật. Các mục 2026-11-03 dưới đây là bằng chứng lịch sử.

Cập nhật 2026-11-03. Nhánh `feature/firmware-telemetry-client-completion` từ dev `1e73aea` sau PR #14 của Tân.

**Phần mềm đã triển khai; nghiệm thu ESP32 đang WAITING_HARDWARE.** Board/cảm biến vẫn ở chỗ Tân. Chưa nạp, chưa đo ảnh hưởng mạng và chưa xác nhận Dashboard bằng dữ liệu board thật. Code được đưa vào dev qua [PR #15](https://github.com/namtrungdn310/ASD-EASE/pull/15) theo yêu cầu Trung; trạng thái CI/merge xác nhận tại PR.

## Đã hoàn thiện

- Theo yêu cầu tách chuyển động: firmware0.3.0/telemetry1.1 gửi hai vector sau EMA; backend giữ đủ qua MQTT/HTTP→DB→WS, frontend có hai ô và hai biểu đồ ba trục. Giữ1.0 tương thích và raw/control/topic cũ. Xem [đặc tả/đổi phiên bản](../contracts/IMU_TELEMETRY_V1_1.md). Máy Trung đã rebuild backend; cần nạp0.3.0 để thử trục thật.

- Firmware0.2.1 thêm điểm chuyển động từ50 mẫu MPU6050 trước EMA; xem [motion-rms-v1](../contracts/MOVEMENT_SCORE.md). Không thay AI/quality/trạng thái kỹ thuật. Chờ nạp và so sánh giữ yên/xoay trên board thật; các mô tả null ở mốc firmware cũ bên dưới là lịch sử.

- Luồng dev một lệnh cho Trung/Tân: scripts/dev.mjs + local_dev.py chuẩn bị/reuse local và bật dịch vụ; frontend/dev/local-session.mjs đổi token server lấy cookie, LocalConnection.tsx tự mở/gia hạn phiên trước Dashboard. Xem05-ONE-COMMAND-DEV.md; production không bật bridge này.

- Wi-Fi và ESP-MQTT chạy ở task riêng, không chờ mạng trong vòng đọc cảm biến. Snapshot queue1 luôn thay bằng bản mới nhất, không xả telemetry cũ sau reconnect.
- Topic `asd-ease/v1/DEVICE/{device_id}/...`, telemetry QoS0, control/ACK/sync/presence QoS1; clean session, SUBACK trước sync, LWT có connection nonce mới trước CONNECT.
- Start/Stop, ACK thực thi, xác nhận backend, lease tính từ lượt sync, chống lặp/nonce/generation cũ, giữ epoch khi reconnect. Reboot không tự tiếp tục phiên cũ.
- Serializer đúng schema1.0; dữ liệu lỗi/cũ thành null, GSR delta=percentChange/100, không bịa quality/movement/prediction. Tuổi HR lấy từ nhịp hợp lệ và tuổi PPG, không chỉ lúc gọi read().
- Cấu hình DEVICE/ACL riêng, broker bind IP LAN có chủ đích. Giữ loopback mặc định và file secret local.
- Loại subscriber thử chưa dùng theo topic cũ; tiếp tục dùng receiver04 có registry/xác thực/phiên và DB→WS hiện có.
- Tests native C++ dùng chính core production, kiểm tra JSON bằng Pydantic runtime và đi qua Mosquitto/backend/DB/WS thật. Python chỉ thay lớp vận chuyển trong bài thử native, dữ liệu luôn SYNTHETIC.

## Các file chính làm gì?

| File/nhóm | Vai trò |
|---|---|
| include/communication/session_protocol.h và src/communication/session_protocol.cpp | Luật phiên/lệnh/ACK/đồng hồ và tạo JSON đúng đặc tả, chạy được cả ESP32 và tests native. |
| communication/mqtt_transport.* | Wi-Fi, ESP-MQTT, SUBACK/PUBACK, LWT, reconnect, task/queue có giới hạn và thống kê lỗi/tài nguyên. |
| communication/telemetry_serializer.* | Chụp số đo và tuổi mẫu từ driver, không gửi Pretty JSON Serial. |
| communication/network_settings.h, network_config.example.h | Mặc định mạng tắt; đọc cấu hình local, phân biệt LAN plaintext/TLS và env chỉ build. |
| MAX30102Sensor/MPU6050Sensor/GSRSensor | Thêm thời điểm mẫu/nhịp hợp lệ; giữ thuật toán lọc, đơn vị và GPIO của Tân. |
| src/main.cpp | Copy snapshot sang task mạng, thống kê số mẫu/loop; giữ đọc cảm biến và Serial. |
| platformio.ini | Pin platform7.1.3/ArduinoJson7.4.3/C++17, build thêm env kiểm tra mạng/TLS. |
| scripts/setup_local_mqtt.py | Tạo bộ credential mới có DEVICE riêng bằng --device-id, không ghi đè cấu hình cũ. |
| compose.yaml | MQTT_BIND_IP và MQTT_LOCAL_DIR để chọn LAN/bộ cấu hình thử, mặc định vẫn loopback. |
| tests/native/protocol_harness.cpp, scripts/firmware_native*.py | Chạy core C++ bằng clock/transport thử; không phải cảm biến hoặc radio thật. |
| scripts/check_firmware_protocol.py | Kiểm tra serializer/phiên/lệnh/freshness/giới hạn bằng core C++ và schema backend. |
| scripts/check_mqtt_integration.py | Kiểm tra broker/API/DB/WS; --native-firmware dùng core C++ thay simulator Python. |
| backend/tests/test_firmware_topics.py | Chặn topic cũ/sai nguồn qua receiver đang dùng. |
| .github/workflows/ci.yml | Thêm native/protocol/broker trong Firmware build, giữ6 tên check bảo vệ nhánh. |

## Lựa chọn SDK và giới hạn

Dùng ESP-MQTT có sẵn trong Arduino2.0.17/ESP-IDF4.4 của platform đã pin, publish được QoS1; bỏ PubSubClient vốn không publish QoS1. [API chính thức ESP-MQTT](https://docs.espressif.com/projects/esp-idf/en/v4.4.7/esp32s3/api-reference/protocols/mqtt.html). Header/API và libmqtt.a đã được compile/link cả nhánh mạng/TLS; TLS handshake trên board chưa thử.

Worker mạng stack12 KiB, SDK MQTT stack6 KiB; inbox8 gói tối đa4 KiB, core+outbox gửi giới hạn8 gói/32 KiB, snapshot1. Giới hạn này chưa chứng minh còn đủ heap/stack cho board và HTTPraw07; phải đo runtime. Chờ SUBACK/PUBACK có timeout, lỗi CONNACK cấu hình/quyền hoặc xác minh chứng chỉ dừng retry; lỗi mạng tạm dùng backoff.

Giữ MPU6050 SDA5/SCL11 của PR #14, MAX30102 SDA8/SCL9, GSR7. Profile50/50/20 là danh định, không ghi như số đo. Không đổi driver để làm payload trông đẹp.

## Cách dùng và bước tiếp

1. Tân làm theo [05-SETUP](05-SETUP.md), xác nhận board/dây rồi nạp env esp32s3_supermini với file credential local.
2. Điền [05-VERIFICATION](05-VERIFICATION.md), đặc biệt LAN/StartStop/reconnect/độ trễ/số mẫu/tài nguyên/Dashboard thật.
3. Code đã commit/push, [PR #15 vào dev](https://github.com/namtrungdn310/ASD-EASE/pull/15); theo [Git workflow](../GIT_WORKFLOW.md), chỉ merge sau đủ6 CI và không xung đột. Tân pull dev sau khi PR merge; chỉ ghi nhánh05 DONE sau đủ bằng chứng board.
4. Nhánh06 làm backend raw bền/chống trùng/đối chiếu;07 mới bật raw HTTP/batch và thay zero-batch summary bằng tổng kết thu thật.

Nhánh05 Stop có cutoff0/raw_recording_enabled=false, do đó complete=false là đúng. Không lấy telemetry1Hz thay raw hoặc kết quả native thay nghiệm thu ESP32.
