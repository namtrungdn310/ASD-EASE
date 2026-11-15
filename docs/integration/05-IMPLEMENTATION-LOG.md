# Nhật ký hoàn thiện nhánh 5

## Kết thúc đợt thử tham số, HR chưa đạt — 2026-11-07

- Lượt cổ tay0.3.15 sau xác nhận:45s/2.246 mẫu, timestamp16–21ms, không lỗi/gap/quá sáng; contact/guard/mạng ổn định. WS đủ39 GSR/IMU nhưng0 HR, baseline vàquality đều chưa công nhận kết quả. Đã báo thả tay.
- Kết hợp ba mứcLED vàlặp10mA: chưa có cấu hình đủ lặp lại, chưa có nhịp tham chiếu để phân biệt bỏ sót nhịp thật với loại nhiễu đúng. Không tăng LED/hạ ngưỡng hoặc tiếp tục yêu cầu đo cùng điều kiện khi chưa có căn cứ mới.
- Đã quay về0.3.13-led10/200Hz/avg4 làm đối chiếu, hash verified11,556s; kiểm20s/1.000 mẫu/max20ms và14 frame WS GSR/IMU đạt. Giữ các profile thử vàsửa clock trong repo để review/tái hiện; không chọn mặc định mới hoặc ghi HR/nhánh5 DONE. [Checkpoint vàviệc còn thiếu](05-WRIST-SAMPLING-TRIAL.md). Chưa CI/push.

## Profile400Hz/avg8 và sửa trôi đồng hồ — 2026-11-07

- Lượt lặp10mA/200Hz sau xác nhận0/39 HR, không lỗi/gap/clip/ALC, contact/guard ổn định. Không chọn mức LED từ một lượt có số, không tăng LED thêm.
- Thêm env `esp32s3_wrist_dense`, giữLED10mA vàFIFO50Hz, chip400Hz/avg8, readback0x7F/0x2F. Giữdefault vàcác env cũ. Bản0.3.14 đã nạp nhưng kiểm20s ghi gap82ms dùI2C/overflow0; chưa yêu cầu đo người ở bản này.
- Tái hiện clock lưới20ms tạo gap giả khi oscillator lệch nhẹ. Bản0.3.15 chỉ bật tracking chậm1ms/lô choPPG400Hz, không timestamp tương lai/chèn mẫu; kiểm riênggián đoạn thật vàsốmẫuFIFO. Các profile200Hz/IMU giữ clock cũ.
- PASS7 build/4 header/89 driver ở4 profile vàhồi quy. Nạp0.3.15/hash verified12,103s; kiểm55s thu2.746 mẫu, không gap/I2C/overflow, WS49GSR/IMU. Đang chờ xác nhận đo cổ tay45s; chưa khẳng định mọi nguyên nhân gap đã hết hoặc HR đã tối ưu. [Checkpoint](05-WRIST-SAMPLING-TRIAL.md). ChưaCI/push.

## Lượt12,4mA và quay về kiểm lặp10mA — 2026-11-07

- Sau xác nhận:12,4mA45s/2.251 mẫu không lỗi/gap/quá sáng, guard cho phép; WS0/39 HR, đủ GSR/IMU. IR236.378–237.660, chưa chạm rail nhưng tăng nền không cải thiện lượt này. Replay cùng policy0/32, chưa có tham chiếu.
- Đã quay về0.3.13-led10/hash verified11,938s; kiểm20s/1.001 mẫu không lỗi và14 frame WS GSR/IMU đạt. Có tiếp xúc đầu đoạn rồi hở trong lượt kiểm, chưa biết vị trí nên không tính là nghiệm thu lặp cổ tay.
- Đã hỏi xác nhận đặt lại cổ tay để đo lặp10mA45s; chưa chọn mức tối ưu hoặc đổi mặc định6,2mA của source. Không tăng LED thêm, không nới policy và chưa push/CI mới. [Checkpoint](05-WRIST-PROFILE.md).

## Phục hồi I2C và kiểm thử cổ tay 0.3.13 — 2026-11-06

- Cổ tay10mA sau xác nhận:45s/2.252 mẫu không lỗi/gap/quá sáng, WS15/39 HR79–85,1bpm và đủ GSR/IMU; còn đoạn trống. Replay cùng policy6,2mA0/32,10mA hybrid18/32, không có tham chiếu và không thay số frame thực. Đã nạp0.3.13-wrist12/hash verified12,489s; kiểm trước áp da20s/1.001 mẫu và14 frame WS đạt. Chờ xác nhận đo12,4mA, chưa chọn mức tối ưu.

- Lượt mới: cổ tay nhẹ6,2mA,45s/2.252 mẫu không tăng lỗi/gap/ALC, guard cho phép, HR chưa hợp lệ. MQTT timeout trong lượt rồi tự khôi phục13 frame WS GSR/IMU; không đổi auth/firewall hoặc yêu cầu reload. Đã nạp0.3.13-led10/hash verified23,422s; kiểm trước áp da20s/1.001 mẫu và14 frame WS đạt. Chờ xác nhận đo10mA cùng vị trí, chưa thử12,4mA.

- Thay init SparkFun nhiều giao dịch bằng state machine một giao dịch/poll; dừng ngay khi lỗi, kiểm readback/reset-timeout, giữ recoveryCause và log stepMaxUs. Không gọi lại Wire.begin hoặc đổi bus/cảm biến khác.
- Bổ sung ALC_OVF, chẩn đoán quang và motion guard dùng IMU mới/đã lấy bias; chuyển động chặn HR, sau khi yên thu lại cửa sổ. Chuẩn bị LED12,4 mA bên cạnh mức6,2/10; chưa tự chọn hoặc tự tăng LED.
- 6 build/4 header và kiểm native đạt. Mô phỏng 601/701 có case chưa giải quyết: ánh sáng tuần hoàn giống nhịp khi IMU yên. Không giấu kết quả hoặc nới policy.
- Upload đầu bị mất COM7. Trung cắm lại USB, nạp0.3.13 mặc định thành công22,026s/hash verified. Kiểm45s trước áp da:2.251 mẫu, không lỗi/gap/overflow, WS39 GSR/IMU; init148ms trải qua nhiều vòng, một bước tối đa1.438µs. IMU yên/cổng chuyển động mở. Chờ đo cổ tay6,2mA; lỗi bus cũ chưa tái hiện, chưa nghiệm thu HR/CI/push. [Checkpoint và cách tiếp tục](05-WRIST-PROFILE.md).

## Bước 4: thử hybrid C++ trên ESP — 2026-11-06

- Port policy đã chốt sang workspace cố định, task riêng và queue 1 slot; sensing không chờ phân tích. Giữ baseline khi valid, fallback chỉ cùng generation và tuổi tối đa 1.500 ms; không gia hạn timestamp từ cache.
- Đối chiếu 10.800 cửa sổ Python/C++ đạt; kiểm selector/driver, 5 build và hồi quy đạt. Thêm env tắt hybrid để đối chứng; không sửa cấu hình LED, Wi-Fi hoặc schema.
- Nạp 0.3.12 qua COM7/hash verified. Self-test ESP đạt, WS GSR/IMU đủ. Đầu ngón tay 45 giây có 38/39 HR 77,2–88,3 bpm; cổ tay 0/39, replay cùng policy cũng từ chối. Mỗi lượt thu 2.251 mẫu không tăng lỗi/gap, nhưng giữa hai lượt có lỗi I2C/6 init thất bại và loop gap tối đa 1.025 ms. Chưa nghiệm thu HR cổ tay hoặc xử lý xong phục hồi I2C; chưa CI mới. [Chi tiết](05-PPG-FIRMWARE-TRIAL.md).

## Bước 3: chốt ứng viên hybrid có kiểm chất lượng — 2026-11-06

- Đã triển khai2 policy offline được chốt trước: độ đều RR, template leave-one-out, năng lượng phổ, so8s/4s và2 lần xác nhận. Hybrid giữ nguyên HR C++ khi valid, chỉ bổ sung khi trống; không nhận HR tham chiếu làm đầu vào, không gia hạn qua gap.
- Vòng phát triển01–10: cân bằng tăng98 cửa sổ nhưng nhận nhầm1 nhiễu nên loại; mức chặt tăng64, không thêm lỗi trên10bpm và0/1457 nhiễu/phẳng. Chốt mức chặt rồi mới kiểm11–15/seed mới, không đổi cấu hình sau xem kết quả.
- Vòng mới: mức chặt tăng43 cửa sổ tham chiếu, coverage90,24→92,08%, MAE0,6234→0,6238bpm; không thêm lỗi trên10bpm,0/1457 nhiễu/phẳng mới. Các lỗi đã được baseline công nhận vẫn giữ nguyên.
- File cổ tay đầu replay6/32→13/32; file không ấn vẫn0/32, chưa có tham chiếu trên người. Chưa khẳng định cổ tay đo ổn định.
- Đã xuất đặc tả ứng viên offline có hash và thêm kiểm hồi quy: tổng76 ca công cụ offline local đạt, gồm4 ca qua bộ lọc C++ thật. Giữ6 check CI, chưa CI từ xa/commit/push; firmware vẫn0.3.11. [Báo cáo và điểm nối bước4](05-PPG-QUALITY-EVALUATION.md).

## Bước 2: đối chiếu HR offline — 2026-11-06

- Hoàn thành benchmark bộ C++ sản phẩm với bản chuyển NumPy MSPTDfastv2 có nguồn/commit/MIT. Dùng chính bộ lọc C++ chung, cửa sổ quá khứ, chặn dữ liệu cũ qua gap; không nạp/đổi firmware0.3.11 hoặc đưa dữ liệu giả lên Dashboard.
- Đã chạy4 file đo thật,10 recording BIDMC có ECG-HR và38 ca tổng hợp gồm7 HR sạch/1 phẳng/30 nhiễu. BIDMC06–10: bộ hiện tại2219/2335 cửa sổ,MAE0,46bpm; MSPTD-IR2335/2335,MAE0,75. Trên2219 cửa sổ chung,MAE lần lượt0,46/0,50; không so MAE riêng mà bỏ qua coverage.
- Cổ tay giữ cố định: replay bộ hiện tại0/32, MSPTD-IR29/32 nhưng40..112bpm, chưa có đáp án trên người. Nhiễu không có nhịp: hiện tại0/1410, MSPTD-IR1197/1410. MSPTD chỉ tạo ứng viên/chưa quality gate, chưa đủ để thay driver.
- PASS47 ca port+6 ca chấm và native harness biên dịch Werror; thêm53 ca vào AI tests hiện có, giữ6 check, không tải dataset trong CI. Chưa có CI từ xa/commit/push mới. MATLAB/Octave chưa có nên không giả đã chạy binary gốc; không claim hiệu năng ESP từ NumPy laptop.
- [Báo cáo, nguồn, cách chạy và quyết định bước3](05-PPG-ALGORITHM-EVALUATION.md). Chưa chọn bộ mới chạy production; cần đánh giá lớp chất lượng đi kèm và chống nhận nhầm nhiễu.

## Bước 1: ghi lỗi I2C 0.3.11 — 2026-11-06

- Theo thứ tự Trung chọn, bổ sung lỗi gửi/đọc thiếu byte/readback sai/probe thư viện và counter thời gian init/phục hồi. Log qua snapshot/task sẵn có, không đổi MQTT, HR hoặc LED/lịch lấy mẫu.
- PASS76 ca HR,56 ca driver/12 snapshot baseline và LED10mA,32 FIFO/39 protocol,4 header/4 build. Ca lỗi đọc→initfail→initok tái hiện6020ms bằng clock giả; chưa khẳng định là nguyên nhân lỗi cũ trên board.
- Nạp baseline0.3.11 COM7/hash verified11,199s; RAM56116B/flash931553B. Đang thu log không cần đặt tay; chưa có CI/commit/push mới. [Theo dõi bước 1](05-PPG-I2C-DIAGNOSIS.md).
- Hoàn tất quan sát45s không tiếp xúc và45s ngón tay có xác nhận: không lỗi I2C mới/init lại. Ngón tay2.251 mẫu, WS41 DEVICE/41 GSR/41 IMU/34 HR68,5..74,6bpm, không mất6s. Thuật toán không đổi (hash khớp0.3.10), không quy kết cải thiện do code chẩn đoán. Chưa có tham chiếu, chưa tái hiện nguyên nhân lỗi cũ. Giữ log; dữ liệu mới dùng đối chiếu offline ở bước2.
- Lượt cổ tay cùng0.3.11 sau xác nhận:2.252 mẫu/45s, timestamp20ms, không I2C mới/init lại/mất6s; WS41 GSR/41 IMU nhưng4 HR71,7..74,2bpm. Contact/settled giữ1, restarts không tăng trong lượt; IR chỉ qua điều kiện ở vài cửa sổ cuối, RED không đạt. HR cổ tay chưa ổn định. Đã lưu raw/log local cho bước2, chưa đổi thuật toán hoặc LED. [Chi tiết](05-PPG-I2C-DIAGNOSIS.md).
- Theo yêu cầu Trung đo lại45s, giữ cố định/chỉ đặt lên cổ tay không ấn:2.252 mẫu, không I2C/init mới hoặc mất6s; WS41 GSR/41 IMU/0 HR. Contact/settled giữ1, restarts79 không tăng; tương quan8s IR≤0,378/RED≤0,350 nên không qua cổng0,60. Giữ bằng chứng local cho bước2, không kết luận do riêng lực ép hoặc phần cứng. [Lượt lặp lại](05-PPG-I2C-DIAGNOSIS.md).

## Sửa lỗi nửa nhịp 0.3.10 — 2026-11-06

- Chẩn đoán tiếp: lấy bộ bắt đỉnh từ commit330f92c đối chiếu bộ hiện tại trên cùng 4 file đo và 4 ca tổng hợp. File ngón tay mới nhất: bộ cũ 30/39 mốc có số, bộ hiện tại 0/39. Nhiễu trắng không có nhịp: bộ cũ 58/59 mốc báo78–119bpm, bộ hiện tại0. Chưa có HR tham chiếu cho file thật, không kết luận số cũ đúng hoặc cổng mới tối ưu. [Báo cáo](05-HR-DIAGNOSIS.md); không nạp/sửa thuật toán trong lượt chẩn đoán này.

- Tái hiện ca biên độ xung xen kẽ 80→40 bpm. Bỏ điều kiện 90% đỉnh mạnh nhất, giữ ngưỡng 0,60 và các cổng kiểm tra còn lại; thêm 5 ca hồi quy. Không giữ HR cũ để làm kín biểu đồ.
- Đạt 76 ca HR, 49 ca driver/12 snapshot ở hai cấu hình LED; 32 FIFO, 39 protocol, 4 header và 4 build. Nạp baseline COM7/hash verified 11,199s, RAM 56.060B/flash 930.513B.
- Thêm công cụ đối chiếu với ECG-HR BIDMC 01–05. Kết quả và 14 cửa sổ sai lớn còn lại được ghi tại [báo cáo đối chiếu](05-PPG-REFERENCE-BENCHMARK.md). Bộ này dùng phát triển, chưa phải tập đánh giá độc lập.
- WS bản mới/phiên tự động đạt. Lượt đầu ngón tay 45s sau xác nhận: 1.942 mẫu, lỗi đọc gây khoảng mất 6.221ms; WS 41 GSR/41 IMU nhưng 0 HR. Phần đầu chưa lỗi đọc cũng không đạt kiểm tra chu kỳ. HR chưa nghiệm thu, không quy hết cho vị trí đeo hoặc thao tác của Trung. Chi tiết trong báo cáo khôi phục cảm biến. Chưa CI/commit/push mới.

## Tín hiệu yếu/hai kênh0.3.9 — 2026-11-06

- Trung yêu cầu giữ cụm cố định, chỉ sửa code. Hoàn thiện PPG200Hz/averaging4/FIFO50Hz; sàn4 counts + proxy nhiễu thay sàn50 counts; đánh giá8s/4s cho mỗi kênh và chọn IR/RED đủ điều kiện, từ chối bất đồng. Cần hai lượt nhất quán, không forward-fill/giữ HR cũ, TTL3s giữ nguyên.
- PASS71 ca HR,49 ca driver/12 snapshot schema ở baseline và LED10mA; benchmark chỉ nhiễu0/2400 cửa sổ.32 ca FIFO/39 protocol và4 tổ hợp header đạt. Replay file cổ tay cũ vẫn0 HR, không tuyên bố cải thiện đo thật từ test tổng hợp.
- Bốn build đạt: baseline RAM56060B/flash930529B, network56060B/930541B, LED10mA56060B/930545B, serial29516B/335265B. Nạp baseline0.3.9 COM7/hash verified13,544s. Chưa có CI/commit mới.
- Thử0.3.8-led10 trước đó0/30 HR,30/30 IMU, không clip/lỗi lấy mẫu mới; đã quay về baseline. Env LED10mA hiện chỉ để thử riêng, không đổi mặc định. Mời Trung đặt lại cổ tay sau nạp để đo35s. [Chi tiết](05-SENSOR-RECOVERY.md).
- Trung đã đặt lại và đo0.3.9:1.752 mẫu/35s,30 frame WS DEVICE/30 IMU,0 HR hợp lệ; contact ổn định, không tăng counter lỗi trong lượt. Xử lý HR tối đa4,93ms; không ép ra số vì chưa đủ chu kỳ và chưa có nhịp tham chiếu. Code hoàn tất phần sửa này, HR cổ tay chưa đạt; không thay phần cứng hoặc tự push/merge.

## HR theo cửa sổ0.3.8 — 2026-11-06

- Lượt che sáng:1.752 mẫu/35s,30 frame WS/30 IMU,0 HR. Contact restart tăng6 lần; chưa cô lập được tác động ánh sáng với tiếp xúc. Không có lỗi I2C/clip/gap mới. Chuẩn bị env `esp32s3_ppg_led10` riêng, firmware `0.3.8-led10`, chỉ đổi dòng6,2→10mA danh định; mặc định vẫn0.3.8/6,2mA. Test native bản thử16+49 ca/12 snapshot đạt; build/nạp/đo sẽ bổ sung sau. Xem [thử quang học](05-PPG-OPTICAL-TRIAL.md).

- Đã đo thêm mặt trong cổ tay sau xác nhận của Trung, cùng0.3.8:1.753 mẫu/35s,30 frame WS DEVICE/30 IMU,0 HR. Contact ổn định, tương quan8s tối đa khoảng0,265 trong log; không trace drop/timestamp lùi/tăng counter lỗi. Xử lý HR tối đa từ boot4,625ms. Chưa xác định nguyên nhân quang/tiếp xúc, cần ảnh nghiêng khi đang đeo trước phép thử tiếp. Không sửa/nạp firmware trong lượt này, chưa nghiệm thu HR.

- Thu sóng thô0.3.7 theo yêu cầu kiểm tra HR cổ tay chập chờn; thêm script capture35s, mặc định raw trace tắt, dữ liệu người thật lưu local bị Git bỏ qua. Trung xác nhận chưa có số HR tham chiếu.
- So sánh đầu ngón tay1.751 mẫu: có đoạn lặp rõ hơn nhưng còn biến động nền; thuật toán cũ vẫn có bước nhảy HR77,7..144,3 dù counter không tăng. Không coi log VALID là bảo đảm nhịp đúng.
- Thêm `ppg_rate.h`: cửa sổ8s, kiểm tra cả8s/4s mới nhất và phủ quyết kênh đỏ khi có chu kỳ bất đồng. Không EMA giữ số cũ, không nới TTL; ngừng SpO2 thử nghiệm. Thêm16 ca cửa sổ vào script kiểm tra driver,49 ca driver/12 snapshot và39 ca protocol đều đạt.
- Ba build đạt, header4 tổ hợp đạt. Nạp COM7 thành công11,220s/hash verified; static RAM52804B, flash929961B. Network-check flash929973B, serial-check RAM26260B/flash334641B. Không tuyên bố CI mới hoặc nghiệm thu HR cổ tay.
- Replay tín hiệu thật vẫn từ chối phần lớn cửa sổ, không chỉnh ngưỡng để ép hiện số. Sau nạp, Trung đặt lại đầu ngón tay:1.753 mẫu/35s,30 frame WS DEVICE,7 HR73,2..78,8,30 IMU; xử lý HR tối đa4,1ms. Cổ tay cùng bản:1.753 mẫu/35s,30 frame/30 IMU nhưng0 HR; xử lý tối đa4,233ms. Các counter lỗi không tăng trong hai lượt, lỗi startup vẫn giữ. Replay bỏ điều kiện biên độ vẫn không đạt chu kỳ, không sửa firmware theo thí nghiệm. Chưa có tham chiếu, chưa nghiệm thu HR cổ tay. Bước tiếp: so sánh mặt trong cổ tay. Chi tiết [khôi phục cảm biến](05-SENSOR-RECOVERY.md).

## HR đứt đoạn0.3.6 — 2026-11-06

- Trung báo HR hiện rồi mất. WS0.3.5 có6/15 frame HR,15/15 IMU; log cho thấy kiểm tra đơn ngưỡng50000 xóa lịch sử nhịp khi tín hiệu cổ tay đi dưới ngưỡng. Nền ngoài da đo≈500..1000; cổ tay từng có28k..49k.
- Tách nhận/mất tiếp xúc10000/6000, debounce mất100ms, chờ ổn định1s và loại bước DC>15%/mẫu trước bắt nhịp. Không nới TTL3s, không giữ số cũ giả live. Thêm contact/settled/restarts/beats vào Serial.
- Driver46 ca/11 snapshot schema, FIFO32/core39 đạt; nạp0.3.6 COM7/hash verified. Log đầu sau nạp contact0/IR≈630; chưa chứng minh HR cổ tay ổn định. Vẫn giữ counters startup overflow/gap/discard, chưa kết luận mất mẫu bằng0. Chi tiết [khôi phục](05-SENSOR-RECOVERY.md).

## Sửa sau khi nạp0.3.2 — 2026-11-06

- Trung báo chỉ GSR có số. Đọc Serial thật, không reset khi mở monitor: IMU trả WHO_AM_I0x74, bản0.3.2 chặn vì chỉ nhận0x68; PPG n=0 do OVF giữ1 và vòng reset3s trước pop đầu. Wifi/mqtt/sync vẫn1.
- Bổ sung profile6515 bằng driver InvenSense gốc (ACCEL_CONFIG2/FIFO/readback), giữ ID lạ bị chặn và không áp sai công thức nhiệt6050. Đọc metadata PPG riêng và thử rollover không đủ; sửa tiếp thành pop/bỏ lô overflow rồi bắt lại, không reset chip lặp mãi.
- Bản cuối0.3.5 đã nạp COM7/hash verified. PPG/IMU có cửa sổ450 mẫu/8,992s≈50,04Hz; IMU bias chốt và hai vector qua WS thật. PPG đã có lúc VALID rồi mất khi IR xuống≈500; chưa có tham chiếu, chưa nghiệm thu HR cổ tay. Đang hướng dẫn Trung áp đúng ô kính.
- Trung hỏi vì sao đứng yên số vẫn dao động: giải thích noise/offset, gravity và trục chart tự co; không ép gyro về0 hoặc che sai lệch norm gia tốc≈10,07.
- Build3 env đạt (4,030/10,011/9,099s), FIFO32, driver41/11 snapshot/schema và core39 đạt; giữ kết quả backend/frontend của lượt trước vì không sửa phần đó. Chi tiết [khôi phục cảm biến](05-SENSOR-RECOVERY.md). Chưa push/CI/merge.

## Tối ưu code theo yêu cầu đã làm rõ — 2026-11-06

- Trung yêu cầu tối ưu **code**, không chờ sửa vỏ. Hoàn thiện firmware0.3.2: FIFO và readback cấu hình cả PPG/IMU, clock/lịch giữ pha, phát hiện gap/overflow/clipping/ngưng mẫu, log định kỳ chạy task thấp với queue1.
- PPG bỏ chặn cố định360/400ms và half-RR; lọc4Hz, trung vị5/EMA0,35 để giảm độ trễ. Không tự tăng LED hoặc hạ ngưỡng nhận da khi chưa đo. IMU50Hz/FIFO/DLPF10Hz, lấy lệch gyro khi đứng yên; giữ raw trước bù/EMA. Chỉ nhận ID6050 được hỗ trợ.
- GSR dùng eFuse ADC, không còn raw×3300/4095; baseline từ điện áp trước EMA, kiểm tra ổn định. Mô hình điện dẫn chưa hiệu chuẩn bị khóa mặc định: raw tiếp tục lên FE, delta null, không gắn nhãn SCR giả.
- 37 ca driver C++ sản xuất với fake ngoại vi và10 snapshot qua runtime schema; FIFO28, core39, backend111, frontend60/build và9 nhóm native MQTT/backend/WS đạt. Ba env và4 tổ hợp header đã đạt; ghi kết quả cuối sau cập nhật default_envs trong05-WRIST-MEASUREMENT.md.
- Đã thêm kiểm tra driver vào cùng job Firmware build, giữ nguyên6 tên check. Chưa push/CI/merge, chưa nạp. Hai file schema local của Trung giữ nguyên hash. Chi tiết tại [chuỗi đo](../contracts/SENSOR_ACQUISITION_0_3_2.md); sau bàn giao code hướng dẫn nạp rồi đo từng bước, không gọi cấu hình là tối ưu tuyệt đối.

## Đo tại cổ tay — 2026-11-05

- Trung yêu cầu tối ưu theo từng bước với MAX30102 ở cổ tay, GSR ở hai ngón tay. Theo dõi riêng tại [05-WRIST-MEASUREMENT.md](05-WRIST-MEASUREMENT.md); chưa đổi LED, ngưỡng, bộ lọc hoặc cách quy đổi GSR khi thiếu phép đo.
- Sửa đường đọc PPG để tránh ring 4 phần tử SparkFun: decoder FIFO phần cứng có burst tối đa 30 byte, kiểm tra I2C/overflow/reset, bỏ lô lỗi và bắt lại HR. Thêm `[PPG-DAQ]` cho số mẫu, khoảng poll, gap/overflow/clip và IR/RED/AC.
- Bản chuẩn bị 0.3.1: bỏ cờ build đè phiên bản 0.2.0, pin SparkFun 1.1.2. MQTT/schema/phiên tự động giữ nguyên. C++ FIFO 28 ca, protocol/schema 39 ca, 4 tổ hợp header và hai env PlatformIO đạt; chưa có CI mới, chưa nạp board.
- Ảnh mặt áp da cho thấy bo và đầu nối hướng ra da; cần mặt đỡ cách điện và cửa sổ quang, xác nhận mắt cảm biến không bị linh kiện khác kê cách da trước khi thử. Chờ Trung chỉnh gá/xác nhận, sau đó hướng dẫn nạp và đo từng bước. COM7 được tìm thấy; chưa mở Serial hay reset ESP trong lượt này.

## Tiếp tục ngày 2026-11-05

- Trung yêu cầu phiên mở tự động cùng npm run dev, không dùng nút. Launcher bật đúng target DEVICE trong backend.env local; backend chờ sync rồi tạo một START mỗi boot, dùng luồng command/ACK hiện có. Browser chỉ GET trạng thái và WS, không tự Start/Stop. Đã bỏ hướng nút chưa bàn giao và chuyển SessionControl thành hiển thị thuần.
- Đã bật/chạy backend trên máy Trung: trước đó ESP32-001 chưa có phiên, sau cập nhật tự tạo AUTO-…/RECORDING với ACK thật. Cursor DB thuộc session mới, cookie→WS nhận3 frame DEVICE timestamp tăng. Không POST Start bằng công cụ thử hoặc browser để làm bằng chứng tự động. Xem05-AUTOMATIC-SESSIONS.md; raw/export vẫn chưa hoàn tất.
- Kiểm thử cuối lượt phiên tự động: backend111 và frontend60 tests/build đạt; có concurrency chống tạo đôi, không lặp sau timeout/Stop, cùng boot giữ phiên và boot mới tách phiên. Giao diện không có nút Start/Stop; browser không tạo session.

- Theo yêu cầu mới: badge thiết bị có Đã kết nối chỉ khi live; waiting/stale/backend_disconnected đều Chưa kết nối, giữ lý do chi tiết và cơ chế tự phục hồi. Thêm khung Dự đoán AI luôn hiện gồm trạng thái/xác suất/lịch sử, chờ khi modelnone và đọc prediction/model_version hiện có khi có mô hình. Không sinh dự đoán giả, không lấy kết quả cũ làm hiện tại.
- Giao diện dùng hết chiều rộng viewport: bỏ max-width1280px, bốn ô cùng hàng từ1600px, hai cột ở màn hình vừa và một cột ở mobile. Khung AI cũng chuyển hai phần sang xếp dọc. Frontend58 tests/build PASS; HTTP các module và3 frame DEVICE schema1.1 thật đạt, chưa có mô hình trên board. Browser runtime không khả dụng nên chưa xác nhận ảnh/bố cục viewport thật. Không cần nạp firmware cho thay đổi UI này.

- Trung báo mới mở Dashboard đôi khi đứng Chờ dữ liệu, phải hard refresh. Bổ sung deadline mở phiên/WS, heartbeat ping/pong, renew cookie trước reconnect, khôi phục online/pageshow/visibility và backend đóng subscriber lỗi. Tests tái hiện3 ca frontend/2 ca backend FAIL trước sửa; frontend54/backend101/build PASS sau sửa. Không khẳng định đã tái hiện đúng phiên browser của Trung.
- Sau rebuild backend,6 kết nối cookie mới nhận frame DEVICE đầu0,375..0,985 giây kể từ WS open; tất cả ping có pong.12 gói thật tiếp theo cách nhau1002 ms. Browser runtime không khả dụng; ghi rõ phân biệt bằng chứng DOM/HTTP/WS và trình duyệt thật tại05-REALTIME-RECOVERY.md. Không đổi firmware hoặc dữ liệu giả làm DEVICE.
- Hồi quy native C++ qua broker/backend/API/DB/WS cô lập đạt9 nhóm, thêm heartbeat trước Start; giữ các bài ACL/restart/StartStop và trục telemetry1.1.

- Làm lại toàn màn hình theo yêu cầu Trung: logo/header gọn, bốn ô số đo gắn biểu đồ, bộ style thống nhất và thông tin phụ thu gọn. Chữ ngắn; bỏ đoạn hướng dẫn/đơn vị lặp, quality chưa ước lượng không hiển thị0% như lỗi, DEVICE chưa model không dựng biểu đồ xác suất rỗng. Trang mở phiên/lỗi cùng kiểu với Dashboard. Xem docs/design/DASHBOARD.md.
- Kiểm tra UI mới: frontend46 tests/DOM/StrictMode và build đạt; các màu chữ đã tính tương phản>=4.72:1. HTTP giao diện/CSS/module và cookie→WS còn nhận3 frame DEVICE schema1.1 với hai vector. Ảnh Trung trước đổi bố cục đã xác nhận các trục thật hiển thị; không yêu cầu nạp thêm cho lượt UI này. Browser runtime list rỗng nên chưa chụp/đo bố cục375/768/1440px hoặc dùng screen reader.

- Theo yêu cầu số chính dễ theo dõi: mỗi ô IMU có độ lớn sqrt(x²+y²+z²) nổi bật và ba trục có dấu bên dưới. Tính tại frontend từ snapshot, giữ m/s²/degrees/s và chú thích trọng lực; null không thành0. Không đổi gói MQTT hoặc yêu cầu nạp thêm chỉ cho thay đổi trình bày này.

- Trung yêu cầu tách riêng: thêm telemetry1.1/firmware0.3.0 với movement.acceleration và angular_velocity sau EMA. Dashboard thay điểm tổng hợp bằng hai ô sáu giá trị và hai biểu đồ, giữ dữ liệu1.0 cũ. Các schema local có sẵn của Trung không bị sửa; model1.1 nằm trong schemas/imu.py. Backend99 tests, frontend44/build, native39/schema, firmware2 env/header4 đạt. Backend trên máy Trung đã build/chạy lại, chờ nạp0.3.0 và kiểm tra board thật.
- Native C++→Mosquitto/backend/WS thực đạt8 nhóm, gồm xác nhận sáu trục1.1 âm/0 đúng đơn vị, cùng Start/Stop/lặp/ACL/restart; đầu vào harness là SYNTHETIC, không thay board. Sau rebuild backend, probe nhận3 frame DEVICE thật vẫn schema1.0/firmware0.2.0, xác nhận tương thích và chưa có trục trước khi nạp0.3.0. Công cụ browser không có kết nối, chưa kiểm tra trực quan giao diện hai nhóm mới.

- Trung nạp bản chẩn đoán thành công11.12 s/hash verified và gửi ảnh Dashboard đã có HR/GSR, trạng thái tiếng Việt. Xác nhận luồng ESP→MQTT→backend→WS→Dashboard hiển thị thật; chưa coi số HR là đã hiệu chuẩn. Không cần tiếp tục giữ ngón tay chỉ để debug NO_FINGER khi HR đã lên.
- Theo yêu cầu chuyển động chưa lên, bổ sung motion-rms-v1 ở firmware0.2.1: RMS gia tốc lệch1g + con quay trong50 mẫu, quy đổi0..1; có warm-up, reset lỗi/gap/bão hoà, kiểm tra freshness. Định nghĩa tại contracts/MOVEMENT_SCORE.md. Native C++37 tests/schema runtime và build2 env đạt. Chưa nạp0.2.1/chưa nghiệm thu giữ yên và xoay/rung trên board; không ghi phần này hardware PASS.

- Dashboard đổi nhãn trạng thái sang tiếng Việt, thêm giải thích khi HR/điểm chuyển động chưa có và khi thiết bị chưa chạy AI. Frontend41 tests và build đạt.
- Kiểm tra HR trực tiếp: cửa sổ đầu25 s có25 NO_FINGER; sau khi Trung xác nhận đèn đỏ sáng và đặt lại tay, cửa sổ35 s vẫn có35 NO_FINGER, IMU35 VALID. Cùng lúc WS nhận35 frame ESP32-001, HR và movement đều null. Chưa có bằng chứng lỗi truyền HR; driver chưa nhận diện tiếp xúc. Không đổi ngưỡng/thuật toán để làm xuất hiện số.
- Trước bản0.2.1, firmware chưa tính movement.score: serializer gửi null theo contract, không thay bằng gia tốc m/s² hoặc số giả. MPU6050 VALID không đồng nghĩa đã có điểm0..1.
- Bổ sung IR/RED/ngưỡngIR vào Serial ở trạng thái NO_FINGER để chẩn đoán tiếp xúc/ngưỡng ở bước tiếp. Build cả2 env đạt. Không đổi schema MQTT, GPIO hoặc lịch mạng; cần nạp firmware mới trước khi đọc được log này. Chưa xác nhận nguyên nhân phần cứng hay ngưỡng chưa phù hợp.

- Theo yêu cầu mới, bỏ thao tác DevTools/token: npm run dev ở root/frontend tự chuẩn bị/reuse local theo header, bật broker/backend và Vite. Bridge Node giữ token ở server, chỉ cấp cookie HttpOnly cho localhost; App tự mở/gia hạn phiên. Hướng dẫn cùng cách Trung/Tân tại05-ONE-COMMAND-DEV.md.
- Đã chạy2 entry và stop/start trên máy Trung; auto-session lấy cookie rồi nhận3 frame DEVICE thật, cả sau restart. Chưa có browser tool để xác nhận UI, chưa chạy máy Tân. Backend77 tests, frontend41, build/audit0 đạt; Vite cập nhật8.3.6 sửa advisory dev server.

- Trung gửi ảnh PPG VALID/có HR, GSR/IMU VALID; chủ đích smoke test, chưa giữ đo ổn định. Chuyển sang đăng nhập cookie trên Dashboard. Ảnh mới có loopGap106 ms (heapMin202632/stackWater3780 byte), cần giữ là điểm kiểm tra F17; không gộp với cửa sổ uptime khác hoặc kết luận zero-loss.

- Đã có Serial thật từ Trung: cửa sổ24.1 s,25 NET lines, wifi/mqtt/sync1, các counter lỗi/drop0, pending/outbox0. HeapMin201764/stackWater3780 byte, loopGap10 ms; processed rates xấp xỉ50.08/49.75/19.92 Hz. Chưa đủ F17 do thiếu baseline và ca mất mạng. GSR/IMU driver VALID, PPG NO_FINGER; chuyển sang kiểm tra MAX30102 khi đặt ngón tay. Raw log giữ local bị Git bỏ qua.

- Trung đã nạp env esp32s3_supermini qua COM7, SUCCESS21.78 giây/hash verified. Sau reset backend MQTT connected/sync1. Probe WS qua cookie nhận3 frame thật DEVICE/ESP32-001/session=null, timestamp tăng, khoảng1002 ms. Bằng chứng nhỏ được lưu trong thư mục credential local bị Git bỏ qua; chưa có ảnh Dashboard, đo3 driver hoặc Start/Stop thật.

- Trung đã điền Wi-Fi trong header local; đã kiểm tra không in secret và đối chiếu credential MQTT, broker/IP hiện tại. Build esp32s3_supermini networking-enabled đạt (RAM47180 byte, flash915953 byte). Dịch vụ vẫn healthy/sync0; chuyển sang hướng dẫn Trung upload COM7, chưa có kết quả nạp.

- Trung đã nối laptop vào hotspot iPhone/5G Viettel: laptop172.20.10.3, gateway172.20.10.1. Tạo bộ credential local esp32-trung, account ESP32-001 riêng và header network_config.h (chờ Trung điền2 trường Wi-Fi).
- Compose project asd-ease-esp32-trung: broker172.20.10.3:1883, backend127.0.0.1:8000 healthy; account backend/esp32 đăng nhập MQTT đạt, backend MQTT connected/sync0. Login HTTP/WS cookie qua dịch vụ thật đạt. Không gửi gói đo giả; ESP chưa được nạp cấu hình mới. Frontend đang có tại localhost5173 đúng dự án.

- Bước dây/nguồn: Trung xác nhận GPIO đúng cấu hình,3 cảm biến đều3V3 và chung GND. Chuyển sang chọn LAN; chưa mở broker hoặc lưu mật khẩu Wi-Fi. Chưa có bằng chứng đọc cảm biến thật.

- Bước đọc chip/flash đã đạt theo output Trung gửi: ESP32-S3 QFN56 rev0.2, flash4 MB XMC, embedded PSRAM2 MB/AP_3v3, crystal40 MHz, USB-Serial/JTAG; eFuse flash Quad/3.3 V. Chưa nạp firmware mới; tiếp tục đối chiếu dây/VCC/GND của3 cảm biến.

- Bước USB đã đạt: Trung gửi kết quả USB Serial Device COM7, VID:PID303A:1001. Chuyển sang đọc chip/flash bằng esptool; chưa nạp firmware.

- Base dev46d4e2d sau PR #17, nhánh `fix/esp32-local-mqtt-integration`.
- Trung đã có ESP32-S3 Super Mini và 3 cảm biến, đang cấp nguồn qua USB ở quán cà phê. Serial/PnP chưa thấy ESP; chờ kiểm tra cáp/cổng để nạp. Chưa chạy radio/cảm biến thật.
- Đã phân tích thay đổi Tân, sửa đường telemetry/sync/DB/WS và auth. Giữ chẩn đoán Wi-Fi và cấu hình cổng/bind local. Chi tiết tại [rà soát PR #17](05-REVIEW-PR17.md).
- Kết quả local cuối: backend72, protocol C++30, frontend26/build, firmware2 env/header4 và Compose config đạt. Native C++ → Mosquitto/API/DB/WS đạt7 nhóm với login/cookie HttpOnly như browser; gồm Start/Stop và restart backend/broker. Chưa có CI cho lượt sửa local này.
- Tiếp tục cùng Trung từng bước tại [05-LOCAL-BRINGUP.md](05-LOCAL-BRINGUP.md). Không nạp khi chưa xác nhận COM/board/flash; chưa ghi HW PASS.

## Nhật ký trước đó - 2026-11-03

Ngày 2026-11-03. Nhánh `feature/firmware-telemetry-client-completion` từ dev `1e73aea` (PR #14 của Tân), sau backend04 `7ff5a2c`.

## Phạm vi và bằng chứng

Trung yêu cầu hoàn thiện phần code còn thiếu. Board/cảm biến hiện ở chỗ Tân; discovery serial trên máy này không có thiết bị. Chỉ xác nhận build/tests/tích hợp phần mềm; phần cứng ghi WAITING_HARDWARE.

Giữ thay đổi GPIO MPU SDA5/SCL11 của Tân, PPG8/9 và GSR7; không tự đổi lại dây hoặc thuật toán lọc. Giữ hai thay đổi định dạng schema local và prompt chưa commit của Trung.

## Rà soát PR #14

- Đã có serializer và điểm tích hợp vào main, nhưng publish ba topic `asd/v1/devices/.../sensors/*` khác contract `asd-ease/v1/DEVICE/.../telemetry`.
- Transport đợi Wi-Fi tới8 s trong loop sensing; queue16 snapshot và flush backlog; chưa subscribe/state/Start/Stop/ACK.
- PubSubClient không đáp ứng publish QoS1 cho control. Chuyển sang ESP-MQTT có sẵn trong Arduino/ESP-IDF đang dùng, pin platform; build cả nhánh network-disabled và network-enabled.
- Serializer chưa có tuổi mẫu, quality gán0.9/1 và mapping CALIBRATING/GSR chưa khớp quy ước.
- mqtt_subscriber.py mới là đường gom topic khác contract, chưa được main khởi động; nếu nối vào sẽ bỏ qua registry/boot/phiên và còn broadcast khi DB lỗi. Loại bỏ đường thử chưa dùng này, dùng receiver04 có xác thực/nghiệp vụ chung; giữ tests hồi quy và thay tests cho đường bị bỏ bằng kiểm tra chặn topic cũ.

## Các mốc

- [x] Đọc diff Tân, code/contract, kiểm tra môi trường và tách nhánh; hỏi vị trí board.
- [x] Core C++ portable: control/lease/epoch/chống trùng, serializer/freshness, native harness xuất JSON thật.
- [x] ESP-MQTT QoS1/task mạng riêng, queue hữu hạn/latest-only, SUBACK/LWT/TLS/reconnect, tích hợp sensing.
- [x] Cấu hình DEVICE/ACL/profile và LAN; bỏ đường subscriber khác contract.
- [x] Native tests/fixtures qua Pydantic; harness C++ qua broker thật → backend/DB/WS, các lỗi và hồi quy.
- [x] Build firmware hai chế độ, backend/AI/frontend, hướng dẫn05/ma trận nghiệm thu cho Tân.
- [ ] Tân nạp/đo cảm biến thật, LAN/Dashboard, StartStop/lỗi/tài nguyên trên ESP32; board chưa ở máy Trung.
- [x] Trung yêu cầu đưa code vào dev: commit d1101c5, push và mở [PR #15](https://github.com/namtrungdn310/ASD-EASE/pull/15). CI/review/merge theo kết quả trên head cuối của PR; local không thay CI.

## Kết quả chạy local

- PlatformIO2 env đạt, header4/4; native C++30 tests qua Pydantic runtime.
- Hai bài MQTT (core C++ và simulator Python) đều đạt7 nhóm qua Mosquitto thật; account DEVICE riêng bị chặn khi publish vào topic SYNTHETIC khác.
- Backend61, AI15, frontend26/build/audit0; HTTP transport19 frame đạt. Compose config --quiet đạt.
- Đã bổ sung timeout SUBACK, dừng retry khi CONNACK/quyền/chứng chỉ sai, thống kê outbox/lỗi; log ID/boot/connection/phiên và Serial dùng cùng ID MQTT. Build lại cả hai env đạt.
- Pin platform7.1.3/ArduinoJson7.4.3/C++17; SDK ESP-MQTT có sẵn đã link đủ nhánh TLS. Chưa thử handshake TLS/đồng hồ trên board.
- Chỉ kích thước static: mạng tắt RAM20636/flash322293 byte, build-check mạng RAM47180/flash913889 byte. Không xem đây là số đo RAM runtime.

Tài liệu vận hành ở [05-SETUP](05-SETUP.md), giải thích file ở [05-HANDOFF](05-HANDOFF.md), ma trận phần mềm/phần cứng ở [05-VERIFICATION](05-VERIFICATION.md). Phần code READY_FOR_REVIEW, nghiệm thu WAITING_HARDWARE; không đóng phase07.

## Điểm kỹ thuật phải giữ khi tiếp tục

- Telemetry nguồn DEVICE thật trên board; fixture native/SYNTHETIC phân biệt rõ, không giả phần cứng.
- Control1.0/telemetry1.0; topic/QoS/retain theo MQTT_CONTROL.md; backend kiểm tra ACK nonce hiện hành.
- Không có raw ở05: STOPPED summary zero/cutoff0/raw_recording_enabled=false, complete=false.
- Mạng không chạy chờ trong sensing. Callback chỉ xếp gói có giới hạn; worker duy nhất xử lý state; snapshot copy nhất quán.
- Boot mới sau reboot, connection mới trước CONNECT/LWT, request mới mỗi sync. Epoch không reset khi reconnect/lặp lệnh.
- Chưa có board: không nạp, không ghi tốc độ/RAM chạy thật hoặc ảnh Dashboard thật đã PASS.

Nguồn kiểm tra API: [ESP-MQTT IDF4.4.7](https://docs.espressif.com/projects/esp-idf/en/v4.4.7/esp32s3/api-reference/protocols/mqtt.html), header mqtt_client.h và libmqtt.a thực có trong framework cài trên máy.
