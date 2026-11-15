# HR theo dõi chu kỳ qua nhiều cửa sổ

**Đã có bản mới hơn0.3.20-tracker:** xem [xác nhận cú nhảy và nối thiếu ngắn có nhãn](05-HR-CONTINUITY.md). File này giữ lịch sử triển khai0.3.17–0.3.18 và kết quả ở các mốc đó.

Ngày 2026-11-07. Trung yêu cầu thử hướng mới sau khi bản demo chỉ hiện một số rồi mất. Mục tiêu trước mắt là HR ước tính cập nhật đều hơn từ dữ liệu thật, không ép về dải nhịp nghỉ và không yêu cầu sửa phần cứng/đè cảm biến. GSR/IMU giữ nguyên.

**Kết quả mới nhất:** đã hoàn tất code, build, nạp và hai lượt cổ tay. ESP đang mang **0.3.18-tracker**. Lượt cuối nhận 45 gói/45 giây, 17 gói có HR ước tính; đoạn cuối có 13 gói liên tiếp 70,3–72,2 bpm. Còn khoảng thiếu HR, chưa có tham chiếu để xác nhận sai số. Xem mục bàn giao cuối file; các cấu hình phía dưới được giữ theo tiến trình, không phải tất cả đều đang chạy.

## Cấu hình đầu, ghi trước replay

Không nới tiếp ngưỡng của `0.3.16-demo`. Tạo bộ `PpgCycleTracker` riêng, dùng chính cửa sổ đã qua bộ lọc nhân quả của sản phẩm. Một cấu hình ban đầu:

- 161 giả thuyết, 40–200 bpm, prior khởi đầu đều; không chọn sẵn 70–90 bpm.
- Mỗi giây xử lý IR/RED bằng bỏ xu hướng tuyến tính, giảm ảnh hưởng xung vượt 6 MAD quy đổi. Không sửa raw, không dùng mẫu sau thời điểm dự đoán.
- Phổ FFT512/Hann, tự tương quan tại chu kỳ ứng viên; kết hợp cửa sổ 8 giây và 4 giây theo trọng số 0,4/0,6. FFT zero-padding không tăng độ phân giải vật lý của cửa sổ.
- Điểm mỗi cửa sổ: 0,55 phần phổ cơ bản/hài, 0,45 phần tự tương quan. Hài chỉ được cộng khi phần cơ bản cũng có năng lượng; không tự chia đôi số HR vì nó trông cao.
- Cập nhật toàn bộ giả thuyết bằng chuyển tiếp Gaussian sigma 3 bpm mỗi bước 1 giây, phạm vi lân cận ±12; giữ 2% khối lượng cho giả thuyết mới. Không bám một giá trị cũ vô hạn. Đây là bộ lọc giả thuyết kỹ thuật, chưa phải mô hình xác suất đúng đã hiệu chuẩn.
- Nhận kết quả sau hai cửa sổ có bằng chứng, điểm tốt nhất ≥0,15, tương phản so với trung bình ≥0,04, điểm tại giả thuyết chọn ≥0,12 và khối lượng quanh ±8 bpm ≥0,22. Không giữ một điều kiện nghiêm ngặt riêng ở mỗi tầng như bản strict.
- Hai kênh rõ (điểm ≥0,65) nhưng bất đồng trên 12% thì không chọn tùy ý. Một kênh phẳng không được coi là phép đo độc lập thứ hai.
- Cửa sổ yếu giữ các giả thuyết tối đa hai lượt để nối lại, nhưng không phát HR mới chỉ từ prior. Flat, NaN, đổi generation, timestamp lùi/trùng hoặc gap đánh giá >1,5 giây xóa xác nhận. Sàn biên độ 4 counts và kiểm năng lượng đoạn mới vẫn giữ.

`massScore` là độ tập trung của giả thuyết, **không phải phần trăm HR chính xác**. Bản đầu ghi vào log chẩn đoán; không đổi schema của Trung để trình bày nó như xác suất y khoa.

## Kiến trúc và cách kiểm

Tính FFT/giả thuyết ở task phân tích riêng, queue latest-only, workspace cố định. Vòng đọc cảm biến chỉ chụp/copy cửa sổ. Không đưa một hàm FFT nặng vào vòng sensing 10 ms. Tạo profile firmware riêng, giữ được rollback về `0.3.16-demo` hoặc bản đối chứng.

Đã có 31 test C++ đầu tiên: dải nhịp sạch, flat/reset/clock/generation, một kênh phẳng, hài mạnh, xung đột hai kênh và đổi nhịp. Workspace tracker 16.512 byte, chưa phải số đo heap/stack/timing trên ESP.

Replay các raw đã thu, gồm hai lượt demo gần nhất, dùng C++ thực tế. So số ước tính mới, khoảng mất dài nhất và số nhảy; không lấy số giữ ở FE làm HR mới. Dữ liệu cổ tay chưa có tham chiếu nên không tính độ chính xác. Kiểm thêm nhiễu trắng/có màu, mô phỏng có nhịp gốc/hài và dữ liệu công khai có HR tham chiếu; báo cả nhận nhầm nhiễu.

Tham khảo ý tưởng theo dõi phổ trong [TROIKA](https://arxiv.org/abs/1409.5181). Đây **không phải bản port TROIKA/SSA/SSR**; không mượn kết quả sai số công bố để gọi tracker này chính xác. Bản sao nguồn trước thay đổi nằm ở `backend/storage/local/hr-tracker-before-20261107/`, không có credential.

Chưa nạp tracker, chưa yêu cầu đặt tay thêm tại thời điểm khóa cấu hình này. Trước nạp phải chốt replay, kiểm tích hợp và build; sau đó hướng dẫn một lượt tại một thời điểm, thu xong báo thả tay ngay.

## Cấu hình 1 đã chấm, chưa chọn để nạp

Sáu trace cổ tay: tracker có 173/204 ước tính mới, demo cũ 43/204. Trên mô phỏng có nhịp: MAE 1,39 bpm/17 lỗi >10 bpm so với demo 4,51 bpm/163 lỗi. Tuy nhiên tracker nhận **364/784 cửa sổ nhiễu không có nhịp** (demo 24/784); trên BIDMC01–05 đã xem, MAE 1,49 bpm/25 lỗi >10 so với demo 0,50 bpm/7 lỗi. Vì thế chưa đưa cấu hình 1 lên thiết bị chỉ để có số liên tục.

Báo cáo `backend/storage/local/ppg-tracker-development.json` giữ nguyên. Cửa sổ chồng nhau, không phải 784 phép đo độc lập; không dùng con số này để suy xác suất trên người.

## Cấu hình 2, khóa trước replay mới

Giữ không gian giả thuyết, chuyển tiếp, cửa sổ và các điều kiện nhận. Thay phép chấm bằng chứng: ước lượng nền AR(1) trên từng cửa sổ và làm trắng trước tính phổ, nhằm giảm ưu thế của nhiễu chậm. Tự tương quan vẫn tính từ sóng trước làm trắng. Kết hợp phổ và tự tương quan bằng trung bình hình học thay vì cộng độc lập, để một thành phần đơn lẻ không tự tạo số mạnh. Hệ số cộng hài là 0,35 và vẫn cần năng lượng cơ bản; đã kiểm lại ba ca hài mạnh.

Đây là cấu hình thứ hai có lý do từ lỗi quan sát, không quét hàng trăm ngưỡng. 31 test C++ vẫn đạt. Chưa có kết quả replay cấu hình 2 tại thời điểm khóa này. Báo cáo mới dùng tên `ppg-tracker-v2-development.json`, không ghi đè cấu hình đầu. Nếu cần vòng kiểm tiếp, giữ nguyên source và dùng seed 11717/11731 cùng BIDMC16–20 chưa xem trong các vòng cũ.

## Cấu hình 2 đã chấm và sửa nguyên nhân biên ở cấu hình 3

Làm trắng giảm nhiễu nhận nhầm xuống 109/784 cửa sổ, nhưng chỉ còn 67/204 cửa sổ cổ tay; MAE mô phỏng tăng lên 5,06 bpm. Không chọn theo mỗi số false-positive giảm.

Phân tích thêm phát hiện không gian giả thuyết cắt ngay ở 40 bpm có thể khiến dao động chậm hơn 40 bị chọn thành biên 40. Cấu hình 3 quay về bằng chứng phổ/tự tương quan của cấu hình 1, mở miền giả thuyết nội bộ thành 30–210 bpm, **chỉ xuất 40–200**; nếu giả thuyết trội nằm ngoài dải thì không kẹp về biên. Đồng thời tính phần giao của bin phổ với băng ứng viên, tránh bước nhảy do lưới HR1bpm nhỏ hơn bin FFT5,86bpm. Đây là sửa hành vi biên và nội suy, không chọn một dải HR nghỉ.

Giữ các tham số tracking/điều kiện nhận khác, không quét ngưỡng tiếp. Thêm hai test cho sóng 35/205bpm không được bị kẹp thành HR40/200. Cấu hình 2 có bản sao nguồn khớp hash trong `backend/storage/local/hr-tracker-v2-sources-20261107/`. Cấu hình 3 là lần cuối của vòng phần mềm này, cần ghi cả số nhận nhầm nhiễu và kết quả trên người trước khi kết luận.

## Chọn cấu hình 3 để kiểm thử thiết bị, chưa xác nhận độ chính xác

33 ca C++ đạt, gồm kiểm biên 35/205 bpm. Replay sáu raw: 117/204 cửa sổ có ước tính mới so với demo 43/204. Hai trace demo gần nhất lần lượt từ 12 lên 21 và từ 0 lên 22 cửa sổ. Mô phỏng có nhịp: MAE 0,84 bpm/13 lỗi >10 bpm so với demo 4,51 bpm/163 lỗi; BIDMC01–05 đã xem: MAE 1,02 bpm/17 lỗi >10 so với demo 0,50 bpm/7 lỗi.

**Đánh đổi còn lớn:** tracker nhận 297/784 cửa sổ nhiễu không có mạch, demo 24/784. Vì vậy chỉ chọn thử theo yêu cầu ưu tiên ước tính tương đối/cập nhật đều của Trung, không coi đây là bộ nhận biết nhịp thật đáng tin cậy hoặc nhãn chuẩn để train. Không giấu nhóm nhiễu khỏi báo cáo.

Giữ nguyên cấu hình 3, chưa điều chỉnh theo vòng kiểm tiếp. Runner bổ sung metadata phân biệt control sạch được dùng lại với seed/dữ liệu tham chiếu mới; chạy lại vào báo cáo khóa source `ppg-tracker-locked-development.json`, sau đó kiểm seed mới 11717/11731, noise11801/11813 và BIDMC16–20. Không dùng vòng này để chọn cấu hình khác. Chưa có kết quả tại thời điểm ghi đoạn này.

## Kết quả cấu hình 3 trên bộ kiểm mới

Giữ nguyên nguồn giữa development và validation. Mô phỏng có nhịp seed mới: tracker nhận 4.455/4.704 cửa sổ, MAE 1,16 bpm, 41 lỗi >10 bpm; demo 4.124/4.704, MAE 4,12 bpm và 294 lỗi. Nhiễu không tuần hoàn: tracker nhận 343/931, demo 57/931. BIDMC16–20 chưa dùng chọn cấu hình: tracker nhận 2.267/2.330, MAE 2,07 bpm/86 lỗi >10; demo 2.138/2.330, MAE 1,43 bpm/71 lỗi. Theo dõi có thể tăng coverage nhưng không bảo đảm tăng độ đúng. Chọn nạp thử theo mục tiêu demo tương đối mới, không gọi là đã nghiệm thu sai số.

Đã nạp **0.3.17-tracker**, esptool hash verified; self-test thật đạt, worker chạy riêng. Kiểm sau nạp có 5 frame DEVICE đúng phiên bản, GSR/IMU đầy đủ, cùng phiên tự động.

### Lượt cổ tay đầu trên tracker

Trung xác nhận đặt nhẹ, laptop gần; thu 45 giây rồi báo thả tay ngay. `ppg-20261107-170056-d8f67d.csv/.json`: 2.251 mẫu, 45,016 giây, complete, interval tối đa20ms, không trace dropped hoặc timestamp lùi. WS `ppg-tracker-wrist-20261107-170056-f0bd94.json`: **45 gói, 19/45 có HR**, 40–74,2bpm; GSR/IMU45/45, một phiên, khoảng nhận lớn nhất1,125giây. Không có HR tham chiếu. Một ước tính còn mới có thể xuất hiện trong hơn một gói; số gói có HR không bằng số cửa sổ tracker độc lập.

Thẻ FE có số ở38/45 gói khi tính thêm19 gói giữ số gần nhất có tuổi ≤10giây; **không gọi38/45 là HR mới**. HR còn nhảy mạnh, không nói đã ổn định. Worker hoàn tất38 lượt,21 lượt accepted, không queue overwrite; max wall78.218µs, stack còn2.612byte, heapMin151.912byte. Đây là log riêng lượt đo, không chứng minh mọi điều kiện. NET wifi/mqtt/sync giữ1, fail/drop/error0; invalid1 có trước không tăng. Không I2C/overflow/gap/clip/ALC mới trong log.

## Bản làm mượt kết quả mới 0.3.18-tracker

Giữ toàn bộ thuật toán giả thuyết cấu hình3, thêm median3 + EMA0,30 trên **kết quả tracker mới được chấp nhận**, không tính từ giá trị giữ ởFE. Khi quá3giây không có kết quả mới hoặc reset/gap/đổi generation thì xóa trạng thái smoother. Không phát HR mới ở cửa sổ yếu chỉ để đường vẽ liền. Log riêng `candidateBpm` trước làm mượt và HR sau làm mượt, để kiểm độ trễ và sai số, không đổi schema.

35 test core đạt, gồm đổi80→120bpm, theo kịp sau15lượt và reset không kế thừa số cũ. Chạy lại replay có nguồn khóa để chấm ảnh hưởng làm mượt, sau đó build/nạp bản riêng. Dữ liệu validation vừa xem giờ là hồi quy, không gọi là test độc lập lần hai. Không mở thêm cấu hình chọn chu kỳ.

Đã build/nạp0.3.18-tracker, esptool hash verified, nhận lại5frame DEVICE đúng phiên bản/GSR/IMU; chuẩn bị lượt cuối. Build dùng static RAM76.604byte, flash949.261byte, không thay profile/default_envs khác. 62testFE và build đạt; 35coretracker, 8tích hợp tracker, 8tích hợp hybrid cũ, 10selector, 6capture và 4tổ hợp header đạt. Hồi quy trước đó còn có76HR đối chứng,89driver/12snapshot schema và95parityquality. Chưa chạy CI từ xa.

Báo cáo `ppg-tracker-smoothed-development.json` và `ppg-tracker-smoothed-regression.json` lưu hash nguồn và candidate trước làm mượt. Nguồn khóa tại `backend/storage/local/hr-tracker-smoothed-sources-20261107/`. Các báo cáo cũ giữ nguyên để truy vết cấu hình; không đọc source hiện tại rồi nhận là nguồn đã dùng cho một báo cáo cũ.

## Bàn giao 0.3.18-tracker sau lượt cổ tay cuối

Trung xác nhận áp nhẹ cùng vùng cổ tay, không đè, laptop gần 30–50 cm. Đã thu đủ 45 giây và báo thả tay ngay trước phân tích; không yêu cầu đo thêm trong vòng này.

| Mục | Quan sát thực tế |
|---|---|
| Raw | `ppg-20261107-170616-259f68.csv/.json`: 2.252 mẫu/45,0 giây, complete, không lỗi capture/cleanup, dropped0, interval tối đa20ms, không timestamp lùi |
| WebSocket | `ppg-tracker-wrist-20261107-170616-fa8d3a.json`: 45 gói DEVICE, đúng `0.3.18-tracker`, một phiên tự động |
| HR trong gói | 17/45 gói có HR ước tính, khoảng70,3–85bpm; 13 gói cuối liên tiếp70,3–72,2bpm |
| Thẻ FE | Có số ở36/45 gói nếu tính thêm19 gói giữ số trước có ghi tuổi ≤10giây; không gọi cả36 là HR mới |
| Phần còn thiếu | Có đoạn11 gói liên tiếp không có HR trong telemetry. Không nội suy/lấp biểu đồ hoặc DB |
| GSR/IMU | Đủ45/45 cho cảGSR và hai vector IMU; không đổi thuật toán của chúng |
| Mạng | Khoảng nhận lớn nhất1,016giây; wifi/mqtt/sync giữ1; fail/drop/error0. invalid1 có trước và không tăng |
| Lấy mẫu | Log không tăng I2C/overflow/gap/clip/ALC; loopGap tối đa12ms trong thống kê |
| Worker | 36 request/completed,14 accepted, không queue overwrite; max wall78.254µs, stack còn2.964byte; workspace ESP17.152byte |
| Bộ nhớ | HeapMin151.976byte trong log. Không suy nhiệt độ hoặc công suất từ số này |

Log worker có14 cửa sổ accepted nhưng17 gói có HR vì telemetry có thể gửi lại ước tính còn mới trong giới hạn freshness hiện có. Không thay timestamp đo khi đọc cache. Workspace native17.168byte khác ESP17.152byte do ABI/alignment, không ghi số native thành số đo trên board.

**So sánh có giới hạn:** demo0.3.16 ở lượt trước có0/45 gói HR; tracker0.3.17 có19/45 và còn nhảy40–74,2bpm; tracker0.3.18 có17/45 và đoạn cuối đều hơn. Đây là ba lượt khác nhau, không phải cùng raw/điều kiện được kiểm soát hoàn toàn; không quy mọi khác biệt cho smoother hoặc khẳng định số70–72 là đúng nhịp thật.

[Biểu đồ ba lượt](../../backend/storage/local/ppg-tracker-hardware-comparison.png) đã xem lại, có phân biệt gói HR với thẻ giữ số và không nối đường qua khoảng thiếu. [Bàn giao máy đọc được](../../backend/storage/local/ppg-tracker-final-handoff.json) lưu hash input/source/binary và thống kê. Script tái hiện: `backend/storage/local/hr-tracker-smoothed-sources-20261107/analyze_handoff.py`.

Hồi quy bản làm mượt trên bộ đã xem: mô phỏng có nhịp nhận4.455/4.704, MAE1,33bpm/69 lỗi>10; BIDMC16–20 nhận2.267/2.330, MAE1,73bpm/78 lỗi>10. Các số này không phải sai số tại cổ tay Trung. Làm mượt có độ trễ, không luôn cải thiện sai số: ví dụ MAE mô phỏng tăng so với tracker chưa làm mượt1,16bpm. Nhiễu không mạch vẫn bị nhận343/931, và nhiễu quang tuần hoàn có thể trông như mạch; **chưa đủ điều kiện coi HR này là nhãn chuẩn để train hoặc số đo đã kiểm chứng**.

### File chính làm gì

- `include/processing/ppg_cycle_tracker.h`: giữ/phân tích nhiều giả thuyết chu kỳ, kết hợp hai kênh, xác nhận và làm mượt khi có bằng chứng mới.
- `src/sensors/ppg_hybrid_worker.cpp`: chạy phân tích ở task riêng, copy cửa sổ qua queue hữu hạn, ghi thời gian/stack; không chạy FFT trong vòng lấy mẫu.
- `src/sensors/MAX30102Sensor.cpp`: nhận đúng kết quả tracker còn mới/cùng generation; khi bật tracker thì không âm thầm thay bằng bộ đối chứng.
- `board_config.h`, `platformio.ini`: profile/version riêng; không đổi `default_envs` hoặc credential.
- `main.cpp`, `capture_ppg_trace.py`: thêm log tracker trước/sau làm mượt, không gửi debug vào schema1.1.
- `frontend/src/utils/heartRateDisplay.ts`, `Dashboard.tsx`: nhãn “Nhịp tim ước tính”, “Theo dõi chu kỳ · số đo tương đối”; giữ số tối đa10giây có tuổi nhận, không sửa telemetry hay points.
- `ppg_tracker_test.cpp`, `check_ppg_tracker.py`, `check_ppg_hybrid_driver.py`: kiểm core/hồi quy và đúng tích hợp C++, không dùng một gói JSON tự viết thay thực thi thuật toán.

Chưa kiểm ảnh Dashboard trực tiếp bằng trình duyệt tự động vì runtime không có browser khả dụng. Nhãn/trạng thái giữ số đã được kiểm bằng test render component thật; luồng DEVICE tới endpoint WS của FE đã kiểm trên phần cứng thật. Không báo browser screenshot PASS. Raw/log cá nhân nằm trong thư mục ignored.

### Dùng tiếp và rollback

ESP đã được nạp, hằng ngày vẫn mở Docker Desktop, bật đúng hotspot/Wi-Fi LAN đã cấu hình, cấp nguồn ESP và chạy:

```powershell
npm run dev
```

Không cần nạp lại mỗi lần mở máy. Đổi Wi-Fi/host trong `network_config.h` thì phải nạp lại đúng profile tracker:

```powershell
.\.venv\Scripts\python.exe -m platformio run -d ai/edge_firmware -e esp32s3_hr_tracker -t upload --upload-port COM7
```

Rollback demo cũ dùng `-e esp32s3_hr_demo`; rollback đối chứng chặt dùng `-e esp32s3_ppg_led10`. Không xóa DB/credential, không build env mặc định rồi nhận là bản tracker.

**Vòng triển khai hướng mới đã xong:** code/tests/build/nạp và hai lượt kiểm trên người. Đã có đoạn HR lên liên tiếp, **chưa đạt luôn có HR ở mọi giây hoặc xác nhận độ chính xác**. Không tự mở thêm vòng giữ tay/nới ngưỡng. Không commit/push/merge hoặc đánh nhánh5 DONE từ kết quả này. Sự kiện nóng cũ cũng chưa có phép đo để xác nhận nguyên nhân đã được xử lý.
