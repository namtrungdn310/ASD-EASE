# HR cổ tay: tìm nguyên nhân và cải thiện thuật toán

**Vòng mới nhất:** thử giảm nhận nhầm chu kỳ và lọc nền; replay một lượt cũ tốt hơn nhưng đo 0.3.21 chỉ nhận 5/45 frame HR quanh 43 bpm. Không giữ bản thử, khôi phục core 0.3.20. Mục tiêu chưa đạt; xem [kết quả và các cách đã loại](05-HR-HARMONIC-REJECTION.md). Không dùng việc có đường dự báo FE làm bằng chứng số đo đúng.

Cập nhật 2026-11-07. Đây là kế hoạch hiện hành cho HR, thay cho việc tiếp tục thử LED và tăng mức lấy mẫu. Các báo cáo cũ giữ làm bằng chứng lịch sử. Chưa có kết luận đã tìm được nguyên nhân chính hoặc HR cổ tay đã đạt.

**Checkpoint mới nhất0.3.20-tracker:** theo yêu cầu liền mạch của Trung đã thêm xác nhận cú nhảy, sửa xác nhận chu kỳ khởi tạo và lớp dự báo FE tối đa15giây có nhãn. Lượt cuối45gói:28có HR thiết bị,8tạm tính; không trống sau HR đầu tiên trong lượt. HR còn đoạn thấp và thiếu tham chiếu nên chưa xác nhận độ đúng. [Bàn giao vòng mới](05-HR-CONTINUITY.md). Không tự mở thêm vòng đo.

**Checkpoint hiện hành sau khi Trung yêu cầu hướng tracking:** đã triển khai/nạp0.3.18-tracker và kiểm hai lượt cổ tay. Lượt cuối45gói/45giây,17gói có HR,13gói cuối liên tiếp70,3–72,2bpm. Đã có đoạn cập nhật đều hơn, còn khoảng thiếu và độ đúng chưa đối chiếu. Vòng code/test/build/nạp/đo hướng mới đã hoàn tất; chưa mở thêm vòng tự động. [Bàn giao tracker](05-HR-CYCLE-TRACKER.md). Các checkpoint “chưa chọn bản để nạp” dưới đây thuộc vòng thuật toán cũ.

**Ưu tiên mới do Trung chốt:** demo HR tương đối, ít nhảy trên FE. Đã triển khai/nạp `0.3.16-demo`, làm mượt ứng viên mới, giữ số trên thẻ tối đa 10 giây có tuổi nhận; không điền telemetry/biểu đồ. Đã thử hai lượt cổ tay và một lượt kết nối trên bàn. Lượt cổ tay cuối nhận đủ **45 gói/45 giây**, GSR/IMU đủ nhưng **HR 0/45**; lượt trước driver có HR nhưng mạng ngắt trước lúc HR xuất hiện. **Đường truyền đã kiểm liên tục ở lượt cuối, HR hiển thị đều chưa đạt.** [Kết quả demo và giới hạn](05-HR-DEMO.md). Không đổi kết luận kiểm sai số cũ thành đạt.

**Checkpoint mới nhất:** đã đủ **bốn lượt hoàn chỉnh: 9.008 mẫu raw, 160 frame WS**, cộng B2 gián đoạn giữ riêng. Đã chấm hai ứng viên offline: A thiếu coverage nhịp sạch; B qua development nhưng vòng seed mới nhận nhầm 165 thành 81,656 bpm. **Chưa chọn bản để nạp; HR cổ tay chưa đạt.** Không tự mở thuật toán thứ ba hoặc đo thêm. [Kết quả và quyết định](05-HR-WEAK-SIGNAL-EXPERIMENT.md), [danh mục dữ liệu](05-HR-DATA-HANDOFF.md). Chưa xác nhận khắc phục nguyên nhân nhiệt.

## 1. Điều kiện và mục tiêu đã chốt

- Giữ nguyên cụm ba mạch trên đế tròn. Khi đo, lật mặt linh kiện xuống; ô kính MAX30102 trên mạch xanh hướng vào da, toàn bộ mạch xanh nằm trong phạm vi cổ tay. ESP32 và MPU nhô ra ngoài một phần không tự chứng minh đầu quang bị kê hở.
- **Chỉ đặt nhẹ trên cổ tay, không dùng tay đè xuống, không yêu cầu siết dây chặt hơn.** Không tháo mạch, đổi dây hoặc yêu cầu thay cảm biến trong kế hoạch này.
- **“Không quá khắt khe” còn áp dụng cho thuật toán:** không buộc sóng cổ tay yếu phải có hình dạng và độ đều giống sóng đẹp ở đầu ngón tay. Bộ `hybrid_strict` hiện tại là đối chứng, không phải đáp án phải giữ bằng mọi giá.
- Chỉ tối ưu HR. Giữ nguyên driver, hiệu chuẩn, tần số và cách hiển thị GSR/IMU. Có thể đọc IMU hiện có để đối chiếu nhiễu chuyển động; không sửa phép đo của nó.
- Ưu tiên **đúng gần tham chiếu trước, tăng tỷ lệ có kết quả sau**. Có khoảng trống tạm thời vẫn chấp nhận được nếu tránh được các số sai lớn.
- Dữ liệu thật lên Dashboard vẫn đi ESP → Wi-Fi → MQTT → backend → WebSocket → frontend. USB chỉ nạp/log; mô phỏng không được thay dữ liệu DEVICE.

## 2. Những gì đã biết từ các lần đo

| Lượt | Kết quả đã ghi nhận | Ý nghĩa và giới hạn |
|---|---|---|
| Đầu ngón tay, 0.3.12 | 38/39 frame WS có HR, khoảng 77,2–88,3 bpm | Thuật toán và đường truyền có thể tạo kết quả trong điều kiện này; chưa có tham chiếu để gọi là chính xác |
| Cổ tay, LED 10 mA lần đầu | 15/39 frame WS có HR, khoảng 79–85,1 bpm | Có lúc lấy được ứng viên; không chứng minh số này đúng |
| Cổ tay, lặp LED 10 mA | 0/39 frame có HR | Không lặp lại được dù cùng cấu hình |
| Cổ tay, LED 12,4 mA | 0/39 frame có HR | Nền quang cao hơn chưa tạo ra nhịp được chấp nhận |
| Cổ tay, 400 Hz/gộp 8, FIFO 50 Hz | 0/39 frame có HR | Chưa có bằng chứng tăng số mẫu chip giúp trường hợp này |

Các lượt cổ tay gần nhất không tăng lỗi I2C, FIFO overflow, gap, clipping hoặc ALC. Trong ba lượt 10 mA đầu/lặp và 400 Hz, cả 45 bản chụp trạng thái đều qua cổng tiếp xúc và chuyển động. Đây là quan sát bằng phần mềm, không phải phép đo lực tiếp xúc.

Ở lượt 10 mA lặp, tương quan chu kỳ IR toàn cửa sổ chỉ khoảng 0,045–0,395, trong khi baseline yêu cầu ít nhất 0,60; RED cũng không vượt đồng thời hai cửa sổ cần thiết. Do đó có ít nhất một cổng đang loại HR trước khi công nhận kết quả. **Chưa biết đó là loại nhiễu đúng hay bỏ sót nhịp thật.** Số log đã làm tròn, không thay giá trị chính xác khi replay.

Điều kiện ánh sáng của dữ liệu cũ chưa được chuẩn hóa thành cặp A/B. Không dùng chúng để kết luận ánh sáng là nguyên nhân chính. Báo cáo lấy mẫu và các file bằng chứng: [đợt thử cổ tay](05-WRIST-SAMPLING-TRIAL.md), [các mức LED](05-WRIST-PROFILE.md).

### Phân tích lại trong bước dọn mã

Đã replay bốn trace bằng đúng bộ lọc C++ hiện tại và công cụ quality có sẵn, mỗi trace 32 cửa sổ đủ điều kiện. Đây là dữ liệu phát triển đã xem, chưa có HR tham chiếu.

| Trace | Baseline | Hybrid strict | Hybrid balanced cũ |
|---|---:|---:|---:|
| Ngón tay 0.3.12 | 32/32 | 32/32 | 32/32 |
| Cổ tay 10 mA đầu | 16/32 | 18/32 | 24/32 |
| Cổ tay 10 mA lặp | 0/32 | 0/32 | 0/32 |
| Cổ tay 400 Hz/gộp 8 | 0/32 | 0/32 | 0/32 |

Lượt 10 mA lặp: nhánh quality IR bị loại sớm vì 8s/4s bất đồng ở 12/32 cửa sổ; 13 cửa sổ tính được đầy đủ đặc trưng thì cả 13 không qua độ đều RR, trung vị template và tỷ lệ phổ của strict. Các lý do sau không loại trừ nhau, không cộng thành tổng. Lượt 400 Hz: bất đồng 8s/4s chiếm 15/32 ở IR và 18/32 ở RED.

Trong cùng đoạn cố định giây 32–40, raw cổ tay có trôi nền và xung ngắn nổi bật hơn đoạn ngón tay. Bộ lọc hiện tại còn để lại dao động bất thường; **chưa quy được chúng cho ánh sáng, tiếp xúc hay một nguyên nhân khác**, và chưa biết phần nào là mạch thật. Hai kênh có thể cùng chịu một nhiễu nên cùng đỉnh phổ không tự xác nhận HR.

**Hai hướng ưu tiên của vòng thuật toán:** (1) xử lý trôi nền/xung mà vẫn bảo toàn sóng mạch yếu; (2) chọn chu kỳ và kết hợp bằng chứng mềm, tránh để cửa sổ 4 giây hoặc template quá chặt loại toàn bộ ứng viên. Không chỉ chuyển sang `balanced` cũ: cấu hình đó từng nhận nhầm nhiễu trong benchmark lịch sử, và vẫn không cứu được hai trace khó này.

Bằng chứng cục bộ: [hình sóng cùng đoạn thời gian](../../backend/storage/local/hr-saved-traces-20261107.png), [bảng replay và lý do loại](../../backend/storage/local/hr-saved-traces-20261107.json). File này nằm trong thư mục ignored trên máy Trung, không phải tài nguyên đã đưa lên GitHub. Script tái hiện lưu cùng bản sao dọn mã tại `backend/storage/local/hr-cleanup-20261107/analyze_saved_traces.py`.

Một lưu ý khi đọc log: `powerRatio=0` ở bản hiện tại có thể do chưa chọn được chu kỳ và chưa gán trường kết quả, không đủ để kết luận công suất tín hiệu thực bằng 0.

## 3. Các giả thuyết cần tách riêng

| Giả thuyết | Cách kiểm | Khi nào được kết luận |
|---|---|---|
| Mất mẫu hoặc lỗi vận chuyển làm mất HR | Đối chiếu raw, bộ đếm driver, HR trước serializer và frame WS cùng thời gian | HR tồn tại tại ESP nhưng mất phía sau mới xem là lỗi truyền/hiển thị; không sửa lọc để chữa mạng |
| Ánh sáng ngoài ảnh hưởng sóng | So A không che với B che sáng, giữ nguyên vị trí/lực chạm/firmware | Chỉ nói có ảnh hưởng khi khác biệt lặp lại; đổi vị trí hoặc lực chạm làm cặp thử mất giá trị |
| Tín hiệu mạch yếu so với nền/nhiễu | Xem raw IR/RED, dao động sau bỏ nền, phổ và mức lặp theo thời gian | Phân biệt nền DC lớn với phần dao động; không gọi biên độ AC/DC hiện tại là PI/SNR đã hiệu chuẩn |
| Bộ lọc làm yếu hoặc méo nhịp | Replay cùng raw qua bộ lọc đang chạy và ứng viên có thể chạy nhân quả | Cải thiện phải tồn tại trên đoạn chưa dùng để chỉnh, không chỉ một biểu đồ đẹp |
| Cổng kiểm tra quá chặt | Thống kê từng lý do loại, so các ngưỡng trên cùng dữ liệu và bộ có tham chiếu | Nới điều kiện có kiểm chứng giúp nhận thêm nhịp đúng mà không tăng rõ lỗi lớn |
| Nhận nhầm một nửa/gấp đôi nhịp | So đỉnh phổ, các đỉnh tự tương quan và các hài; kiểm dữ liệu có HR gốc | Không lấy HR trước đó làm đáp án rồi ép mọi ứng viên bám theo |

MAX30102 có khử ánh sáng nền. `ALC_OVF` chỉ báo khi cơ chế đó chạm giới hạn; không có cờ này không chứng minh hết nhiễu quang. Cơ sở: [datasheet MAX30102, trang 9 và 12](https://www.analog.com/media/en/technical-documentation/data-sheets/MAX30102.pdf). Tài liệu [tích hợp quang học của hãng](https://www.analog.com/en/resources/technical-articles/guidelines-for-the-optomechanical-integration-of-heartrate-monitors-in-wearable-wrist-devices.html) giải thích phần AC mang thông tin mạch và phản xạ ngoài đường đi qua mô có thể làm giảm chất lượng. Các tài liệu này không xác định nguyên nhân riêng của cụm mạch đang thử.

## 4. Thứ tự thực hiện và điểm dừng

### Mốc 0 — Dọn phần thừa, khóa bản đối chứng

- [x] Kiểm working tree và bảo toàn thay đổi đang có; không reset, không dọn bằng `git clean`.
- [x] Dọn file/biến/dependency không có bên sử dụng đã xác định; lưu bản sao cục bộ.
- [x] Hoàn tất kiểm thử sau dọn: 7 build, 4 tổ hợp header, 60 test frontend, driver/protocol và parity; chi tiết tại [báo cáo dọn mã](05-CLEANUP-AUDIT.md).
- [x] Không đổi phép lọc HR đang dùng hoặc tự nạp firmware trong bước dọn.

Bản được nạp gần nhất theo hồ sơ: **0.3.13-led10**, chip 200 Hz/gộp 4, FIFO 50 Hz, LED danh định 10 mA. Đọc lại phiên bản thực trước lần đo mới; không coi lịch sử là trạng thái live. Các profile khác chỉ là đối chứng/thử nghiệm, chưa chọn tối ưu.

### Mốc 1 — Phân tích dữ liệu đã có trước khi bắt người dùng đo thêm

- [x] Đối chiếu bốn trace đại diện với hồ sơ vị trí/phiên bản, lỗi lấy mẫu/WS; lưu hash đầu vào, điều kiện ánh sáng chưa biết ghi rõ.
- [x] Replay bằng bộ lọc C++ sản xuất, tính cùng cửa sổ 8 giây và 4 giây; lưu lý do loại của quality IR và RED riêng. Đã đối chiếu log baseline, chưa có log nguyên nhân chi tiết cho mọi lần tính baseline.
- [x] Phân biệt tầng lấy mẫu, tiếp xúc/chuyển động, ứng viên chu kỳ và quality; không diễn giải mọi trường 0 của log là một phép đo thật bằng 0.
- [x] Vẽ raw bỏ nền, sóng sau lọc và phổ trên cùng khoảng cố định. Không chọn đoạn theo HR trông hợp lý. Biểu đồ Dashboard 1 Hz không thay raw 50 Hz để thiết kế bộ lọc.
- [x] Chọn hai hướng xử lý có bằng chứng: trôi nền/xung và chọn chu kỳ với cổng mềm. Chưa kết luận nguyên nhân vật lý của nhiễu.

Replay bắt đầu bộ lọc tại đầu trace, không có toàn bộ lịch sử trước đó hoặc mọi trạng thái task/IMU. Số cửa sổ replay khác số frame WS; ghi hai loại riêng. Không dùng tương quan IR/RED như hai phép đo độc lập hoàn toàn.

**Điểm dừng:** có bảng loại theo từng tầng và xác định được việc cần sửa/kiểm tiếp. Nếu raw đã đủ trả lời một giả thuyết thì không yêu cầu đo lại chỉ để lặp bằng chứng.

### Mốc 2 — Chỉ đo bổ sung để trả lời câu hỏi còn thiếu

Không đổi LED, sample rate, firmware, vị trí hoặc lực chạm trong phép so ánh sáng. Chỉ thử khi đã đọc được phiên bản và kiểm luồng sẵn sàng; chưa yêu cầu giữ tay lúc đang build hay sửa code.

1. **A1, 45 giây:** cổ tay như cách đeo đã chốt, ánh sáng phòng bình thường, không che thêm.
2. **B1, 45 giây:** giữ cụm ở nguyên vị trí, dùng vật tối màu che ánh sáng từ phía ngoài; không chèn giữa ô kính và da, không đè vật che lên cụm.
3. Chỉ khi A1/B1 cho thấy khác biệt cần xác nhận: thử **B2 rồi A2**, mỗi lượt 45 giây. Tối đa bốn lượt cho câu hỏi ánh sáng trong vòng này.
4. Ghi thời điểm đổi điều kiện. Phân tích cùng khoảng ổn định, bỏ quá độ theo cùng quy tắc; không chọn khoảng loại riêng để có kết quả tốt.

AI hướng dẫn **một lượt tại một thời điểm**, chờ xác nhận sẵn sàng, thu xong báo thả tay ngay. Nếu việc che làm thay đổi vị trí/lực chạm, đánh dấu bị nhiễu yếu tố; không gán cải thiện cho ánh sáng. Cặp A/B chỉ đánh giá ảnh hưởng của ánh sáng ngoài, không tự tách được phản xạ LED nội bộ hay mọi nhiễu điện.

Không mặc định phải quay lại thử đầu ngón tay: đã có dữ liệu đối chứng. Chỉ thêm một lượt nếu cần kiểm cảm biến hoặc firmware đã thay đổi đáng kể.

### Mốc 3 — Thiết kế ứng viên cho tín hiệu yếu, không lấy “strict” làm mặc định bắt buộc

Chỉ triển khai sau bảng nguyên nhân/tầng loại ở mốc 1. Nếu cần thông tin ánh sáng thì dùng mốc 2 trước; không nhất thiết chờ xác định được mọi nguyên nhân vật lý mới phân tích thuật toán offline.

Luồng ứng viên cần so:

`raw → xử lý nền/trôi chậm → lọc dải nhịp → ứng viên chu kỳ/đỉnh → chấm bằng chứng → chọn HR → làm mượt phần đã có bằng chứng`

- **Ứng viên A:** sửa đúng nút thắt lớn nhất của pipeline hiện có. Ví dụ thay điều kiện loại cứng ở cửa sổ ngắn bằng đánh giá độ tin cậy kết hợp, hoặc giảm yêu cầu hình dạng khi sóng yếu nhưng chu kỳ còn rõ. Thay đổi phải ghi riêng để biết tác dụng.
- **Ứng viên B:** chỉ làm nếu A không đạt. Kết hợp thông tin tự tương quan và phổ/hài để chọn chu kỳ cho sóng yếu; không lệ thuộc hoàn toàn vào tìm đủ từng đỉnh. Không tự ưu tiên vùng 70–90 bpm hoặc khóa quanh HR cũ.
- Xem lại ngưỡng tương quan 0,60, đối chiếu 8s/4s, CV RR, template 0,90/0,75 và tỷ lệ phổ 0,65. Đây là lựa chọn kỹ thuật đã dùng, **không phải các ngưỡng đúng cho mọi cổ tay**. Không giữ chúng chỉ vì test cũ được viết theo chúng.
- Bộ lọc phải giữ được thành phần nhịp và có độ trễ đo được. Dùng bộ lọc nhân quả khi đánh giá khả năng chạy thật; lọc dùng mẫu tương lai chỉ được dùng làm minh họa offline, không lấy kết quả đó thay firmware.
- Không tự thêm notch 50/60 Hz vào FIFO 50 Hz: cần xem phổ và khả năng alias trước. Không tăng số tầng lọc/độ dài cửa sổ chỉ để đường vẽ phẳng.
- So IR và RED bằng chất lượng có thể quan sát; không chọn kênh theo đáp án tham chiếu hoặc vì số của nó trông quen.
- Các kiểm tra dữ liệu hỏng, timestamp lùi, NaN, clipping và mất mẫu vẫn cần giữ. Phân biệt chúng với điều kiện hình dạng/độ đều có thể quá chặt.

Giới hạn vòng đầu: **tối đa hai ứng viên thuật toán**, mỗi ứng viên tối đa ba cấu hình có lý do, khóa trước vòng kiểm mới. Không quét hàng trăm ngưỡng rồi chọn đẹp nhất trên cổ tay đã xem nhiều lần.

Nghiên cứu [đối chiếu các bộ phát hiện nhịp PPG](https://pubmed.ncbi.nlm.nih.gov/35853440/) là căn cứ tham khảo cách benchmark, không bảo đảm thuật toán được xếp tốt sẽ tốt nhất trên cụm này. MSPTD đã được thử trong repo; không bắt đầu lại toàn bộ nghiên cứu chỉ vì đổi tên thuật toán.

### Mốc 4 — Mô phỏng và chọn bằng sai số, không bằng độ kín biểu đồ

- Dùng lại công cụ hiện có: `benchmark_ppg_candidates.py`, `ppg_quality_candidate.py`, `benchmark_ppg_quality.py`, `simulate_wrist_ppg.py` và harness C++. Chỉ mở rộng đúng phần cần; tránh tạo nhiều công cụ tương đương không dùng.
- Tất cả file người dùng đã xem/chỉnh trước đây là **dữ liệu phát triển**, không gọi là test mới. Tách theo cả lần đo, không chia các cửa sổ chồng nhau của cùng trace sang train/test.
- Từ các đặc điểm đo được, mô phỏng độc lập: nền cao nhưng sóng yếu; trôi nền; đổi biên độ; nhiễu trắng/có màu; ánh sáng biến thiên; hài gây nửa/gấp đôi HR; rời da; mất mẫu. Quét các mức yếu quanh phạm vi quan sát thay vì chỉ một sóng sin đẹp.
- Sóng có nhịp gốc và nhiễu không có nhịp phải có nhãn riêng. Không gán số HR từ Dashboard làm đáp án của trace thật. Đặc điểm lấy từ cổ tay không biến mô phỏng thành mô hình quang học đã hiệu chuẩn.
- Dùng seed/trace mới sau khi khóa ứng viên; báo số cửa sổ đúng, sai, bị bỏ, MAE, p95, lỗi lớn, độ trễ và tỷ lệ có kết quả. Báo riêng các cửa sổ mới được cứu.
- Độ chính xác và độ sẵn có là hai trục. Không chọn ứng viên loại hết cho MAE đẹp; cũng không chọn ứng viên luôn hiện số nhưng sai nhiều.
- Với nhiễu quang tuần hoàn giống mạch và IMU yên, ghi rõ ca nhầm đã biết; không giấu hoặc khẳng định chỉ phần mềm luôn phân biệt được.

**Mốc kiểm kỹ thuật dự kiến cho lúc nghỉ:** khi có tham chiếu đồng bộ phù hợp, nhắm MAE không quá 5 bpm và ít nhất 95% cửa sổ được chấp nhận sai không quá 10 bpm; báo cả số cửa sổ thiếu và mọi lỗi nửa/gấp đôi nhịp. Đây là mục tiêu nội bộ ban đầu, không phải tiêu chuẩn y khoa. Trước hết ứng viên cần không làm sai số/lỗi lớn tệ hơn đối chứng, đồng thời cứu thêm được nhịp đúng. Chưa đặt điều kiện bắt buộc phải có số liên tục.

Hiện chưa có HR tham chiếu đồng bộ tại cổ tay. Vẫn có thể hoàn tất chẩn đoán code, benchmark tham chiếu công khai và mô phỏng, nhưng **chưa thể chấm sai số HR thật tại cổ tay**. Đếm mạch thủ công đủ thời gian chỉ là mốc kiểm thô; không dùng để chấm từng cửa sổ như ECG đồng bộ. Không yêu cầu mua thiết bị để tiếp tục những phần độc lập này.

### Mốc 5 — Port/nạp một bản có cơ sở và kiểm trên đúng kiểu đặt

- Chỉ đưa lên ESP ứng viên đã qua mốc 4. Đặt phiên bản rõ; giữ bản đối chứng có thể nạp lại.
- Task tính HR tách việc lấy mẫu; đo heap, stack, độ trễ và gap thật. Không giải quyết nhiễu bằng việc làm chậm hay mất mẫu.
- Đối chiếu quyết định C++/offline trên cùng raw; chạy các test có ý nghĩa, không sửa expected chỉ để bộ mới đạt.
- Kiểm GSR/IMU/MQTT/WS/phiên tự động không hồi quy, nhưng không tối ưu lại chúng.
- Thử một lượt cổ tay để phát triển, rồi một lượt mới sau khóa cấu hình để kiểm khả năng lặp lại. Hướng dẫn và chờ xác nhận từng lượt.

Nếu cần làm mượt: thử trung vị ngắn hoặc EMA thích ứng **trên ước tính mới đã có bằng chứng**, đo cả độ trễ và sai số trước/sau. Không kéo dài TTL, điền HR cũ, nối qua mất tiếp xúc, hay biến số dự báo thành số vừa đo. Nếu thêm cơ chế theo dõi chu kỳ, chỉ chấp nhận khi cửa sổ hiện tại còn bằng chứng, và kiểm nguy cơ bị khóa vào một nhịp sai.

**Điểm dừng của vòng này:** sau tối đa hai ứng viên và hai lượt cổ tay kiểm bản được chọn, bàn giao bảng so trước/sau và kết luận đạt phần nào/chưa đạt phần nào. Nếu chưa đạt thì chỉ mở vòng mới khi có một giả thuyết mới kèm bằng chứng; không tự tiếp tục tăng LED, đổi filter và yêu cầu giữ tay liên tục.

## 5. Các file trọng tâm

| File | Trách nhiệm trong vòng này |
|---|---|
| `include/processing/ppg_rate.h` | Lọc nhân quả, ứng viên chu kỳ và cổng baseline |
| `include/processing/ppg_quality.h` | Đặc trưng/độ tin cậy và lựa chọn HR ở C++ |
| `src/sensors/ppg_hybrid_worker.cpp` | Tính riêng khỏi vòng lấy mẫu, quản lý cửa sổ/kết quả |
| `src/sensors/MAX30102Sensor.cpp` | Thu raw, freshness, reset đúng nguyên nhân; tránh xóa lịch sử vì một cửa sổ chưa đạt nếu không cần |
| `scripts/ppg_quality_candidate.py` | Đối chiếu logic offline; tách cấu hình ứng viên mới khỏi policy lịch sử |
| `scripts/benchmark_ppg_*.py`, `scripts/simulate_wrist_ppg.py` | Đo sai số/khả năng có kết quả và ca nhiễu |
| `tests/native/ppg_*` | Kiểm thuật toán, dữ liệu lỗi, thời gian và parity thực thi |

Đường dẫn firmware tương đối với `ai/edge_firmware/`. Không đổi schema/API để làm một ước tính HR chưa đạt được nhận. Không sửa driver GSR/IMU hoặc giao diện trong vòng này trừ khi có lỗi tích hợp được chứng minh.

## 6. Bàn giao để tiếp tục qua hội thoại dài

Mỗi mốc ghi ngắn: giả thuyết, file/phiên bản, dữ liệu và hash, cấu hình đã khóa, kết quả tốt/xấu, việc chưa thử và bước tiếp. Raw/log cá nhân, hình sóng và thông tin local nằm trong `backend/storage/local/` đã được bỏ qua bởi Git; không xóa để làm repo trông sạch hơn. Không commit credential.

Trạng thái cuối cần tách: dọn mã/kiểm thử phần mềm; khôi phục thêm HR trên dữ liệu yếu; truyền thật đủ luồng; đo HR cổ tay đã so tham chiếu. Một mục đạt không thay các mục còn lại.

**Checkpoint trước lượt A1, 2026-11-07:** đã bật lại dịch vụ, thấy ESP ở COM7. Wi-Fi quán trực tiếp chưa kết nối được MQTT; chưa quy được lỗi cho cấu hình cụ thể của quán. Theo lựa chọn tiết kiệm data của Trung, dùng Mobile hotspot 2.4 GHz trên laptop để chia sẻ chính Wi-Fi quán cho ESP. Đã đồng bộ cấu hình local và nạp lại bản đối chứng `0.3.13-led10` (hash flash verified), không đổi thuật toán HR. Broker/backend healthy, ESP báo wifi/mqtt/sync đều 1, WebSocket nhận 11 frame DEVICE có GSR và hai vector IMU. Counter `invalid` trên ESP có 1 từ trước lúc đọc; không tuyên bố bằng 0 hoặc coi đó là lỗi đọc PPG. Lượt kiểm chưa áp cảm biến đo HR. [Cách chạy qua hotspot laptop](05-ONE-COMMAND-DEV.md).

### Lượt A1 đã thu — 2026-11-07, 14:37 (Asia/Saigon)

Trung xác nhận đặt nhẹ ở cổ tay, ánh sáng phòng bình thường, chưa che thêm; thu 45 giây và báo thả tay ngay khi xong. Giữ bản `0.3.13-led10`, chip 200 Hz/gộp 4/LED danh định 10 mA.

- Raw `ppg-20261107-143727-69bc62.csv/.json`: 2.252 mẫu, trace dropped 0, không timestamp lặp/lùi. Khoảng cách mẫu 19–40 ms, có một khoảng 40 ms; không diễn giải thành mọi mẫu đều cách chính xác 20 ms.
- I2C/overflow/gaps/clip/ALC đều 0 trong log, một lần init thành công. Cổng tiếp xúc/settled giữ 1 và restarts 208→208. Cổng chuyển động mở 41/45 bản chụp; bốn bản đầu đang chờ cửa sổ sạch. IMU clip 46 có từ trước và không tăng; bộ đếm invalid mạng 1 cũng không tăng trong lượt.
- WebSocket thu 40 frame DEVICE trong cửa sổ 40 giây, GSR 40/40 và hai vector IMU 40/40; **HR 0/40**. Wi-Fi/MQTT/sync đều 1, lỗi mạng 0; không quy HR thiếu cho việc MQTT chưa nối.
- Replay 32 cửa sổ: baseline, hybrid strict và balanced đều 0/32. Nhánh MSPTD chưa qua quality có ứng viên nhưng chưa có tham chiếu để chấm đúng/sai, không đưa các số đó lên FE.
- Quality IR loại vì RR ngoài dải ở 15/32 cửa sổ, RED 21/32. Đây là điều kiện hiện tại yêu cầu mọi khoảng giữa các đỉnh đều nằm trong 0,3–1,5 giây; có thể loại cả cửa sổ chỉ vì một đỉnh tìm sai. Các lý do khác gồm 8s/4s bất đồng và không đủ đỉnh. Chưa kết luận nguyên nhân vật lý; thêm hướng kiểm cách loại ngoại lệ RR thay vì nới đồng loạt ngưỡng sinh lý.

Bằng chứng local: `hr-A1-20261107-143727-df30b0-ws.json` và `hr-A1-20261107-analysis.json` trong `backend/storage/local/`. Cửa sổ replay khác lịch sử live; không dùng 32 cửa sổ thay số frame WS.

### Lượt B1 đã thu — 2026-11-07, 14:41 (Asia/Saigon)

Trung xác nhận che sáng phía ngoài, cách đặt nhẹ như A1. Thu 45 giây, báo thả tay và bỏ vật che ngay khi xong; giữ nguyên bản đối chứng, LED và lấy mẫu.

- Raw `ppg-20261107-144120-c09b18.csv/.json`: 2.252 mẫu, khoảng cách 19–20 ms, trace dropped 0, không timestamp lặp/lùi. I2C/overflow/gaps/ALC đều 0.
- Clip PPG giữ 3→3 và IMU clip 65→65: có từ trước lúc B1 bắt đầu, không tăng trong lượt. Contact/settled đều 1, restarts 318→318; cổng chuyển động mở 45/45 bản chụp.
- WebSocket `hr-B1-20261107-144121-d2388d-ws.json`: 40 frame DEVICE, GSR và hai vector IMU đủ 40/40, **HR 0/40**. Mạng vẫn đồng bộ, error/fail/drop không tăng; invalid giữ 1.
- Replay cùng cửa sổ: baseline và hybrid strict 0/32; hybrid balanced cũ tạo 4/32 ứng viên, khoảng 75,2–82,6 bpm. Đây không phải nhịp đã được xác nhận đúng và không được gửi lên FE. Quality IR tính được đủ đặc trưng trước cổng chấp nhận ở 16/32 cửa sổ, so với A1 là 2/32; loại vì RR ngoài dải giảm từ 15 xuống 4.
- Hình sóng ở cùng đoạn giây 32–40 có khác biệt, nhưng chưa xác nhận nguyên nhân chỉ là ánh sáng. Bộ đếm contact reset và clipping đã thay đổi giữa hai lượt; không biết chắc trạng thái tiếp xúc có giữ liên tục hay không. Không coi việc người dùng xác nhận cùng vị trí là phép kiểm lực chạm/độ rọi đã đo.

Bảng so và [hình A1/B1](../../backend/storage/local/hr-A1-B1-20261107.png) nằm trong `backend/storage/local/`, báo cáo `hr-A1-B1-20261107-analysis.json`. Có khác biệt đủ để kiểm khả năng lặp lại, chưa đủ kết luận che sáng giải quyết HR hoặc bộ balanced đúng hơn.

### B2 gián đoạn và tạm dừng A2 — 2026-11-07, 14:46 (Asia/Saigon)

B2 đã bắt đầu sau xác nhận của Trung nhưng raw chỉ thu 1.673 mẫu/33,413 giây trước lỗi USB. WebSocket nhận 31 frame ở hai phiên, không phải 40 frame của một phiên ổn định. Trung sau đó báo rút USB vì **chip ESP32-S3 nóng**, không thấy mùi khét/khói/biến dạng. Không quy mất USB/đổi phiên thành ESP tự crash; không dùng lượt này như B2 hoàn chỉnh. Chẩn đoán driver bị công cụ cũ làm mất khi xử lý lỗi, không dựng lại số đếm như dữ liệu quan sát.

Đã sửa công cụ để giữ dữ liệu dở và lỗi gốc, PASS 6 test giả lập. **Không cấp nguồn/nạp/đeo đo thêm; A2 tạm dừng.** Chưa đổi cấu hình công suất hoặc thuật toán HR. [Rà soát nhiệt, code và bước tiếp](05-THERMAL-CHECK.md). Raw/log còn lại giữ local; không tự yêu cầu đo bù. Việc phân tích thuật toán trên dữ liệu đã có có thể tiếp tục offline.

### A2 hoàn tất, chốt đợt thu ban đầu — 2026-11-07, 15:08 (Asia/Saigon)

Sau yêu cầu tiếp tục của Trung, đã Clean/build rồi nạp lại cùng binary `esp32s3_ppg_led10`, kiểm hash và luồng MQTT/WS. Trung xác nhận cụm không nóng bất thường, đặt cổ tay và sẵn sàng A2 không che. Thu đủ 45 giây, báo thả tay và hướng dẫn rút USB khi xong.

Raw `ppg-20261107-150835-f55320.csv/.json`: 2.252 mẫu, timestamp 19–20 ms, trace dropped 0, `capture_status=complete`, không lỗi thu/cleanup. I2C/overflow/gap/clip/ALC 0 trong log, contact/settled 1 và restarts 200→200; motion cho phép 45/45. WebSocket `hr-A2-20261107-150835-8bec03-ws.json`: 40 frame DEVICE một phiên, GSR và hai vector IMU đủ; HR 0/40. IMU clip 4 và network invalid 2 có từ trước lượt, không tăng. Không đo nhiệt độ.

Đợt thu chốt ba lượt đủ và một lượt gián đoạn; B2 không được ghi thành lượt đầy đủ. Đã so cùng khoảng giây 13–30 và vẽ cùng đoạn 22–30 ở cả bốn trace, không chọn riêng đoạn có ứng viên. Chưa có cải thiện HR do che sáng đủ lặp lại, chưa có HR tham chiếu. Xem [bàn giao dữ liệu](05-HR-DATA-HANDOFF.md); bước tiếp theo là thuật toán offline, không yêu cầu đặt cổ tay hoặc thu thêm ở checkpoint này.

### B2 đo lại hoàn tất theo yêu cầu Trung — 2026-11-07, 15:22 (Asia/Saigon)

Trung yêu cầu thu thêm B2 đủ thời gian để hoàn thiện bước thu. Đã bật lại hotspot laptop, reset ESP một lần để khôi phục kết nối (không nạp firmware khác) và xác nhận có frame DEVICE trước khi yêu cầu đặt tay. Trung xác nhận không nóng bất thường, đã che sáng và sẵn sàng; thu đủ 45 giây rồi báo thả tay/rút USB.

- Raw `ppg-20261107-152207-29b374.csv/.json`: 2.252 mẫu, timestamp 19–20 ms, `capture_status=complete`, elapsed 45,0 giây, không lỗi capture/cleanup hoặc trace dropped.
- I2C/overflow/gap/clip/ALC 0, contact/settled 1 và restarts 86→86; motion cho phép 45/45 bản chụp. IMU clip 0, network invalid giữ 1; wifi/mqtt/sync 1, lỗi mạng 0. Chưa đo nhiệt.
- WebSocket `hr-B2-repeat-20261107-152207-3b2a88-ws.json`: 40 frame DEVICE trong một phiên, GSR/IMU đủ; HR 0/40. Bộ strict/baseline replay 0/32, balanced cũ có 3/32 ứng viên chưa biết đúng/sai.

**Bước thu đã đủ bốn lượt hoàn chỉnh**, B2 cũ vẫn là bản gián đoạn lưu riêng. Đã tạo báo cáo mới cho bốn trace đầy đủ, cùng cửa sổ kết thúc giây 13–44 và hình đoạn 22–30, không thay dữ liệu cũ. Hai lượt che có một số ứng viên balanced offline (4/32 và 3/32) trong khi hai lượt không che chưa có; đây là dấu hiệu mô tả, chưa chứng minh nhân quả hoặc HR đúng. [Bàn giao cuối bước thu](05-HR-DATA-HANDOFF.md). Không yêu cầu đo thêm; chuyển sang thuật toán offline trên bộ này.
