# Khôi phục dữ liệu cảm biến sau bản0.3.2

## Bước 3 đã chọn ứng viên offline — 2026-11-06

Hybrid chặt giữ HR C++ valid và bổ sung bằng MSPTD đã kiểm chất lượng khi trống. Qua vòng phát triển và vòng mới sau khóa cấu hình; chưa port/nạp firmware hoặc nghiệm thu HR cổ tay. Xem [báo cáo và giới hạn](05-PPG-QUALITY-EVALUATION.md). ESP vẫn0.3.11; không dùng kết quả NumPy để tuyên bố tài nguyên/tính đúng trên board.

## Bước 2 đã đối chiếu offline — 2026-11-06

Giữ firmware0.3.11. Đã so bộ HR C++ với bản chuyển MSPTDfastv2 trên4 trace,10 BIDMC và38 ca tổng hợp;53 ca kiểm công cụ đạt. MSPTD chưa quality gate tạo nhiều ứng viên nhưng chưa đủ tin cậy để thay driver. Bước tiếp đánh giá chất lượng đi kèm, chưa nghiệm thu cổ tay. Xem [phương pháp/kết quả đầy đủ](05-PPG-ALGORITHM-EVALUATION.md).

## Bước 1 đang làm: chẩn đoán I2C 0.3.11 — 2026-11-06

Đã nạp bản thêm `[PPG-IO]`/`[PPG-INIT]` để xác định giao dịch lỗi và từng lần khởi tạo lại. Giữ nguyên thuật toán HR của 0.3.10, LED, nhịp lấy mẫu và backoff3s. Build4 env/4 header, 76 ca HR, 56 ca driver/12 snapshot ở hai mức LED, 32 FIFO/39 protocol đạt; COM7/hash verified11,199s. Đang quan sát board, chưa tuyên bố sửa được lỗi 6s hoặc HR. Xem [bước 1 và cách đọc bằng chứng](05-PPG-I2C-DIAGNOSIS.md). Các mốc dưới là lịch sử.

## Cập nhật 0.3.10: sửa lỗi nhận nửa nhịp — 2026-11-06

Chẩn đoán bổ sung sau phản hồi của Trung: [so bộ cũ/mới trên cùng sóng và nhiễu kiểm thử](05-HR-DIAGNOSIS.md). Bộ cũ cho số trên file hiện tại nhưng cũng cho số trên nhiễu không có nhịp; bộ hiện tại vẫn chưa đáp ứng lượt đầu ngón tay. Không dùng kết quả ban đầu làm chuẩn độ chính xác và không quy HR trống hoàn toàn cho phần cứng.

Đã sửa lỗi chọn chu kỳ dài gấp đôi khi các xung có biên độ lớn nhỏ xen kẽ: ca 80 bpm từng trả 40 bpm nay đạt. Giữ ngưỡng tương quan 0,60, đối chiếu 8s/4s, hai lượt xác nhận và vô hiệu HR khi cửa sổ bị từ chối. Không đổi lấy mẫu, LED mặc định, schema hoặc TTL.

Đạt 76 ca HR, 49 ca driver/12 snapshot schema ở baseline và LED10mA; 32 ca FIFO, 39 ca protocol, 4 tổ hợp header và 4 build. Baseline RAM 56.060B, flash 930.513B. Đã nạp 0.3.10 COM7, hash verified, 11,199s. Chưa có CI/commit mới.

Sau nạp đã bật lại frontend bằng `npm run dev` vì cổng 5173 chưa chạy; broker/backend được launcher chuẩn bị và healthy. WebSocket nhận 5 frame DEVICE đúng 0.3.10, có session tự động. Kiểm tra Serial 8s khi chưa xác nhận tiếp xúc: wifi/mqtt/sync=1, fail/drop=0, PPG khoảng 50 mẫu/s, io/clip=0; overflow/gaps=15/discarded46 từ trước lượt và không tăng trong lượt, không gọi là không mất mẫu từ boot. IMU bias=1 và không lỗi; contact=0, IR khoảng 300 nên HR null lúc đó phù hợp. Không dùng lượt này chấm chất lượng HR.

Trên cùng 2.335 cửa sổ BIDMC 01–05, tỷ lệ có kết quả tăng 81,88%→90,28%, MAE trên phần được chấp nhận giảm 3,27→0,87 bpm. Vẫn còn 14 cửa sổ sai trên 10 bpm, gồm lỗi lớn khoảng 48 bpm. Đây là bộ phát triển dùng sửa lỗi, không phải đánh giá độc lập hoặc bằng chứng HR cổ tay chính xác. Xem [nguồn, cách chạy và giới hạn](05-PPG-REFERENCE-BENCHMARK.md).

Lượt đầu ngón tay cuối của 0.3.9: 2.251 mẫu/45s, WS 40 frame DEVICE/40 IMU nhưng chỉ 2 frame HR khoảng 74,6–74,7 bpm. Không có tham chiếu độc lập nên không lấy các số đó làm đáp án. **Chưa nghiệm thu HR cổ tay; cần lượt đo mới trên 0.3.10.** Giữ cụm cố định, không yêu cầu tháo/đổi dây. Các mục dưới là lịch sử.

### Đầu ngón tay 0.3.10 sau xác nhận của Trung

Thu 45s được 1.942 mẫu, trace drop=0, không timestamp lùi; có khoảng mất 6.221ms. WS đồng thời nhận 41 frame DEVICE đúng 0.3.10, đủ 41 GSR/41 cặp vector IMU, phiên tự động hoạt động; **0/41 frame có HR**. Không nghiệm thu HR, kể cả tại đầu ngón tay.

Trong khoảng 33s đầu chưa lỗi đọc, contact/settled=1, restarts=38 giữ nguyên nhưng không có cửa sổ HR đạt. Hệ số chu kỳ 8s cao nhất cả lượt chỉ IR 0,150/RED 0,209, thấp hơn cổng 0,60; không phải do GSR/IMU hoặc WebSocket làm mất riêng số HR. Đây là mô tả thuật toán hiện tại, không chứng minh cổng tối ưu hoặc module hỏng.

Ở cuối lượt io tăng 0→1, gap 15→25, overflow 15→24, discarded46→86; PPG ngừng sinh dữ liệu cho ứng dụng khoảng 6,2s rồi tự đọc lại. IMU và mạng vẫn chạy. Driver đánh dấu lỗi và thử khởi tạo lại với khoảng chờ 3s; chưa xác định nguyên nhân giao dịch I2C thất bại hoặc lần khởi tạo không đạt. Không coi khoảng mất đó là toàn bộ nguyên nhân 0 HR vì phần đầu liên tục cũng không qua bộ xử lý. Không đổi ngưỡng hoặc rút ngắn retry khi chưa có bằng chứng.

Raw/chẩn đoán/plot local: `backend/storage/local/ppg-20261106-022934-82bbc4.*`; thống kê WS: `ppg-0310-finger-ws.json`. IR 99.878..116.929, RED 89.710..98.719 chỉ xác nhận có mức phản xạ; không tự xác nhận thấy mạch đập. Không yêu cầu sửa gá/dây hoặc đổ lỗi cho thao tác của Trung. Cần tiếp tục phân biệt lỗi thu nhận và giới hạn bộ xử lý; chưa kết luận chỉ code có thể làm HR ổn định trên cụm hiện tại.

## Cập nhật0.3.9: tín hiệu yếu và hai kênh quang

Ngày2026-11-06, Trung xác nhận cụm đã cố định và yêu cầu chỉ sửa code, không tháo bo hoặc đổi dây. Giữ yêu cầu này cho các bước tiếp theo; không lấy sửa gá làm điều kiện để hoàn thiện phần mềm.

### Thay đổi phần mềm

- Chip PPG200Hz/averaging4 thay100Hz/averaging2; FIFO vẫn50Hz, clock20ms và acquisition profile gửi backend không đổi. Đọc lại FIFO_CONFIG/SPO2_CONFIG phải đúng0x5F/0x2B trước nhận dữ liệu. Đây là thay đổi số xung lấy trung bình, tăng thời gian LED hoạt động mỗi giây; chưa đo công suất hoặc chứng minh tốt hơn trên người. Khi so/train phải giữ thông tin cấu hình theo firmware, không coi hai chế độ hoàn toàn tương đương chỉ vì cùng50Hz.
- Thay sàn biên độ50 counts cố định bằng sàn4 counts kèm đối chiếu năng lượng tín hiệu/nhiễu ước tính từ sai phân bậc hai. Proxy này dựa giả thiết nhiễu trắng, có giới hạn với nhiễu màu/chuyển động, không phải SNR đã hiệu chuẩn hoặc chất lượng phần trăm.
- Tính chu kỳ cả8s/4s cho IR và RED. Mỗi kênh phải tự qua điều kiện biên độ/nhiễu/tự tương quan0,60/nhất quán12%. Chọn kênh có bằng chứng rõ hơn; nếu cả hai tốt nhưng bất đồng thì từ chối. Không còn ép HR dùng IR khi RED đủ điều kiện còn IR quá yếu/nhiễu.
- Cần hai lượt kiểm tra liên tiếp thống nhất trước khi hiện HR; các cửa sổ chồng nhau nên không được gọi là hai phép kiểm độc lập. Tiếp xúc mới cần khoảng13s trước kết quả đầu. Khi điều kiện thất bại vẫn vô hiệu ngay; không giữ HR cũ hoặc nới TTL3s.
- Giữ LED mặc định0x1F (~6,2mA danh định); bản thử10mA không được chọn làm mặc định. `[PPG-RATE]` thêm redRecent/source/powerRatio để chẩn đoán; không thêm trường vào MQTT hoặc gán quality giả.

### Bằng chứng trước khi đo board

PASS71 ca cửa sổ C++ gồm tín hiệu8..12 counts, kênh thay thế, hai kênh bất đồng, đỉnh phụ, nền trôi, đổi HR, mất xung/mẫu và xác nhận hai cửa sổ. Benchmark48 lượt nhiễu trắng/màu từ nhiều seed có0/2400 cửa sổ được chấp nhận. Đây là bộ dữ liệu tổng hợp hữu hạn, không chứng minh không bao giờ nhận nhầm nhiễu.49 ca driver/12 snapshot qua serializer/schema đạt ở cả baseline và LED10mA;32 ca FIFO/39 ca protocol và4 tổ hợp header đạt.

Replay trên các file đo cũ: đầu ngón tay6/24 cửa sổ được chấp nhận,73,58..77,55bpm; các file mặt trong cổ tay/che sáng/LED10mA vẫn không có cửa sổ đạt. Không dùng replay này để khẳng định bản mới đã đo ổn định hoặc sai số giảm; việc tăng averaging phải đo lại trên board.

Build4 env đạt: baseline RAM56060B/flash930529B; network-check56060B/930541B; LED10mA56060B/930545B; serial-check29516B/335265B. Nạp baseline0.3.9 COM7/hash verified13,544s. Chưa đo lại HR cổ tay sau nạp; chưa có CI/commit mới.

### Kết quả board0.3.9 sau nạp

Trung xác nhận đặt lại mặt trong cổ tay/che sáng và giữ yên. Lượt35s thu1.752 mẫu, khoảng timestamp20ms theo clock mẫu ước tính, không trace drop/timestamp lùi. WS nhận30 frame nguồn DEVICE, phiên AUTO, firmware0.3.9; đủ30 vector IMU,0 HR hợp lệ. Hai kênh được xét nhưng không có kênh qua đủ kiểm tra chu kỳ. Hệ số cả8s trong35 dòng log: IR cao nhất khoảng0,290, RED khoảng0,409; một vài cửa sổ4s vượt0,60 nhưng không đủ bằng chứng để bỏ điều kiện8s/xác nhận liên tiếp.

PPG n7655→9356 trong154867→188864ms (khoảng50,03 mẫu/s); io/clip giữ0, overflow/gaps giữ3 và discarded34 là số startup, không phát sinh thêm trong lượt. Contact/settled giữ1, restarts giữ21. Network wifi/mqtt/sync=1, fail/drop0; invalid giữ1 từ startup. LoopGap24ms/pollMax23ms, thời gian xử lý HR lớn nhất4.930µs (4,93ms), heapMin183860B, network stack watermark3684 theo API framework. Không suy ra các giá trị này từ hằng số, cũng không coi là nghiệm thu lâu dài.

Raw/chẩn đoán/plot ở `backend/storage/local/ppg-20261106-020011-fcf745.*`, không đưa vào Git. `powerRatio=0` khi source=0 chỉ nghĩa chưa chọn kênh HR hợp lệ, không phải đã đo mức nhiễu bằng0. Cảm biến vẫn đọc raw, Dashboard vẫn nhận GSR/IMU qua MQTT; HR null theo kết quả xử lý, không phải toàn bộ luồng truyền bị mất.

**Bàn giao phần mềm0.3.9: đã triển khai, build/test và nạp. Mục tiêu HR cổ tay ổn định: chưa đạt.** Không sửa/gỡ cụm theo yêu cầu Trung; không đặt số HR cố định, forward-fill hoặc hạ điều kiện để ép hiện. Chưa có phép đối chiếu độc lập nên chưa thể chứng minh sai số HR hoặc cam kết một thay đổi code tiếp theo sẽ giải quyết giới hạn tín hiệu. Không lặp nạp thêm bản chỉ để có số hiển thị. Bước tiếp khi tiếp tục nghiên cứu phần mềm là đánh giá thuật toán trên dữ liệu PPG có nhịp tham chiếu và tách dữ liệu chỉnh tham số/đánh giá; các file cổ tay hiện tại không có đáp án để chấm độ chính xác.

Các mục bên dưới giữ lịch sử0.3.8 trở về trước; không dùng mô tả cổng IR-only/sàn50 counts cho bản0.3.9.

## Cập nhật0.3.8: phân biệt nhịp lặp với nhiễu

Ngày2026-11-06, bản0.3.7 thêm thu sóng thô USB: `p` bật tối đa60s, `q` dừng; mặc định tắt. `scripts/capture_ppg_trace.py --port COM7 --seconds 35` lưu CSV/chẩn đoán trong `backend/storage/local/`, đã được Git bỏ qua. Dashboard vẫn dùng MQTT. Không commit dữ liệu đo trên người hoặc credential.

Sau xác nhận tiếp xúc cổ tay,0.3.6 vẫn có HR76,4..178,2 trong23/32 dòng hợp lệ dù contact/settled ổn định. Sửa ngưỡng tiếp xúc chưa giải quyết hết lỗi. Sóng thô có thay đổi mức nền lớn xen đoạn gần phẳng, chưa có nhịp lặp đủ rõ để xác nhận HR.

Trung thử đầu ngón tay:1.751 mẫu/khoảng35s, khoảng mẫu lớn nhất40ms, không tràn hàng đợi trace hoặc timestamp lùi. Một số đoạn lặp rõ hơn cổ tay nhưng vẫn có thay đổi nền lớn. Thuật toán cũ báo HR77,7..144,3 và coi cả35 dòng chẩn đoán là hợp lệ; counter overflow/gap không tăng trong lượt đo. Chưa có HR tham chiếu, không lấy mức khoảng80 làm đáp án mặc định.

Bản0.3.8 thay bắt đỉnh + trung vị/EMA bằng `processing/ppg_rate.h`:

- Không đổi RED/IR FIFO50Hz, LED, acquisition profile hoặc sóng thô. Chỉ đổi phép ước tính HR.
- Lọc0,5..4Hz, bỏ2s quá độ rồi xét cửa sổ8s mỗi1s. Cần khoảng12s tiếp xúc liên tục trước kết quả đầu; có độ trễ cửa sổ.
- Tự tương quan trong40..200bpm, hệ số tối thiểu0,60. Kết quả cả8s và4s mới nhất phải thống nhất trong12%; kênh đỏ chỉ phủ quyết khi có chu kỳ rõ nhưng khác IR. Từ chối biên độ/đoạn cuối quá yếu.
- Cửa sổ bị từ chối làm HR không hợp lệ ngay; không giữ số cũ hoặc gia hạn timestamp. TTL3s giữ nguyên; mất tiếp xúc/lỗi/mất mẫu khởi động lại cửa sổ.
- Ngưỡng kỹ thuật thử nghiệm, chưa kiểm định y khoa. Nhiễu tuần hoàn vẫn có thể lọt; chưa có tham chiếu nên chưa nghiệm thu độ chính xác.
- Ngừng tính/in SpO2 theo công thức thử nghiệm cũ. MQTT chưa từng gửi SpO2; schema không đổi.
- `[PPG-RATE]` ghi hệ số tương quan và thời gian xử lý lớn nhất. `[PPG-REG] windows` đếm cửa sổ được chấp nhận, không đếm nhịp.

Test đạt16 ca cửa sổ (nhịp sạch40..200, đỉnh phụ, đổi60→120, nền trôi, hai kênh bất đồng, sóng phẳng/nhiễu/trôi ngẫu nhiên, mất mẫu, mất xung),49 ca driver với ngoại vi giả và12 snapshot qua serializer/schema. Có kiểm tra driver không gia hạn timestamp khi đọc cache và vô hiệu HR khi cửa sổ mới bị từ chối dù tiếp xúc vẫn có. Script kiểm tra driver chạy cả ca cửa sổ, không đổi tên check CI.

Replay cục bộ qua bộ xử lý mới: từ chối các cửa sổ cổ tay đã thu; lượt đầu ngón tay chỉ1/24 cửa sổ đủ điều kiện, khoảng71,8bpm. **Không coi đây là bằng chứng đo ổn định hoặc chính xác hơn.** Số hợp lệ giảm vì từ chối tín hiệu chưa đủ rõ; không hạ ngưỡng để khớp file hoặc làm biểu đồ kín. Cần thử lại trên board và đối chiếu.

Ba build và4 tổ hợp header đạt;39 ca protocol đạt. Nạp COM7 thành công11,220s/hash verified; static RAM52804B, flash929961B. Network-check flash929973B; serial-check RAM26260B/flash334641B. Chưa có CI/commit mới.

### Board thật0.3.8: đầu ngón tay

Trung xác nhận đặt lại sau nạp. Capture35s có1.753 mẫu, timestamp cách20ms theo đồng hồ mẫu ước tính, không trace drop hoặc thời gian lùi. Đồng thời WS nhận30 frame DEVICE0.3.8, đủ30 vector IMU,7 frame có HR73,2..78,8bpm. Serial35 dòng cho thấy contact/settled giữ1,7 cửa sổ được chấp nhận; các cửa sổ khác bị từ chối do chu kỳ chưa rõ/không đồng ý giữa hai khoảng, không phải mất toàn bộ transport.

PPG n4581→6284 trong93872→127867ms, io/clip giữ0; overflow/gap giữ28, discarded59 đều là số đã có từ startup, không được diễn giải thành không mất mẫu từ lúc boot. Network wifi/mqtt/sync=1; fail/drop=0, invalid giữ1 từ startup, loopGap/pollMax giữ26ms. Thời gian xử lý HR lớn nhất4.112µs (khoảng4,1ms); heapMin cuối177976B, network stack watermark3564 theo API framework. Đây là cửa sổ quan sát, chưa chứng minh không có lỗi lâu dài hoặc không rò bộ nhớ.

HR vẫn chưa liên tục.7/30 là độ sẵn có trong lần thử này, không phải độ chính xác. Không so trực tiếp với35/35 cũ như hai phép đo có cùng tín hiệu; khác lượt tiếp xúc và thuật toán mới chủ động từ chối. Chưa có tham chiếu nên chưa kết luận73..79 là nhịp đúng.

### Board thật0.3.8: cổ tay

Trung xác nhận áp lại cổ tay và giữ yên. Capture35s có1.753 mẫu, khoảng timestamp20ms theo clock ước tính, không trace drop/timestamp lùi. WS nhận30 frame DEVICE0.3.8/30 vector IMU nhưng0 frame HR hợp lệ. Contact/settled giữ1; IR105968..111862 và RED59540..65784, chủ yếu là mức nền/trôi và một số bước lớn, chưa có chu kỳ đủ rõ.

PPG io/clip giữ0, overflow/gaps giữ28, discarded59; loopGap/pollMax giữ26ms, wifi/mqtt/sync=1. Bộ xử lý HR tối đa4.233µs (4,233ms). Không phát sinh thêm lỗi lấy mẫu trong lượt này; chưa được gọi là không mất mẫu từ boot.

Đã thử replay riêng trong thư mục tạm, bỏ hẳn điều kiện biên độ50 counts nhưng giữ kiểm tra chu kỳ: vẫn không có cửa sổ đạt, hệ số cả8s chỉ khoảng0..0,29. Không đổi code/firmware theo thí nghiệm này. Như vậy thiếu HR ở lượt cổ tay không chỉ do ngưỡng biên độ cứng hoặc mất WebSocket. Chưa đủ bằng chứng khẳng định cơ chế quang/tiếp xúc cụ thể nào gây tín hiệu yếu; cần thử vị trí/tiếp xúc có kiểm soát và HR tham chiếu. Không tăng LED/hạ ngưỡng hoặc giữ số cũ để tạo cảm giác ổn định.

### Board thật0.3.8: mặt trong cổ tay

Ngày2026-11-06, Trung xác nhận chuyển sang mặt trong cổ tay, áp ô kính và giữ yên. Thu35s có1.753 mẫu, khoảng timestamp20ms theo clock ước tính, không trace drop/timestamp lùi. WS nhận30 frame DEVICE0.3.8,30 có IMU,0 có HR hợp lệ. Không nạp lại hoặc đổi tham số giữa ba vị trí.

IR103695..106400, RED60267..63720. Contact/settled giữ1, contactRestarts giữ50 trong lượt đo. Hệ số tương quan cả8s cao nhất trong35 dòng chẩn đoán khoảng0,265, dưới ngưỡng0,60; có những bước thay đổi nền/ngẫu nhiên nhưng chưa thấy chu kỳ đủ rõ. Không lấy mức DC cao làm bằng chứng đã thu được mạch đập tốt.

PPG n23012→24715 trong461868→495869ms; io/clip giữ0, overflow/gaps giữ28, discarded59. Network wifi/mqtt/sync=1, fail/drop=0, invalid vẫn1 từ startup; loopGap/pollMax giữ26ms. Thời gian xử lý HR lớn nhất từ boot4.625µs (4,625ms), heapMin177976B. Đây là kết quả trong cửa sổ quan sát, không phải chứng nhận không mất mẫu từ boot hay HR chính xác.

CSV/chẩn đoán/plot riêng tư ở `backend/storage/local/ppg-20261106-012813-67472f.*`, đã bị Git bỏ qua. Không đưa dữ liệu đo trên người vào commit. Trong lượt này không sửa firmware, chỉ thu/đối chiếu.

### Board thật0.3.8: che sáng quanh cảm biến

Sau ảnh nghiêng, chưa xác nhận được toàn bộ mặt kính áp đều. Trung thử che ngoài cụm bằng vải tối màu, không lót giữa kính/da. Thu35s:1.752 mẫu, khoảng timestamp20ms theo clock ước tính; không trace drop/timestamp lùi. WS nhận30 frame DEVICE/30 IMU,0 HR.

IR44469..121480, RED30078..93016; contactRestarts109→115 (6 lần) trong lượt này. Đầu lượt có bước nền rất lớn rồi mới ổn định; vì tiếp xúc cũng thay đổi nên không thể quy toàn bộ khác biệt cho ánh sáng hoặc kết luận che sáng chắc chắn không có tác dụng. Hệ số cả8s trong log cao nhất khoảng0,303, chưa đủ điều kiện HR.

PPG io/clip giữ0, overflow/gaps giữ28, discarded59; loopGap/pollMax26ms, wifi/mqtt/sync=1, fail/drop0, invalid giữ1 từ startup. Cửa sổ quan sát không có lỗi lấy mẫu mới; xử lý HR tối đa từ boot4,625ms. CSV/chẩn đoán/plot lưu local ở `backend/storage/local/ppg-20261106-013431-9b7b2c.*`, không commit dữ liệu người thật.

Trạng thái: phần mềm0.3.8 đã build/test/nạp, transport qua WS hoạt động; **HR cổ tay chưa đạt nghiệm thu**. Chưa xác định được nguyên nhân quang/tiếp xúc cụ thể, chưa tuyên bố cấu hình tối ưu hoặc HR chính xác. Bước tiếp theo chuẩn bị [bản thử dòng LED riêng](05-PPG-OPTICAL-TRIAL.md):6,2→10mA danh định, không đổi tốc độ/ADC/thuật toán/ngưỡng hoặc mặc định. Cần đo thật trước khi quyết định giữ hay quay về baseline.

Các phần sau giữ lịch sử0.3.6 trở về trước.

## Cập nhật0.3.6: HR hiện rồi mất

Bản hiện tại **0.3.6**, đã nạp COM7/hash verified. Trung báo HR có đường đứt đoạn. Probe ở0.3.5 nhận15 frame WS DEVICE,15 có IMU nhưng chỉ6 có HR; đây là triệu chứng thật, không chỉ do vẽ biểu đồ.

Đã xác định một nguyên nhân ở phần kiểm tra tiếp xúc: mỗi mẫu IR<50000 làm xóa lịch sử HR, trong khi log cổ tay trước có IR28000..49000 và nền không áp da khoảng500..1000. Thay bằng cổng tiếp xúc có hysteresis: nhận từ10000, mất dưới6000 đủ100ms; chờ ổn định1s trước bắt nhịp, bước nhảy IR>15% trong một mẫu làm khởi động lại bộ lọc. Đây là ngưỡng kỹ thuật phát triển dựa trên lần đo này, không phải phép đo chất lượng hoặc bảo đảm HR đúng cho mọi người/vị trí.

Không kéo dài TTL3s và không forward-fill/giữ số cũ trên Dashboard. Khi tín hiệu thật không còn dùng được, HR vẫn null. `[PPG-REG]` thêm contact/settled/restarts/beats để phân biệt mất tiếp xúc với chưa bắt đủ nhịp. Schema MQTT và `signal_quality` không đổi.

Test driver đạt46 ca, thêm tín hiệu trung bình30000 và dao động qua50000 cũ, mất/đặt lại tiếp xúc, đổi mức DC mạnh;11 snapshot qua serializer/schema. FIFO32/core39 vẫn đạt. Nạp0.3.6 đạt trong56,084s, RAM static47948 byte/flash928677 byte. Log ngay sau nạp có IR≈630 và contact=0 nên chưa nghiệm thu độ ổn định HR cổ tay; không dùng kết quả synthetic làm bằng chứng đã đo ổn định trên người. Counter startup PPG ở lần boot này vẫn có490 overflow/gap và521 discard trước khi đọc đều; cần tiếp tục kiểm chứng phần startup, không che mất mẫu.

Các mục bên dưới là mốc0.3.5 trước thay đổi cổng tiếp xúc.

### Kết quả cuối lượt0.3.6

- Ba build đều đạt: bản dùng thật47948B RAM static/928677B flash; network-check47948B/928689B; serial-check21404B/333345B. Header4 tổ hợp đạt, driver46/FIFO32/core39; warning macro I2C_BUFFER_LENGTH của SparkFun vẫn có, không sửa vendor.
- Lượt kiểm tra tiếp theo sau nạp đọc12 dòng: IR624..651, contact0/settled0, không có HR hợp lệ. Đây là trạng thái chưa nhận tiếp xúc; chưa được phép tuyên bố bản mới đã đo ổn định tại cổ tay. Chờ Trung đặt lại sau nạp rồi đo cùng điều kiện. Không so tỷ lệ có HR mới với6/15 cũ khi điều kiện tiếp xúc khác nhau.

Ngày2026-11-06, máy Trung, ESP trên COM7. Firmware sửa hiện tại **0.3.5**, đã nạp thành công. Không đổi Wi-Fi, credential, topic hoặc phiên tự động. Không dùng USB để đưa dữ liệu lên Dashboard; USB chỉ dùng nạp/log.

## Triệu chứng và nguyên nhân đã đối chiếu

- Dashboard vẫn nhận GSR và mở phiên; Serial có wifi/mqtt/sync=1. Vì vậy không phải toàn bộ WebSocket ngừng chạy.
- Bản0.3.2 chỉ nhận IMU ID0x68. Board thật trả WHO_AM_I=0x74 tại địa chỉ0x68, nên không vào nhánh đọc. Theo driver MPU6515 do InvenSense công bố trong kernel,0x74 là ID MPU6515, có ACCEL_CONFIG2 khác6050.
- PPG n=0, lặp reset mỗi3 giây, OVF=1 trước khi pop mẫu. Chỉ đổi đọc metadata sang từng thanh ghi hoặc bật rollover chưa giải quyết được vòng lỗi. Cần pop/bỏ dữ liệu lỗi để counter được xóa trước khi nhận lô mới; không liên tục reset chip trước lần pop đầu.

## Thay đổi

- Thêm riêng profile ID0x74: ACCEL_CONFIG2=0x45 (DLPF5 và FIFO1KiB theo driver gốc), kiểm tra readback; giữ ±2g/±250dps và acquisition50Hz. ID chưa hỗ trợ khác vẫn bị từ chối. Chưa xác minh công thức nhiệt độ riêng6515 nên không áp công thức6050 để hiển thị một nhiệt độ có thể sai.
- PPG dùng rollover như SparkFun gốc, đọc riêng WR/OVF/RD, vẫn đọc dữ liệu0x07 theo lô. Khi overflow/đầy không chắc chắn: bỏ lô bằng pop tối đa32 mẫu, xóa lịch sử HR/clock rồi đọc lô mới. Lỗi I2C/nguồn vẫn phục hồi bằng re-init, không bỏ qua lỗi hoặc coi số cũ là hợp lệ.
- Thêm `[PPG-REG]` có wr/rd/ovf/int/discarded để đối chiếu. Đếm cả lô mất/discard, không đổi counter thành0 cho đẹp.
- Giữ ngưỡng nhận tiếp xúc IR50000 và quality chưa ước lượng; khi không có tiếp xúc/nhịp hợp lệ HR vẫn null.

## Bằng chứng board thực

- Nạp0.3.3/0.3.4/0.3.5 qua COM7 thành công, hash flash verified. Mốc0.3.3/0.3.4 là chẩn đoán trung gian, không phải bản bàn giao cuối.
- Với0.3.4, probe cookie→WS nhận4 frame DEVICE thật, session AUTO, hai vector có số và timestamp tăng1002ms. Đây là bằng chứng ESP→Wi-Fi→MQTT→backend→WS; không phải screenshot DOM mới.
- Với0.3.5, Serial PPG n4420→4870 trong ms92871→101863:450 mẫu/8,992s ≈50,04Hz; IMU n4548→4998 cùng đoạn cũng≈50,04Hz. Đó là một cửa sổ đo, chưa chứng minh không mất mẫu ở mọi điều kiện.
- Trong cửa sổ này PPG overflow/gaps/lostMin giữ138 và discard169, io=0/clip=0; IMU io/overflow/gaps/clip=0. Không che lỗi startup: các số138/169 đã phát sinh trước cửa sổ ổn định, chưa xác định chính xác từng lần mất; vẫn cần kiểm tra startup dài hơn.
- Đã có một thời điểm PPG báo VALID khi tiếp xúc thay đổi, chưa có thiết bị tham chiếu và chưa coi HR đó là chính xác. Sau đó IR giảm còn khoảng500 và HR null đúng điều kiện. Trung xác nhận đang thử cổ tay; đang hướng dẫn áp đúng ô kính và đo lại, chưa nghiệm thu HR cổ tay.
- IMU bias đã chốt khoảng−0,62/−2,11/+0,27°/s trên hệ trục driver. Số đo đứng yên vẫn có dao động nhỏ; không ép về0. Norm gia tốc quanh10,07m/s² vẫn có sai lệch cần hiệu chuẩn sáu mặt/đối chiếu, không coi đây là chuyển động tuyến tính10m/s².

## Kiểm tra phần mềm

- PASS32 ca FIFO C++: đọc lô/wrap/lỗi, bỏ32 mẫu khi đầy và lỗi giữa quá trình bỏ lô.
- PASS41 ca driver sản xuất với fake ngoại vi, gồm profile6515, giữ ID lạ bị từ chối và phục hồi sau overflow.11 snapshot từ driver qua serializer C++ và schema backend runtime; nguồn SYNTHETIC.
- PASS39 ca core/protocol/schema. Build ba env và header tương thích được ghi ở nhật ký sau khi chạy xong. Chưa push/CI mới, chưa merge.

## Cách đặt khi kiểm tra HR

Mặt ô kính đen có vùng phát/thu quang hướng vào da. Cả ô kính áp nhẹ, không chỉ chấm đèn đỏ; không che kính bằng vải/băng dính và không để cụm bo khác kê mắt quang cách da. Chữ in bo/chiều USB không quyết định chiều đo HR. Giữ ổn định ít nhất30 giây để đối chiếu; nếu không có nhịp hợp lệ thì giữ null thay vì hạ ngưỡng hàng loạt.

## Nguồn đối chiếu

- [Nghiên cứu so sánh15 bộ bắt nhịp PPG với nhịp tham chiếu ECG](https://pmc.ncbi.nlm.nih.gov/articles/PMC9393905/). Đây là nguồn về cách đánh giá; PpgRate của dự án không phải bản port một thuật toán đã được nghiên cứu này kiểm định.

- [Driver InvenSense MPU6515 trong kernel: ID, ACCEL_CONFIG2, FIFO](https://android.googlesource.com/kernel/msm/+/android-msm-dory-3.10-kitkat-wear/drivers/iio/imu/inv_mpu6515/inv_mpu_iio.h).
- [MAX30102 datasheet: pop FIFO và OVF_COUNTER](https://www.analog.com/media/en/technical-documentation/data-sheets/MAX30102.pdf).
