# Bước 4: port C++ và thử board

Triển khai ngày 2026-11-06. Mục tiêu: chạy đúng ứng viên `hybrid_strict` đã chốt ở bước 3, giữ lấy mẫu độc lập với xử lý HR. Chưa nghiệm thu HR cổ tay hoặc sai số khi chưa đo đối chiếu.

## Cấu trúc

- `processing/ppg_quality.h`: port C++ với workspace cố định, không heap; giữ ngưỡng/kiểm tra của policy. Chỉ tính peak MSPTD vì policy Python không dùng onsets. Goertzel tính đúng29 bin rFFT Hann400 từ0,5..4Hz, giữ ngưỡng phổ.
- `PpgRate::copyFilteredWindow`: accessor const chụp400 mẫu/kênh theo thời gian, không sửa thuật toán đối chứng.
- `ppg_hybrid_worker`: task priority0 cùng core Arduino, input latest-only1 slot, output1 slot. Sensing không đợi kết quả. Workspace ở .bss, task stack8192 **byte** theo API ESP-IDF đang cài; không giả đơn vị vanilla FreeRTOS.
- `MAX30102Sensor`: giữ baseline valid, chỉ dùng fallback đã xác nhận/cùng generation và mới không quá1500ms. Contact/reset/lỗi/mất mẫu đổi generation nên không nhận kết quả task cũ. Không gia hạn timestamp từ cache.
- Self-test sóng80bpm nội bộ chạy ở task riêng, reset trước dữ liệu thật; không đưa sóng/kết quả self-test vào output đo hoặc MQTT. Log chỉ ghi PASS/time/resource, không gắn mẫu giả là DEVICE.

Bản thử0.3.12 dùng cấu hình cảm biến/credential/schema cũ. Có env `esp32s3_ppg_baseline` với macro `ASD_PPG_HYBRID_ENABLED=0` và version0.3.12-baseline để tắt task nếu cần đối chiếu; không force-reset Git hoặc sửa dây.

## Tiến độ

- Port C++: đã viết, khớp quyết định Python trên10.800 cửa sổ gồm95 ca tổng hợp và toàn bộ hai báo cáo bước3. Có đối chiếu đặc trưng/nguồn, không chỉ đếm số output.
- Native driver: 56 ca/12 snapshot và 76 ca HR cũ đạt ở hai cấu hình LED. Kiểm tra mới: 10 ca selector/snapshot và 8 ca tích hợp driver thực với kết quả worker giả lập đều đạt; kiểm 39 ca protocol và 4 tổ hợp header đạt.
- 76 ca công cụ offline và 95 ca parity tổng hợp chạy lại đạt. Phải chạy các script `test_ppg_*.py` trực tiếp: chúng dùng hàm `main()`, không phải bài `unittest discover`.
- Build đủ 5 env đạt. Bản mặc định: RAM tĩnh 79.180/327.680 byte; flash 945.297/1.310.720 byte. Bản tắt hybrid dùng 56.124 byte RAM tĩnh, flash 931.861 byte. Heap cho task/queue đo riêng trên board, không cộng nhầm vào RAM tĩnh.
- Đã nạp bản mặc định 0.3.12 qua COM7, esptool xác nhận hash; lượt upload 11,253 giây. Đã kiểm tra self-test, tài nguyên, truyền dữ liệu và đo đầu ngón tay/cổ tay bên dưới. Đầu ngón tay có HR; lượt cổ tay chưa có HR hợp lệ, chưa nghiệm thu độ chính xác.

## Giữ tính đối chiếu với bước 3

Policy Python và artifact bước 3 giữ nguyên. Header `ppg_rate.h` có thêm accessor const nên hash file thay đổi; phần tính HR baseline không đổi. Kiểm native so từng kết quả khi có/không chụp cửa sổ đã đạt. Không sửa hash lịch sử để làm như bước 3 dùng bản mới.

Log `backend/storage/local/ppg-step4-build.log`, `ppg-step4-upload.log` và báo cáo parity được giữ local, không đưa dữ liệu đo cá nhân hoặc credential lên Git. CI trên GitHub chưa chạy cho thay đổi bước 4.

## Kiểm tra sau nạp, chưa yêu cầu áp tay

Trace `ppg-20261106-190103-4c7640.csv/.json`: 45 giây, 2.252 mẫu PPG, khoảng cách mẫu tối đa 20 ms, không rơi trace. Không có tiếp xúc quang (IR khoảng 764), nên HR trống là đúng.

- I2C errors 0→0; init attempts 1→1; startup overflow/gaps 48→48, discarded 79→79. Không phát sinh thêm trong lượt; không gọi là không mất mẫu từ lúc boot.
- Hybrid self-test đạt trên ESP; hai cửa sổ tổng 299.953 µs theo đồng hồ ESP, gồm thời gian bị task khác ngắt. Stack còn ít nhất 3.140 byte trong self-test. Chưa có cửa sổ đo người gửi worker nên chưa đánh giá tải phân tích liên tục.
- Heap thấp nhất 146.928 byte, loop gap tối đa 25 ms; IMU không lỗi hoặc overflow, đã lấy gyro bias. Các số này là quan sát một lượt, không phải bảo đảm lâu dài.
- WebSocket thực nhận 39 frame DEVICE/ESP32-001, firmware 0.3.12: đủ 39 GSR, 39 vector IMU; session AUTO theo boot mới. Không dùng Serial thay kênh MQTT.

## Lượt đầu ngón tay sau xác nhận

Trace `ppg-20261106-190552-5c5a54.csv/.json`: 45 giây, 2.251 mẫu, khoảng cách tối đa 20 ms, không rơi trace. Contact/settled đều 1, contact restarts 7→7, I2C 0→0, overflow/gaps 48→48 và discarded 79→79. Không tăng lỗi hoặc mất mẫu trong lượt.

- WebSocket nhận 39 frame DEVICE, 38 có HR 77,2–88,3 bpm, đủ 39 GSR và 39 vector IMU; cùng phiên AUTO. Đây là mức có kết quả trong lượt, không phải độ chính xác so với mạch tham chiếu.
- Log nguồn theo 45 lần chụp trạng thái: 3 lần chưa có HR, 1 lần fallback IR mới (source 3), 3 lần baseline IR và 38 lần baseline RED. Không quy toàn bộ kết quả cho bộ mới. Số lần chụp log, số cửa sổ được worker chấp nhận và số frame WS là ba phép đếm khác nhau.
- Worker completed 8→52, accepted 0→21; không ghi đè cửa sổ chờ. Wall time quan sát 46.934–174.936 µs/cửa sổ, gồm thời gian bị task khác ngắt; đây không phải thời gian CPU thuần. Worker stack còn ít nhất 3.140 byte, heap thấp nhất 146.928 byte, loop gap tối đa vẫn 25 ms. HR baseline tối đa 5.537 µs.
- Không khởi tạo lại cảm biến; lỗi IMU/overflow giữ 0. Counter MQTT invalid=1 có từ lượt chưa đặt tay, không tăng; fail/drop đều 0.

## Lượt mặt trong cổ tay sau xác nhận

Trace `ppg-20261106-190843-40df7c.csv/.json`: 45 giây, 2.251 mẫu, khoảng cách tối đa 20 ms, không rơi trace. Contact/settled 1, restarts 71→71; IR 94.611–100.587, RED 72.783–75.211. Có tiếp xúc quang không đồng nghĩa có sóng mạch đủ rõ.

- WS nhận 39 frame DEVICE cùng phiên, đủ GSR/IMU nhưng 0 HR. Worker completed 81→125, accepted giữ 23, queue overwritten 0. Đây là kết quả bị từ chối, không phải gói HR bị mất ở backend/frontend.
- I2C errors giữ 3, overflow giữ 74, gaps giữ 76, discarded giữ 135; init attempts giữ 10. Không tăng trong lượt. Tuy nhiên chúng đã tăng **giữa lượt đầu ngón tay và lượt cổ tay**: có 6 lần init thất bại, init tối đa 1.023 ms, loop gap tối đa 1.025 ms và recovery gần nhất 29.636 ms. Log còn lại ghi ProbeFailed tại ms=418506; chưa lưu được giao dịch gây lỗi đầu tiên của khoảng này nên chưa kết luận nguyên nhân điện/dây/thư viện. Không coi việc lấy mẫu liên tục trong 45 giây là đã giải quyết lỗi phục hồi này.
- Worker wall time quan sát 37.908–152.984 µs, max toàn boot 174.936 µs, stack còn 3.140 byte; heap thấp nhất 146.928 byte. IMU không có lỗi I2C/overflow, nhưng gaps đã tăng lên 4 trước lượt và giữ nguyên khi đo; phù hợp với việc cần xử lý chặn vòng lặp khi phục hồi PPG.

## Replay cùng dữ liệu, giữ nguyên policy

Báo cáo local `ppg-step4-local-replay.json` chấm từ giây 13 của mỗi trace, 32 cửa sổ/trace, không có nhịp tham chiếu. Không so trực tiếp mẫu số này với 39 frame WebSocket hoặc 45 dòng log.

- Đầu ngón tay: baseline 32/32; hybrid 32/32. Bộ quality độc lập nhận 12/32; hybrid vẫn giữ baseline tốt. Không có bằng chứng bộ mới làm tăng số HR ở đoạn replay này.
- Cổ tay: baseline, quality và hybrid đều 0/32. Kênh IR có 28/32 cửa sổ thiếu đỉnh, khoảng nhịp ngoài dải, bất đồng đoạn gần hoặc đỉnh quá cũ; 4 cửa sổ còn lại không đạt độ đều/hình dạng/phổ. Kênh RED cũng không đạt. Không sửa ngưỡng sau xem lượt này.
- Ở các cửa sổ tính được đủ đặc trưng của cổ tay, phần năng lượng quanh tần số nhịp và các hài chỉ khoảng 5,1–21,3% với IR, 2,0–4,4% với RED, thấp hơn ngưỡng policy 65%. Đây là chẩn đoán của bộ lọc hiện tại, không chứng minh mọi thuật toán khác đều không thể xử lý.

**Kết luận bước 4:** code C++ và tích hợp task đã kiểm chứng; lấy mẫu/truyền dữ liệu trong hai lượt đạt, đầu ngón tay có HR. **HR cổ tay chưa đạt**, lỗi phục hồi I2C giữa hai lượt cũng còn. Giữ 0.3.12 và cấu hình đã đo, không đổi LED/ngưỡng hoặc tạo số HR cho Dashboard. Đã báo người dùng thả tay sau mỗi lượt; không cần đo lặp lại khi chưa có thay đổi có căn cứ. Chưa nghiệm thu nhánh 5, chưa có đối chiếu nhịp tham chiếu hoặc CI từ xa mới.
