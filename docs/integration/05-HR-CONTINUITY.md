# HR liền mạch ở khoảng mất ngắn

**Mới nhất 2026-11-08:** 0.3.23 sửa trộn median/EMA cũ sau khi đã xác nhận đổi chu kỳ. Lượt cổ tay cuối đủ 45 frame; sau 4 frame đầu chưa có HR, 41 frame còn lại liên tiếp 68,8–76,6 bpm. FE không dùng dự báo trong lượt này, không lỗi kết nối mới. Chưa xác nhận độ đúng bằng tham chiếu đồng thời. [Bàn giao và giới hạn](05-HR-TRACK-SWITCH.md). Các checkpoint bên dưới là lịch sử.

**Cập nhật sau lượt nhận nhầm:** đã thử 0.3.21, đo cổ tay chỉ có 5/45 frame HR quanh 43 bpm; không đạt. Các thay đổi thử nghiệm đã bỏ, khôi phục core 0.3.20 và kiểm 43 ca. Wi-Fi nhà được giữ theo cấu hình local mới. [Chi tiết kiểm nguyên nhân và các cách lọc đã loại](05-HR-HARMONIC-REJECTION.md). Kết quả liền mạch ở các lượt dưới không có nghĩa HR đã chính xác.

Ngày 2026-11-07. Trung thấy HR đôi khi mất rồi có lại, có lúc tụt về40bpm và yêu cầu tiếp tục cải thiện. Đây là vòng mới được yêu cầu sau [tracker0.3.18](05-HR-CYCLE-TRACKER.md), không gọi mọi số40 là lỗi hoặc ép HR về60–100.

**Bản đang nạp: 0.3.20-tracker.** Lượt cuối đủ 45 gói; 28 gói có HR từ ESP và 8 gói được FE ghi “Tạm tính”. Sau gói có HR đầu tiên, lớp hiển thị không bị trống trong lượt thu. HR vẫn có đoạn thấp 43,7–52 rồi lên khoảng75–77bpm, nên chưa xác nhận đã hết nhận nhầm nửa nhịp hoặc HR đúng. Chi tiết, giới hạn và cách chạy ở cuối file.

## Thay đổi đã triển khai

**Firmware0.3.19-tracker:** giữ các giả thuyết qua tối đa14 cửa sổ yếu, thay vì reset toàn bộ sau3 cửa sổ. Không phát HR mới chỉ từ giả thuyết cũ. Mất tiếp xúc/flat/dữ liệu lỗi/generation/gap vẫn reset.

Nếu ứng viên mới lệch quá `max(12bpm,18%)` so với nhịp vừa được chấp nhận trong15giây gần nhất, cần3 cửa sổ ứng viên mới nhất quán; nếu gần nửa/gấp đôi nhịp thì cần6 cửa sổ. Khi có bằng chứng bền, HR40 thật vẫn được nhận. Không sửa mọi40 thành80. Median3/EMA0,30 giữ trạng thái qua mất ngắn tối đa15giây, chỉ cập nhật khi có ước tính mới được nhận; log vẫn tách candidate trước làm mượt.

**FE:** tracker thiếu HR sẽ dùng dự báo ngắn tối đa15giây tính từ **gói có HR cuối**, không gia hạn từ một số dự báo trước. Khi có đủ3 điểm gần nhất cùng xu hướng, dùng xu hướng tắt dần với tổng dịch chuyển tối đa3bpm; nếu chưa đủ lịch sử thì dự báo hằng. Thẻ ghi rõ **Tạm tính · … giây chưa có HR mới**. Sau15giây, mất kết nối, đổi phiên/thiết bị hoặc clock lùi thì không tiếp tục dự báo.

Biểu đồ giữ `hr=null` ở dữ liệu gốc, thêm series trình bày `hrForecast` bằng nét đứt và tooltip **Tạm tính**. Nét liền vẫn là dữ liệu thiết bị. Không ghi số dự báo vào backend/DB, không dùng nó làm nhãn train hoặc nguồn DEVICE mới. Bản demo0.3.16 vẫn giữ chính sách hiển thị cũ tối đa10giây, bản đối chứng không tự bật dự báo.

Phần dự báo giúp đường biểu diễn liên tục qua **khoảng ngắn**; không làm hồi phục thông tin mạch đã mất. Không thể hứa luôn có số khi chưa thu được HR ban đầu hoặc tín hiệu mất lâu. Dự báo có thể sai, kể cả khi đường nhìn mượt. Không có HR tham chiếu đồng bộ tại cổ tay nên không gán độ chính xác cho vòng này.

## Kiểm tra và giới hạn

37 ca core C++ đạt, gồm cú nhảy nửa nhịp không được nhận ngay và HR40 thật bền vẫn được nhận, nhịp80→120, reset/gap/phiên. FE thêm ca hạn15giây, không gia hạn từ dự báo, clock lùi, history rỗng và nguyên vẹn `hr`/telemetry. Các kết quả replay/build/nạp/đo thật cập nhật bên dưới sau khi chạy.

Một điểm đánh đổi cần giữ: xác nhận nhịp thay đổi lớn làm tăng độ trễ vài giây; HR thật thay đổi nhanh không được bảo đảm theo kịp tức thời. Không dùng việc loại được số40 để tự tuyên bố thuật toán đúng hơn.

Replay/build đã hoàn tất, sau đó nạp0.3.19-tracker trên COM7 (hash verified). Kiểm trước đặt tay nhận5gói DEVICE đúng phiên bản, GSR/IMU đủ và cùng phiên tự động. 64testFE/build,37coretracker,8tích hợp tracker,10selector,6capture và4tổ hợp header đạt; chưa chạy CI GitHub từ xa.

Hồi quy dùng lại các seed và BIDMC16–20 đã xem ở vòng trước, không phải test mới: mô phỏng có nhịp nhận4.421/4.704 cửa sổ, MAE1,00bpm/53 lỗi>10; BIDMC16–20 nhận2.239/2.330, MAE1,55bpm/56 lỗi>10. Nhiễu không có mạch vẫn nhận279/931. Không lấy các số này làm sai số trên cổ tay Trung hoặc bằng chứng mọi ứng viên là mạch thật.

Báo cáo `ppg-continuity-final-development.json`, `ppg-continuity-regression.json` giữ source/input hashes. Runner dùng tên phase `validation` để chọn input, nhưng metadata báo cáo hồi quy được chú thích rõ sau chạy rằng dữ liệu/seed đã xem, không thay dự đoán hoặc hash nguồn. Nguồn khóa ở `backend/storage/local/hr-continuity-final-sources-20261107/`.

Build/nạp xong mới yêu cầu Trung chuẩn bị một lượt cổ tay45giây; chưa chấm lượt thật ở checkpoint này. Không thay LED/tần số hay thuật toán GSR/IMU.

## Lượt 0.3.19 và lỗi xác nhận lúc bắt đầu

Đã thu đủ45giây sau xác nhận của Trung và báo thả tay ngay. Raw `ppg-20261107-172548-154e3f.csv/.json`:2.252mẫu, complete, interval tối đa20ms, không dropped/timestamp lùi/lỗi capture. WS `ppg-tracker-wrist-20261107-172548-e429fb.json`:45gói,11gói có HR,40–82,4bpm, một phiên; mạng vẫn đồng bộ. **Số40 còn xuất hiện**, không ghi đã xử lý xong.

Rà code sau lượt này tìm thấy hai điểm startup chưa được kiểm đúng: (1) hai cửa sổ qua cổng quality được đếm liên tiếp dù chọn hai chu kỳ rất khác; (2) prior từ cửa sổ đầu có thể giữ giả thuyết nửa nhịp trong khi bằng chứng mới rõ hơn nghiêng về chu kỳ khác. Không thể dùng việc “đủ hai cửa sổ” để tự gọi đã xác nhận cùng một nhịp.

**0.3.20-tracker** sửa đúng hai điểm: khi chưa có anchor, hai ứng viên phải nhất quán trong `max(8bpm,15%)`; nếu bằng chứng mới ở chu kỳ khác mạnh hơn trên0,10 điểm thì chưa xác nhận prior đang bám. Không tự thay prior bằng số80 hoặc cấm40. Hai test mới đưa80→40 và40→80 lúc startup; bản trước không qua, bản sửa qua cả hai. Tổng39coretest đạt, nhịp40 sạch/bền và biên35/205 vẫn được kiểm như trước.

Đây là sửa logic xác nhận startup, không quét lại ngưỡng để chọn một nhịp mong muốn. Giữ nguyên FE dự báo15giây; chưa gọi HR giả định là số đo. Chạy lại benchmark/build trước nạp0.3.20; chưa có lượt vật lý mới ở thời điểm ghi mục này.

Đã build/nạp0.3.20, hash verified và nhận5frame DEVICE trước yêu cầu đặt tay. 39coretest đạt; FE64test/build vẫn là bản đã kiểm, không thay giao diện sau vòng test. Tài liệu/source rollback0.3.19 giữ ở `hr-continuity-final-sources-20261107/`, nguồn0.3.20 khóa ở `hr-continuity-startup-sources-20261107/` trong thư mục local ignored.

Phát lại đúng45frame0.3.19 qua utility FE thực tế cho36frame có số trên thẻ:11frame từ thiết bị,25frame tạm tính, không còn frame trống sau frame có HR đầu tiên. Đây là replay của lớp hiển thị, **không phải browser screenshot hoặc36HR mới**. Script tái hiện `backend/storage/local/hr-continuity-final-sources-20261107/evaluate_frontend.mjs` kiểm cả việc không sửa frame gốc. Kết quả `ppg-tracker-wrist-20261107-172548-e429fb-frontend.json`.

## Bàn giao sau lượt cuối 0.3.20

Trung xác nhận áp nhẹ ở cùng vùng cổ tay, laptop gần; đã thu đủ 45 giây và báo thả tay ngay trước phân tích. Không yêu cầu đo tiếp trong vòng này.

| Mục | Kết quả |
|---|---|
| Raw | `ppg-20261107-173216-f421a1.csv/.json`: 2.252 mẫu, đủ45,0giây, complete, interval tối đa20ms, không dropped/timestamp lùi/lỗi capture hoặc cleanup |
| WebSocket | `ppg-tracker-wrist-20261107-173216-606796.json`:45gói DEVICE, đúng0.3.20-tracker, một phiên tự động |
| HR nguồn thiết bị | 28/45gói, khoảng43,7–76,7bpm; không có tham chiếu đồng bộ |
| FE tạm tính | 8/45gói, ghi nhãn và nét đứt; không biến thành HR đo mới |
| Độ liền của thẻ | Có số ở36/45gói;9gói đầu chưa có HR. Từ gói HR đầu tiên đến cuối lượt không có gói trống ở lớp hiển thị |
| GSR/IMU | Đủ45/45 choGSR và cảhai vectorIMU |
| Mạng | Khoảng nhận lớn nhất1,047giây; wifi/mqtt/sync luôn1 trong log; fail/drop/error0; invalid1 có trước không tăng |
| Worker |39request/completed,28accepted, không queue overwrite; max wall78.101µs, stack còn2.916byte; workspace ESP17.184byte |
| Lấy mẫu/bộ nhớ | Không tăng I2C/overflow/gap/clip/ALC; loopGap tối đa12ms; heapMin149.564byte trong log. Không suy nhiệt độ từ heap |

**Đã cải thiện phần hiển thị liền mạch qua khoảng thiếu ngắn, chưa giải quyết hoàn toàn số thấp/nhận nhầm nửa nhịp.** Lượt này không có số đúng40 nhưng vẫn có43,7–52; không lấy đó làm chứng minh lỗi đã hết. Không ép số về60–100 hoặc tự đổi43 thành86. Một số HR có thể đã làm mượt từ giả thuyết sai, và dự báo FE cũng có thể nối tiếp một giá trị sai.

Các phép so trên lượt0.3.18/0.3.19/0.3.20 là các lượt khác nhau; không quy mọi khác biệt cho một dòng code. Replay C++ trên cùng raw giúp kiểm logic, nhưng không có HR tham chiếu tại cổ tay nên không chấm sai số thật.

Kiểm bằng utility FE **thực tế**: `heartRateDisplay` và `heartRatePlot` chạy trên45frame đã thu, xác nhận frame gốc không bị sửa. Dự báo chỉ tồn tại trong series trình bày `hrForecast`; `hr_bpm` và `hr` vẫn giữ null ở các gói thiếu. Sau15giây không có HR mới, phần tạm tính dừng; mất kết nối không tiếp tục tạo giá trị mới. Không vẽ trước khi có HR đầu tiên.

[Hình gói DEVICE và phần tạm tính](../../backend/storage/local/ppg-continuity-hardware-comparison.png) đã được xem lại bố cục, chú thích và khoảng trống. [Bàn giao máy đọc được](../../backend/storage/local/ppg-continuity-final-handoff.json) giữ hash nguồn/input/binary và thống kê. Kết quả utility FE của lượt cuối: `ppg-tracker-wrist-20261107-173216-606796-frontend.json`. Đây không phải ảnh chụp Dashboard bằng trình duyệt; browser runtime hiện không có phiên khả dụng, không báo screenshot PASS.

### File chính

- `ppg_cycle_tracker.h`: xác nhận cú nhảy, giữ giả thuyết qua mất ngắn, xác nhận cùng chu kỳ lúc khởi tạo; vẫn nhận nhịp40 thật khi có bằng chứng bền.
- `heartRateDisplay.ts`: dự báo có hạn15giây và series tách biệt, không sửa telemetry/DB.
- `HeartRateChart.tsx`, `MetricChart.tsx`, `Dashboard.tsx`: nhãn “Tạm tính”, đường nét đứt và tooltip riêng; giữ bố cục đang dùng.
- `ppg_tracker_test.cpp`:39ca gồm startup80↔40, không chặn40 thật, gap/reset/phiên và nhịp thay đổi.
- `live-telemetry.test.mjs`:64testFE đạt, gồm hạn dự báo, clock lùi, mất kết nối, không gia hạn từ dự báo và không sửa frame gốc. Frontend build đạt, còn cảnh báo kích thước bundle đã có.

39core,64FE,8tích hợp tracker,10selector,6capture và4tổ hợp header đã đạt. Firmware build/nạp thành công, hash verified. Chưa chạy GitHub CI từ xa, chưa commit/push/merge. Schema của Trung, thuật toán GSR/IMU và credential không thay đổi trong vòng này.

Hồi quy bản0.3.20 dùng lại seed/BIDMC đã xem: mô phỏng có nhịp4.420/4.704 cửa sổ, MAE1,00bpm/53lỗi>10; BIDMC16–20 có2.239/2.330, MAE1,55bpm/56lỗi>10. Nhiễu không mạch vẫn bị nhận276/931; chưa đủ tin cậy để dùng HR này làm nhãn chuẩn cho huấn luyện AI. Đây không phải dữ liệu kiểm độc lập hoặc sai số cổ tay Trung.

### Dùng tiếp

ESP đã nạp; không cần upload mỗi ngày. Kết nối đúng Wi-Fi/hotspot đã cấu hình, mở Docker Desktop và chạy:

```powershell
npm run dev
```

Lúc đầu cần thời gian tìm nhịp. Khi đang “Tạm tính”, số và nét đứt là dự báo ngắn; khi trở lại nét liền/số đo tương đối thì có HR từ thiết bị. Nếu không có HR quá15giây thì sẽ để trống để báo tín hiệu chưa đủ, không tạo số vô hạn.

Sau khi đổi Wi-Fi/host trong header local, nạp lại đúng profile để giữ bản mới:

```powershell
.\.venv\Scripts\python.exe -m platformio run -d ai/edge_firmware -e esp32s3_hr_tracker -t upload --upload-port COM7
```

**Vòng cải thiện liền mạch đã triển khai và kiểm trên phần cứng xong.** Đã đạt việc nối khoảng thiếu ngắn trong lượt kiểm cuối; chưa đạt luôn có HR mới hoặc xác nhận mọi số thấp là sai/đúng. Không mở thêm vòng đo hoặc hứa độ chính xác từ đường vẽ đẹp. Sự kiện nóng cũ cũng chưa có số đo để xác nhận nguyên nhân đã được xử lý.

Bản sao nguồn trước đổi nằm tại `backend/storage/local/hr-continuity-before-20261107/`; credential không nằm trong bản sao. Mọi raw/replay cá nhân giữ ngoài Git. Chưa thay GSR/IMU/schema hoặc mở raw recording.
