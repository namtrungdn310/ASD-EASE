# Giảm nhận nhầm chu kỳ dài của HR

**Cập nhật 2026-11-08:** đã thử lại với dây USB mới; raw đủ nhưng MQTT vẫn mất kết nối, WS chỉ 13/60 frame. Trung nghe bíp nhưng chưa đếm được mạch, nên không có tham chiếu cho lượt này. Đang bổ sung log mạng trong 0.3.22, giữ nguyên thuật toán HR 0.3.20. Xem [bước kiểm đường truyền](05-HR-LINK-DIAGNOSIS.md). Không gán số 75 riêng lẻ cho các raw này.

**Mốc đối chiếu mới:** Trung báo đã đếm 75 nhịp trong 60 giây, tương đương khoảng 75 bpm, sau đó xác nhận **đếm riêng, không đồng thời với cảm biến**. Đã lưu riêng như số đếm tay thô; không gán cho raw cũ hoặc chấm sai số từ số này. Không đưa 75 vào cấu hình firmware hoặc dùng nó thay tín hiệu cảm biến. Đang chuẩn bị một lượt raw/WS 60 giây có báo âm đầu/cuối để lấy số đếm đồng thời; chưa bắt đầu khi chưa có xác nhận sẵn sàng.

**Lượt đếm đồng thời đã thu xong:** sau khi Trung xác nhận sẵn sàng, thu 60 giây với một bíp bắt đầu/hai bíp kết thúc, firmware vẫn 0.3.20. Raw `ppg-20261107-224325-a638c2.csv/.json` đủ 3.002 mẫu, complete, khoảng mẫu tối đa 40 ms, không mất trace hoặc lỗi capture. WS `ppg-manual-pair-20261107-224425-f556dc.json` nhận 28 frame; 6 frame có HR 70,7–72,6 bpm. Khoảng nhận gián đoạn dài nhất 32,234 giây; log mạng có một lần lỗi, nên chưa đạt luồng cập nhật đều trong lượt này. Về sau có cổng chuyển động chặn HR và reset cửa sổ; chưa sửa ngưỡng. Đã báo Trung thả tay ngay sau khi thu. **Chờ số đếm của chính lượt này**, chưa gán số 75 cũ hoặc chấm sai số. Báo cáo `ppg-manual-pair-first-analysis.json` lưu hash và tách tình trạng mạng/HR.

**Kết luận vòng 2026-11-07: chưa đạt.** Bản thử 0.3.21 không cải thiện được lượt cổ tay mới, nên không giữ thay đổi thuật toán này trong mã chạy. Khôi phục core 0.3.20; giữ thêm 4 ca kiểm thử và tùy chọn replay raw trong công cụ kiểm tra. Cấu hình Wi-Fi nhà do Trung cập nhật được giữ nguyên khi build/nạp lại.

Trung xác nhận các đoạn thấp 43–52 bpm ở các lượt trước là nhận nhầm và yêu cầu tối ưu tiếp. Ghi đây là đánh giá của người dùng trên ca thử; chưa có HR tham chiếu đồng bộ để chấm sai số từng cửa sổ. Các mục dưới là lịch sử thử nghiệm, không phải những cải tiến đã được nghiệm thu.

## Giả thuyết và phạm vi

Tracker0.3.20 cộng điểm phổ và tự tương quan. Một đỉnh tương quan ở2T có thể vẫn có điểm khá cao dù phổ tại1/(2T) yếu; prior theo thời gian có thể làm giả thuyết này tồn tại lâu. Không kết luận mọi HR thấp là nhận nhầm nửa nhịp, không nhân đôi mọi40–50 hoặc ép số về60–100.

Ứng viên vòng này thay **duy nhất cách kết hợp bằng chứng mỗi cửa sổ** bằng trung bình hình học `sqrt(spectral_support * autocorrelation)`. Nếu chỉ có tương quan mà gần như không có năng lượng phổ tại chu kỳ ứng viên, điểm không còn được bù bằng phép cộng. Không bật lại làm trắngAR(1) từng thử không đạt; giữ bộ lọc nhân quả, hai kênh, prior, xác nhận cú nhảy/startup, smoother và FE dự báo15giây.

Đã có42coretest đạt: thêm72/100/150bpm biên độ nhịp lớn/nhỏ xen kẽ không được khóa về nửa nhịp. Các ca40bpm thật, hài mạnh và startup80↔40 vẫn giữ kiểm tra. Không sửa expected chỉ để ứng viên đạt.

## Cách chấm trước khi chọn nạp

- Replay nguyên raw các lượt cũ và thêm hai lượt0.3.19/0.3.20 gần nhất. Chạy C++thực, không chọn riêng đoạn đẹp. Raw cổ tay không có HR chuẩn: chỉ báo tỷ lệ ước tính, dải số, khoảng trống và số ứng viên thấp bị người dùng phản ánh.
- So trên cùng mô phỏng có nhịp gốc và nhiễu không mạch. Giữ các seed/biên độ, không sửa nhãn để biến số sai thành đúng.
- Dữ liệu BIDMC/seed đã xem là hồi quy, không gọi là kiểm độc lập. Báo cả MAE/lỗi lớn/coverage, không chỉ số thấp biến mất.
- Không chọn chỉ vì xóa được mọi HR. Nếu giảm sai trên dữ liệu có đáp án và còn HR trên các raw khó, mới đưa sang build/nạp và một lượt cổ tay có xác nhận.

## Kết quả vòng đầu và phép thử tiếp theo

Phép nhân bằng chứng đơn thuần chưa đủ: replay lượt 0.3.20 vẫn trả về 40 bpm. Trên BIDMC 01–05, ứng viên nhận 2.270/2.330 cửa sổ, MAE 0,84 bpm, có 23 sai lệch trên 10 bpm. Trên mô phỏng không có mạch, vẫn nhận nhầm 142/784 cửa sổ. Không chọn bản này chỉ vì số nhìn hợp lý hơn.

Kiểm tra riêng cửa sổ trả về 40 bpm cho thấy chu kỳ ứng viên cách đỉnh tự tương quan gần nhất 33 mẫu ở IR và 14 mẫu ở RED. Giá trị trên sườn đường tương quan đã bị chấm như một chu kỳ có thật. Đây là bằng chứng cho một cửa sổ cụ thể; không chứng minh mọi nhịp thấp đều sai.

Ứng viên tiếp theo vẫn dùng phép nhân, nhưng giảm điểm còn 1/4 nếu không có cả đỉnh phổ trong ±0,15 Hz và đỉnh tự tương quan trong ±2 mẫu quanh chu kỳ ứng viên. Đây là trọng số mềm, không phải ngưỡng HR tối thiểu mới. Giữ các tham số khác như cũ. Trước replay, 43 ca core đạt, gồm ca nhịp 80 bpm dưới nền trôi mạnh, nhịp lớn/nhỏ xen kẽ và 40 bpm thật. Lưu báo cáo mới riêng, không ghi đè kết quả vòng đầu.

Đối chiếu đúng cùng input với core 0.3.20 lưu trước đó: nhiễu nhận nhầm giảm 258 xuống 86/784; BIDMC giảm 22 xuống 13 lỗi trên 10 bpm. Đánh đổi: mô phỏng có nhịp giảm 2.210 xuống 2.080/2.352 cửa sổ và lỗi lớn tăng 10 lên 16. Vì vậy chưa chọn chỉ dựa trên kết quả nhiễu. Báo cáo `ppg-harmonic-matched-baseline.json` có hash input trùng nhau từng ca.

Phép thử tiếp theo thay phép cộng IR/RED bằng trung bình hình học khi cả hai kênh dùng được. Giả thuyết: một chu kỳ trôi nền chỉ mạnh ở một kênh không nên bù cho kênh kia. Kênh còn lại phẳng/lỗi vẫn dùng kênh tốt theo logic cũ. Đây là thử nghiệm riêng, lưu báo cáo riêng; nếu làm mất tín hiệu có nhịp nhiều hơn thì không giữ chỉ vì xóa được số thấp.

Không giữ phép nhân IR/RED: số cửa sổ có nhịp mô phỏng giảm tiếp xuống 2.012/2.352, BIDMC không tốt hơn; lượt raw 0.3.20 giảm từ 18 xuống 4 cửa sổ có ước tính và vẫn có số thấp. Đã trả phép gộp hai kênh về trung bình như trước. Báo cáo ứng viên bị loại vẫn giữ ở `ppg-harmonic-dual-development.json`.

Ứng viên giảm điểm sườn phổ/tương quan được đưa sang hồi quy BIDMC 16–20 và seed 11717/11731. Đây là dữ liệu đã dùng ở vòng trước, không gọi là test độc lập. Không thay ngưỡng trong khi chạy. Mức giảm nhận nhầm nhiễu là lý do để thử tiếp; mức giảm coverage và một số lỗi mô phỏng tăng là giới hạn phải công bố.

Hồi quy phép nhân + giảm điểm sườn: mô phỏng có nhịp nhận 4.184/4.704, MAE 1,17 bpm, 57 lỗi lớn; BIDMC 16–20 nhận 2.192/2.330, MAE 1,48 bpm nhưng có 64 lỗi lớn; nhiễu nhận 118/931. Chưa chọn nạp: kiểm ca `strong_harmonic_48_6` cho thấy phép nhân có thể ưu tiên hài 96 khi tần số cơ bản 48 yếu. Đổi ưu tiên sai từ thấp sang cao không giải quyết bài toán.

Phép thử tối thiểu cuối vòng này: trả cân bằng phổ/tương quan về phép cộng của 0.3.20, chỉ giữ giảm điểm khi ứng viên không gần đỉnh thật. Mục đích là sửa lỗi chấm sườn đã quan sát, tránh làm mất lợi thế nhận tần số cơ bản của bản cũ. Tiếp tục dùng cùng bộ input, báo cáo riêng; không sửa nhãn hoặc ngưỡng để đạt kết quả đẹp.

## Quyết định thử 0.3.21

Giữ **phép cộng cũ + giảm điểm sườn**, không giữ các phép nhân đã thử. Replay lượt 0.3.20 có 26/34 cửa sổ ước tính, 74,7–79,9 bpm; bản cũ trên cùng raw có 24/34, 40,0–76,8 bpm. Cửa sổ replay không bằng số frame WebSocket: pipeline replay bắt đầu lại từ raw và không có trạng thái worker trước lúc thu.

Trên bộ phát triển, mô phỏng có nhịp nhận 2.117/2.352, MAE 0,81 bpm/15 lỗi trên 10; nhiễu nhận nhầm 125/784; BIDMC 01–05 nhận 2.272/2.330, MAE 0,70 bpm/13 lỗi lớn. Bản 0.3.20 trên cùng input lần lượt có 2.210/2.352, MAE 0,67/10 lỗi; nhiễu 258/784; BIDMC 2.274/2.330, MAE 0,85/22 lỗi.

Hồi quy seed đã xem: 4.255/4.704 cửa sổ mô phỏng có nhịp, MAE 1,10 bpm/53 lỗi lớn; nhiễu 152/931. BIDMC 16–20 có 2.221/2.330, MAE 1,55 bpm/**72 lỗi lớn**. Số lỗi lớn BIDMC tăng so với 56 ở bản trước; không kết luận bản mới tốt hơn trên mọi dữ liệu hoặc đã xác nhận độ chính xác cổ tay. Đây là bản thử kỹ thuật sửa lỗi chọn sườn, chưa thay profile mặc định hoặc nghiệm thu HR.

43 ca core đạt. Đã kiểm tra 8 ca tích hợp driver với transport giả. Dự kiến build/nạp profile `esp32s3_hr_tracker`, phiên bản 0.3.21, rồi kiểm đúng một lượt cổ tay 45 giây; chỉ yêu cầu đặt tay khi đã nạp và nối lại. Không đổi phần cứng/GSR/IMU/schema hoặc dữ liệu gốc ở FE. Số dự báo FE luôn có nhãn/nét đứt và không dùng làm HR tham chiếu.

## Đo thật: không đạt, không giữ bản thử

Đã build/nạp 0.3.21, upload xác nhận hash. Trước đo, self-test đạt và nhận 5 frame DEVICE đúng phiên bản qua WebSocket. Sau khi Trung xác nhận đặt nhẹ cổ tay, thu đủ 45 giây: 2.252 mẫu, khoảng mẫu tối đa 20 ms, không mất mẫu trace, không lỗi I2C/FIFO/clipping. WebSocket nhận 45 frame; GSR và IMU đủ 45, khoảng nhận lớn nhất 1,078 giây. HR chỉ có **5/45 frame, 42,9–43,3 bpm**. Không nghiệm thu khả năng có kết quả hoặc độ đúng.

Raw: `backend/storage/local/ppg-20261107-175506-164954.csv/.json`. WS: `ppg-tracker-wrist-20261107-175506-567eb4.json`. Worker tự kiểm đạt, hoàn thành 35/35 yêu cầu, nhận 5 kết quả, không ghi đè hàng đợi; thời gian xử lý lớn nhất 95.053 µs, stack còn 2.948 byte. Không dùng các số này để kết luận đã xử lý vấn đề nhiệt.

Replay cùng raw mới: core cũ nhận 20/34 cửa sổ, 41,0–42,6; ứng viên nhận 7/34, 41,0–42,3. Cả hai đều bám dao động chậm. Không chọn bản chỉ vì khớp một lượt raw cũ đẹp hơn. Raw không bị chỉnh hoặc thay bằng mô phỏng.

## Kiểm thêm bộ lọc, không nạp các cách không đạt

Biểu đồ raw có bước nhảy nền rất lớn quanh giây 33. Điều này gợi ý kiểm tra ảnh hưởng nền và quá độ bộ lọc; chưa chứng minh nguyên nhân vật lý là ánh sáng, lực chạm hay chuyển động. Không kết luận chỉ do Wi-Fi hoặc cảm biến hỏng.

Đã thử tách thêm nền bậc hai/bậc ba trực giao trong cửa sổ. Bộ này qua 47 ca core, gồm 40/80/150 bpm dưới nền cong và nền không có mạch; nhưng trên raw mới vẫn nhận 20/34, khoảng 41,0–42,3. Không giữ nó chỉ vì qua mô phỏng. Báo cáo `ppg-curved-baseline-development.json`; mã nguồn khóa trong `hr-curved-baseline-sources-20261107/`, ghi rõ chưa nạp.

Thử offline hạn chế đạo hàm đột biến bằng trung vị/MAD của 100 mẫu trước, chỉ tạo bản sao dữ liệu dẫn xuất. Ở raw mới có 44 lần hạn chế RED và 49 lần IR; tracker vẫn nhận 18/34, khoảng 41,0–42,7. Hai trace đối chứng không thay đổi mẫu. Cách này cũng không giải quyết được lỗi nên không đưa vào firmware. Chi tiết và hash input gốc/dẫn xuất ở `ppg-derivative-guard-prototype.json`.

Sau các phép thử, đã bỏ thay đổi giảm điểm sườn và nền cong khỏi core chạy, trả về đúng hash core 0.3.20 đã lưu trước đó. Bốn test thêm ở vòng đầu vẫn đạt với core cũ, tổng 43 ca; không gọi chúng là bằng chứng bản cũ đã sửa HR cổ tay. Các thử nghiệm bị loại nằm trong storage local đã được Git bỏ qua, không để các nhánh xử lý không dùng trong firmware.

**Mục tiêu HR ổn định, gần đúng vẫn chưa đạt.** Các đỉnh phổ có thể thuộc mạch, hài hoặc nhiễu; không tự chọn đỉnh gần 80 chỉ vì đó là con số mong muốn. Dự báo FE có nhãn vẫn chỉ là lớp trình bày, không dùng để tuyên bố HR đã được khôi phục. Không lặp thêm lượt giữ tay hoặc đổi LED trong vòng này khi chưa có giả thuyết mới phân biệt được trên dữ liệu.

## Trạng thái bàn giao tại mạng nhà

Đã nạp lại 0.3.20 với `network_config.h` Trung vừa sửa; không đổi SSID/mật khẩu hoặc đưa chúng vào log/Git. Broker đã bind IP LAN nhà hiện tại, broker/backend healthy. Chạy lại `npm run dev`, Dashboard ở `http://localhost:5173`; kiểm bridge cookie và nhận 5 frame DEVICE đúng firmware qua WebSocket. Self-test worker đạt, wifi/mqtt/sync đều 1. Đây là kiểm đường truyền sau đổi mạng, chưa phải một lượt nghiệm thu HR cổ tay mới.

Core khôi phục qua 43 ca, 8 ca tích hợp driver, 4 tổ hợp header; build và upload thành công. Hai schema đang có thay đổi riêng của Trung được giữ đúng hash ban đầu. Header local và toàn bộ raw/báo cáo cá nhân vẫn được Git bỏ qua. Chưa commit/push/merge. Cần mốc đối chiếu nhịp đồng thời, kể cả đếm tay thô, để phân biệt mạch và hài trước khi chốt thuật toán tiếp; chưa có câu trả lời hoặc số đếm tại checkpoint này.
