# Không trộn HR giữa hai chu kỳ đã đổi

**2026-11-09:** firmware hiện nạp là `0.3.27-tracker`, chỉ bổ sung điểm chất lượng
cho bốn card qua telemetry1.2. Lõi chọn chu kỳ/lọc/làm mượt HR vẫn như0.3.26,
chưa nghiệm thu độ chính xác cổ tay. [Công thức và giới hạn của điểm](../contracts/MEASUREMENT_QUALITY_V1_2.md).

## Hiện tại: 0.3.26 đang thử, HR cổ tay chưa đạt

Lượt thật0.3.25 vừa hoàn tất:2.252 mẫu/45giây,45góiWS, chỉ3gói HR107,9 rồi54,0/53,6. Contact/motion allowed đủ45snapshot, không lỗiI2C/FIFO/ngắt mạng mới. Worker hoàn thành44cửa sổ trong khoảng log, xử lý tối đa334.878µs, stack còn2.788byte, không ghi đè queue. Lượt này **không đạt mục tiêu HR ổn định**. Replay nguội cùng raw:0.3.24 nhận5/34cửa sổ40,9–55,2;0.3.25 bỏ toàn bộ, không khôi phục HR. Khác trạng thái trước lúc capture nên replay không được coi là tái hiện nguyên trạng ba số live. FE nhận đủ45gói,3gói đo và19gói tạm tính; dữ liệu gốc giữ nguyên. Không gán mốc đếm tay105–115 của lượt trước cho lượt này.

Sau lượt này có ca tái hiện lỗi trạng thái độc lập: theo dõi108bpm, một cửa sổ phẳng, rồi dao động54bpm. Core0.3.25 quên lịch sử ngay ở cửa sổ phẳng và bỏ mất cổng xác nhận nửa nhịp.0.3.26 giữ lịch sử có giới hạn qua cửa sổ yếu, xóa confirmation/jump đang chờ, không phát HR cũ; sau15cửa sổ yếu vẫn reset, clock/generation đổi vẫn reset như cũ. Cổng6lần xác nhận nửa/gấp đôi và3lần nhảy lớn giữ nguyên. Ca mới chứng minh không nhận54ngay sau một lần yếu, nhưng vẫn nhận được54thật khi tín hiệu mới tồn tại đủ lâu. Không khẳng định đây là nguyên nhân duy nhất của ba số live vì chưa có reference/tái hiện toàn trạng thái.

Vòng seed55021/55037 so0.3.25→0.3.26: nhiễu không tuần hoàn nhận47→46/637; mô phỏng có nhịp giữ4.073/4.704 và0lỗi lớn. BIDMC đã xem:9.102→9.107/9.320 kết quả, lỗi lớn34→31, MAE0,657→0,636bpm. Nhiễu quang tuần hoàn vẫn96/98.46ca core+20toàn dải+46hình dạng đạt;8ca tích hợp,89ca driver/12snapshot và4tổ hợp header đạt. Sửa lần này giữ nguyên cổng chất lượng/hình dạng của0.3.25. Không dùng tuổi/nhịp đếm tay làm prior.

Đã build/nạp0.3.26 cho lỗi trạng thái này và nhận5gói DEVICE đúng phiên bản quaMQTT/backend/WS; self-test worker đạt. Đây là kiểm nối lại, chưa đo chính xác trên cổ tay0.3.26. Các kết quả phần mềm không thay nghiệm thu cổ tay. Không mở thêm lượt đo người trong vòng này. Nguồn, binary, dữ liệu và phép so khóa ở `hr-cycle-selection-20261108/`; source trước0.3.25 giữ riêng. Chưa commit/push/merge. Phần0.3.25 và cũ hơn bên dưới là lịch sử; số đúng về hình thức không đồng nghĩa HR đúng.

## Bản thử 0.3.25 — bằng chứng hình dạng khi chọn chu kỳ

Đã chuyển trọng tâm từ làm mượt sang chọn chu kỳ. Mỗi ứng viên30–210chu kỳ/phút được chấm riêng trên IR/RED: chia phần cuối cửa sổ thành các chu kỳ, nội suy16 điểm/chu kỳ, bỏ DC và chuẩn hóa biên độ, rồi tính tương quan với template gồm các chu kỳ còn lại. Chu kỳ đang chấm không góp vào template của nó. Lấy trung vị để bớt phụ thuộc một xung lỗi. Đây là phép chấm kỹ thuật tự thiết kế, không phải xác suất đúng hoặc triển khai MSPTD.

Điểm phổ/tự tương quan cũ được nhân với `0,25 + 0,75 × độ lặp hình dạng` ở cả cửa sổ8giây và4giây. Chỉ giảm bằng chứng thiếu nhất quán, không cộng một nguồn điểm mới cho nhiễu. Miền HR xuất40–200 và các cổng/nhịp lấy mẫu/LED giữ nguyên. Smoother0.3.24 giữ nguyên; FE không được điền thêm dữ liệu. File chính: `processing/ppg_cycle_shape.h` và `processing/ppg_cycle_tracker.h`; workspace mới cố định1.832byte ở task phân tích.

### Kết quả trước khi nạp

Khóa ứng viên trước khi chạy seed44039/44051. Mô phỏng có nhịp: lỗi trên10bpm giảm5→0, MAE0,639→0,204bpm; số cửa sổ được nhận giảm4.434→4.130 trên4.704. Mô phỏng nhiễu không tuần hoàn: nhận nhầm giảm197→49/637, chưa bằng0. Nhiễu quang tuần hoàn vẫn bị nhận96/98 ở cả hai bản, là giới hạn chưa giải quyết.

20 bản BIDMC đã xem, không phải kiểm độc lập: lỗi lớn76→34, MAE0,874→0,657; số cửa sổ được nhận9.142→9.102/9.320. Tất cả CSV đối chiếu hash manifest nguồn. Đây là so với HR monitor theo cửa sổ, không phải F1 từng nhịp hoặc sai số tại cổ tay Trung. Các cửa sổ chồng lấn không độc lập.

Raw lượt khoảng115bpm được nhận20/21 cửa sổ replay,111,5–116,1bpm; khoảng105–115 đếm tay chỉ là đối chiếu gần đúng của lượt đó. Raw lượt sai0.3.24 bị bỏ toàn bộ34 cửa sổ: đã ngừng phát số41–44 trên raw này, **chưa khôi phục được nhịp thật từ sóng đó**. Raw nhiễu trước nữa vẫn còn10/34 cửa sổ40,5–44,8 không có nhịp tham chiếu; không tuyên bố hết lỗi chọn nhầm. Lượt raw70–80 giữ31/34 cửa sổ.

45ca core+20ca toàn dải+46ca hình dạng đạt, cùng8ca tích hợp,89ca driver/12snapshot,6ca capture và4tổ hợp header. Test hình dạng chạy thêm với assertion biên của thư viện chuẩn. Nguồn tích hợp cho đầu ra replay giống prototype trên4 raw giữ lại; không đổi driverGSR/IMU, bộ lọc đầu vào, motion guard, schema, utility dự báo FE hoặc credential. CI hiện có chạy cả111ca core/range/shape qua `check_ppg_tracker.py --unit-only`; chưa có CI GitHub mới.

Đã build/nạp0.3.25 và nhận5frame DEVICE thật quaMQTT/WS. Worker self-test đạt, workspace ESP19.040byte, stack còn2.996byte; hai cửa sổ self-test tổng604.344µs. Chưa coi đây là số đo khi thu cảm biến thật hoặc xác nhận vấn đề nhiệt. Bằng chứng/rollback cục bộ ở `hr-cycle-selection-20261108/`; chưa commit/push/merge. Chỉ bắt đầu lượt cổ tay mới sau xác nhận sẵn sàng của Trung; không tự ghi PASS.

## Lịch sử 0.3.24

**Kết luận lượt cổ tay0.3.24 — KHÔNG ĐẠT:** thu45giây đủ2.252 mẫu và45gói WS, chỉ7gói có HR41,3–43,8. Trung phản hồi số không đúng/không thuyết phục. Contact/settled/motion allowed đủ45snapshot; I2C/FIFO không lỗi, không có ngắt mạng mới. Replay chính raw này bằng0.3.23 và0.3.24 cho cùng7/34 cửa sổ được nhận và đầu ra giống nhau. Thay đổi smoother không giải quyết lỗi chọn chu kỳ, không công nhận0.3.24 là bản HR cổ tay đã tối ưu. Không mở thêm lượt đo hoặc nạp bản kế tiếp trong kết luận này. Báo cáo `hr-wrist-optimization-20261108/0.3.24-wrist-verdict.json` ở storage local; bản0.3.24 vẫn đang nạp, chưa rollback, chưa commit/push/merge. Khoảng đếm tay105–115 của lượt trước không gán làm nhãn cho lượt mới.

**Cập nhật 2026-11-08 buổi tối — 0.3.24-tracker:** đã nạp bản giảm độ trễ khi HR thay đổi có xu hướng rõ. Chỉ tăng hệ số EMA từ0,30 lên0,50 khi5 ứng viên mới liên tiếp cùng tăng/giảm đều; mất kết quả liên tục hoặc đổi chu kỳ thì xóa bằng chứng xu hướng. Không ngoại suy HR, không đổi phổ/tương quan/chọn chu kỳ/cổng chất lượng hoặc ngưỡng40–200bpm. Đây không phải bản sửa hết nhận nhầm dao động chậm. Chưa nghiệm thu độ chính xác toàn dải trên người.

20 ca mới chạy qua bộ lọc/tracker thực: nhịp đứng yên40,50,…,200bpm và3 lượt tăng40→190 rồi giảm về40 với tín hiệu sạch/yếu/hài mạnh. Giữ589/590 cửa sổ mỗi lượt; MAE so nhịp tức thời khoảng3,13–3,30bpm thay vì3,50–3,64 của bản trước. Mục tiêu kỹ thuật là trễ trung bình tối đa7giây khi nhịp thay đổi0,5bpm/giây; không suy thành sai số cổ tay. Cả45 ca core cũ đạt.

Replay cùng input trên20 bản ghi BIDMC đã xem: số cửa sổ được nhận giữ9.142/9.320 và lỗi trên10bpm giữ76, MAE tăng nhẹ0,858→0,874bpm, P95 tăng2,176→2,238bpm. Mô phỏng có nhịp giữ4.387/4.704 cửa sổ và8 lỗi lớn; MAE0,635→0,637. Mask nhận/từ chối và raw candidate giống nhau ở mọi input đã so. Chấp nhận đánh đổi nhỏ này cho mục tiêu bám nhịp đổi nhanh; không gọi đây là cải thiện mọi chỉ số. Các bản tăng tốc mạnh hơn/tăng trọng số cửa sổ/lọc trôi nền đã loại khi tăng lỗi hoặc không xử lý được lượt nhiễu.

Lượt0.3.23 tại quán45giây nhận24/45 gói HR40–123,5bpm, dữ liệu có dao động chậm cạnh tranh với vùng69 và121chu kỳ/phút. Lượt đếm mạch cùng lúc sau đó:32/60 gói HR114,4–117; Trung báo gần105–115, không có tổng nhịp chính xác. Giữ đây là khoảng đối chiếu gần đúng riêng lượt đó, không gán cho từng cửa sổ hoặc dùng chỉnh số đích. Firmware của hai lượt đều là0.3.23, không phải vừa chỉnh theo nhịp người dùng.

Nguồn/kiểm thử/binary và báo cáo so trước–sau ở `backend/storage/local/hr-wrist-optimization-20261108/`. `scripts/check_ppg_tracker.py --unit-only` nay chạy cả45 ca core và20 ca toàn dải trong CI hiện có. Driver GSR/IMU, bộ lọc đầu vào, motion guard, schema, lớp dự báo FE và credential không đổi. Build/nạp,8 ca tích hợp,89 ca driver/12snapshot,6 ca capture và4 tổ hợp header đạt; sau nạp nhận5 frame DEVICE đúng0.3.24. Lượt kiểm cổ tay mới chỉ bắt đầu khi Trung xác nhận, không tự coi dữ liệu nối lại là kiểm độ đúng.

## Lịch sử 0.3.23

**Kết quả mới nhất:** đã nạp 0.3.23 và kiểm cổ tay 45 giây: đủ 45 frame, 41 frame cuối liên tiếp có HR 68,8–76,6 bpm sau 4 frame đầu chưa có HR. Không lỗi kết nối mới; utility FE nhận đủ frame, không dùng dự báo và không trống sau HR đầu tiên. Chưa có nhịp tham chiếu đồng thời để xác nhận độ đúng. Giữ bản này, không mở thêm lượt đo trong vòng đã hoàn tất.

Ngày 2026-11-08. Đây là sửa trạng thái bộ làm mượt, không phải hiệu chuẩn HR về 75 bpm.

## Bản đã chốt và cách build

Theo xác nhận của Trung, dừng tối ưu HR tại `0.3.23-tracker`. Lõi tracker, bộ lọc, ngưỡng tiếp xúc, bảo vệ chuyển động và lớp hiển thị giữ nguyên. Không nạp lại hoặc mở lượt đo mới trong bước dọn mã.

Env mặc định `esp32s3_supermini` và alias `esp32s3_hr_tracker` đều dùng cấu hình đã đo: LED `0x32` (~10mA danh định), chip200Hz/gộp4, FIFO50Hz. Đã bỏ năm env thử LED/baseline/dense/demo; bản so sánh chỉ chạy bằng native test/benchmark offline. `network_check` và `serial_check` vẫn phục vụ CI. Xem [báo cáo dọn mã](05-CLEANUP-AUDIT.md).

Khi cần nạp sau đổi Wi-Fi:

```powershell
.\.venv\Scripts\python.exe -m platformio run -d ai/edge_firmware -t upload --upload-port COM7
```

Chạy hằng ngày vẫn dùng `npm run dev`, không cần nạp lại khi cấu hình không đổi.

## Bằng chứng mới

Lượt cổ tay 0.3.22 `ppg-20261108-010154-eeca37.csv/.json` có 2.250 mẫu, interval tối đa 20 ms, không mất trace. WS `ppg-link-wrist-20261108-010154-9a44d7.json` nhận đủ 45 frame, khoảng cách lớn nhất 1,063 giây. RSSI -65 đến -62 dBm; không có lỗi mạng mới. HR thiết bị vẫn chỉ có 12 frame, 40,8–46,9 bpm. Chưa có HR tham chiếu đồng thời, không gán số 75 đã đếm riêng cho lượt này.

Phân tích đúng bộ lọc C++ và tracker đang chạy cho thấy một lỗi độc lập với nhịp thật: ở cuối replay, `rawBpm` đã được chấp nhận khoảng 74,5, nhưng `bpm` sau làm mượt vẫn khoảng 40,7. Tracker đã xác nhận đổi chu kỳ; median3/EMA vẫn chứa giá trị của chu kỳ cũ. Cùng lỗi có thể xảy ra ở chiều 80 về 40. Điều này không chứng minh chu kỳ mới chính là mạch thật, nhưng bộ làm mượt đang không thể hiện đúng trạng thái đã xác nhận.

## Sửa tối thiểu

Chỉ khi một chuyển chu kỳ lớn vượt qua đủ số lần xác nhận hiện hành mới xóa lịch sử median/EMA cũ và bắt đầu làm mượt chu kỳ mới. Giữ 6 lần cho nhảy gần nửa/gấp đôi, 3 lần cho nhảy lớn khác; không đổi điều kiện chất lượng, miền HR, prior hoặc lớp dự báo FE. Biến động nhỏ vẫn làm mượt bình thường. Không đặt hằng 75 hoặc tự nhân đôi mọi số 40.

Hai kiểm thử mới cho 40→80 và 80→40 thất bại với core cũ vì kết quả đã nhận chu kỳ mới vẫn bị trộn với nhịp cũ. Bản sửa qua cả hai. Ca kiểm làm mượt nhỏ đổi kích thích 80→120 thành 80→88: theo hành vi mới, 80→120 là chuyển quỹ đạo cần làm mượt lại, còn 80→88 kiểm median/EMA trong cùng quỹ đạo. Không đổi yêu cầu kiểm timestamp hoặc việc phải thực sự có kết quả sau chuyển.

45 ca core đạt. Trước khi chọn nạp, replay cùng raw, mô phỏng và BIDMC đã dùng; kiểm số cửa sổ được nhận và `rawBpm` không thay đổi, vì sửa này chỉ tác động lịch sử đầu ra. Báo cáo dùng tên mới và khóa source/input hashes. Chưa thay phiên bản firmware tại checkpoint này; ESP vẫn 0.3.22.

## Hướng đã loại ở cùng vòng

Đã thử offline đạo hàm bậc một trước chấm chu kỳ để làm nổi sườn xung yếu. Test hài mạnh thất bại do nhận sai nửa/gấp đôi nhịp. Không giữ trong mã chạy, không nạp. Nguồn/kết quả riêng ở `backend/storage/local/hr-slope-prototype-20261108/`.

Biểu đồ chẩn đoán `ppg-wrist-link-20261108.png` và số liệu `ppg-wrist-link-analysis-20261108.json` lưu trong storage local đã bỏ qua bởi Git. Chưa gọi HR ổn định hoặc chính xác; sửa bộ làm mượt không tự giải quyết lỗi chọn chu kỳ ban đầu.

## Replay trước khi chọn nạp 0.3.23

Đã so core cũ/mới trên đúng từng input và assert toàn bộ mask nhận/từ chối cùng `rawBpm` không đổi. Chỉ giá trị qua smoother đổi. Ở raw cổ tay mới nhất, cả hai nhận 14/34 cửa sổ replay; cửa sổ cuối có ứng viên 74,52 thì đầu ra cũ 40,74, đầu ra mới 74,52. Không dùng con số này làm HR tham chiếu hoặc nói các đoạn thấp trước đó đã được xử lý.

Trên bộ phát triển đã xem, mô phỏng có nhịp cùng 2.210/2.352 cửa sổ được nhận: MAE từ 0,67 xuống 0,63 bpm, lỗi trên 10 bpm từ 10 xuống 6. BIDMC 01–05 cùng 2.274/2.330 cửa sổ: MAE 0,85 xuống 0,71, lỗi lớn 22 xuống 12. Nhiễu không mạch vẫn bị nhận 258/784 cửa sổ: sửa smoother không giải quyết điểm yếu này.

Hồi quy trên seed đã dùng và BIDMC 16–20, không phải kiểm độc lập: mô phỏng có nhịp cùng 4.420/4.704 cửa sổ, MAE 1,00 xuống 0,82, lỗi lớn 53 xuống 25; BIDMC cùng 2.239/2.330, MAE 1,55 xuống 1,50, lỗi lớn 56 xuống 51. Nhiễu vẫn 276/931. Không suy những sai số này thành sai số tại cổ tay Trung.

Báo cáo development/regression và so input trùng nhau dùng tiền tố `ppg-track-switch-…-20261108.json`. Source hash khóa trước chấm; dữ liệu/seed hồi quy đã xem được chú thích rõ. Chọn build profile tracker phiên bản 0.3.23 cho sửa lỗi trạng thái này; chưa có kết quả nạp hoặc lượt đo thật ở checkpoint này.

## Đã nạp, chờ lượt cổ tay sau sửa

Đã build/nạp 0.3.23 trên COM7, upload xác nhận hash. Self-test worker đạt; kiểm sau nạp nhận 5 frame DEVICE đúng firmware qua WebSocket. RSSI khoảng -63 dBm, chưa có lỗi mới ở khoảng kiểm. 45 ca core, 8 ca tích hợp driver, 6 ca bộ thu raw và 4 tổ hợp header đạt. Nguồn/binary khóa ở `hr-track-switch-sources-20261108/`; bản trước giữ ở `hr-link-diagnostics-sources-20261108/` để đối chiếu.

Chưa có lượt cổ tay sau sửa ở checkpoint này. Bước tiếp chỉ một lượt 45 giây khi Trung xác nhận sẵn sàng, không cần đếm mạch. Kết quả kiểm phần mềm chưa chứng minh HR cổ tay đã đúng hoặc luôn có số. Giữ cả log mạng để nhận ra gián đoạn truyền nếu xuất hiện lại.

## Lượt cổ tay sau sửa đã hoàn tất

Sau xác nhận của Trung, thu đủ 45 giây rồi báo nghỉ tay ngay. Raw `ppg-20261108-012754-1e8448.csv/.json`: 2.252 mẫu, complete, interval tối đa 20 ms, không mất trace, timestamp lùi hoặc lỗi capture. WS `ppg-track-switch-wrist-20261108-012754-56f6c9.json`: 45 frame cùng một phiên, đúng 0.3.23; HR null ở index 0–3, sau đó 41 frame liên tiếp có số 68,8–76,6 bpm. Không xuất hiện số 40 trong lượt này. Không gọi 41 frame là 41 phép đo độc lập: worker hoàn thành 40 yêu cầu và nhận 39 kết quả; gói live có thể dùng kết quả còn mới.

Đường truyền: khoảng nhận lớn nhất 1,110 giây, Wi-Fi/MQTT/đồng bộ đều giữ trạng thái kết nối trong 45 snapshot; publish fail không tăng, RSSI -67 đến -65 dBm. Worker self-test đạt, không ghi đè queue; xử lý lớn nhất 76.374 µs, stack còn 2.884 byte. Không dùng các số này để xác nhận vấn đề nhiệt đã được khắc phục.

Replay bằng đúng `isTelemetry`, `heartRateDisplay` và `heartRatePlot` hiện tại: cả 45 frame được parser FE nhận; 41 frame có số, **0 frame dự báo**, không trống sau HR đầu tiên, không sửa frame gốc. Báo cáo `ppg-track-switch-wrist-20261108-012754-56f6c9-frontend.json`. Đây là kiểm chức năng bằng utility thực, chưa phải ảnh browser hoặc xác nhận trực tiếp màn hình.

Đối chiếu lại **cùng raw mới này** bằng core 0.3.22 và 0.3.23: cả hai nhận 33/34 cửa sổ replay và đầu ra giống nhau. Vì lượt này không có chuyển chu kỳ lớn cần reset smoother, không quy toàn bộ việc coverage tăng so với lượt trước cho bản sửa. Bằng chứng riêng cho lỗi đã sửa là hai test tái hiện trước/sau và các raw có chuyển chu kỳ trong phép replay khóa input. Điều kiện tín hiệu từng lượt khác nhau vẫn ảnh hưởng lớn.

GSR có giá trị ở 19/45 frame, IMU đủ 45/45; ghi đúng kết quả quan sát, không retune hai cảm biến ở vòng HR này. Không gán số 75 đếm riêng làm nhãn cho lượt. Chưa đánh giá sai số cổ tay, độ tin cậy cả ngày hoặc bảo đảm hết mọi trường hợp nhận nhầm chu kỳ.

Biểu đồ `ppg-track-switch-final-trial-20261108.png` đã kiểm bố cục. Bàn giao `ppg-track-switch-final-handoff-20261108.json` lưu hash raw/WS/nguồn/binary, kết quả utility và giới hạn. Toàn bộ dữ liệu cá nhân ở storage local được Git bỏ qua. Giữ 0.3.23 và luồng chạy hằng ngày `npm run dev`; không cần đổi Wi-Fi hoặc nạp thêm ở vòng này. Chưa commit/push/merge.
