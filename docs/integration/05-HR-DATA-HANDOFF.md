# Bàn giao đợt thu dữ liệu HR cổ tay

Chốt ngày 2026-11-07, cập nhật sau B2 đo lại lúc 15:22. **Đã đủ bốn lượt hoàn chỉnh A1, B1, A2 và B2 đo lại, mỗi lượt 45 giây.** B2 gián đoạn trước đó được lưu riêng, không tính vào bộ bốn lượt đầy đủ. Bước thu theo số lượt yêu cầu đã hoàn tất; dữ liệu dùng phát triển/chẩn đoán thuật toán, chưa đủ xác nhận sai số HR thật tại cổ tay.

## Điều kiện giữ nguyên

**Cập nhật sau thu:** đã hoàn tất [vòng hai ứng viên offline](05-HR-WEAK-SIGNAL-EXPERIMENT.md). Chưa chọn bản để nạp: B còn sai nửa nhịp trên mô phỏng mới và chưa khôi phục HR cổ tay ổn định. Firmware/GSR/IMU giữ nguyên; chưa yêu cầu thu thêm.

Trung lật đế tròn để ô kính MAX30102 hướng vào da tại vị trí cổ tay dự định đeo. Toàn bộ mạch xanh nằm trong phạm vi cổ tay, ESP32 và MPU nhô ra ngoài một phần. Chỉ đặt nhẹ, không dùng tay đè cụm mạch; không yêu cầu siết dây chặt.

Firmware đối chứng `0.3.13-led10`: LED danh định 10 mA, chip 200 Hz/gộp 4, FIFO danh định 50 Hz. Không đổi thuật toán HR, GSR hoặc IMU trong chuỗi này. Trước A2 đã Clean/build và nạp lại cùng cấu hình; A2 thuộc boot/phiên mới. Không gọi đây là thí nghiệm liên tục cùng một boot.

B2 đo lại được thực hiện sau A2, theo yêu cầu bổ sung của Trung. Trước lượt này đã bật lại hotspot và reset ESP một lần để nối lại mạng, không nạp firmware khác. Vì vậy thứ tự thực tế là A1 → B1 → B2 gián đoạn → A2 → B2 đo lại; không trình bày như chuỗi ABBA liên tục không gián đoạn.

Luồng thật đã kiểm: ESP → hotspot laptop chia sẻ Wi-Fi quán → MQTT → backend → WebSocket. USB dùng raw/log, không thay đường dữ liệu DEVICE. Không dùng data iPhone.

## Danh mục lượt thu

| Lượt | Điều kiện | Raw | WebSocket | HR được bản đang chạy chấp nhận |
|---|---|---:|---|---|
| A1, 14:37 | Không che thêm | 2.252 mẫu, đủ 45 giây | 40 frame, một phiên; GSR/IMU đủ | 0/40 |
| B1, 14:41 | Che sáng phía ngoài | 2.252 mẫu, đủ 45 giây | 40 frame, một phiên; GSR/IMU đủ | 0/40 |
| B2, 14:46 | Lặp che sáng | **1.673 mẫu, đoạn dài 33,413 giây; gián đoạn** | 29 frame phiên cũ + 2 frame phiên mới; hai frame sau boot chưa có hai vector IMU | 0/31, không gộp thành một phiên ổn định |
| A2, 15:08 | Bỏ che, sau Clean/build/nạp lại | 2.252 mẫu, đủ 45 giây | 40 frame, một phiên; GSR/IMU đủ | 0/40 |
| B2 đo lại, 15:22 | Che sáng như B1, sau A2 | **2.252 mẫu, đủ 45 giây** | 40 frame, một phiên; GSR/IMU đủ | 0/40 |

**Bộ bốn lượt đầy đủ: 9.008 mẫu raw, 160 frame WebSocket.** Giữ thêm 1.673 mẫu của B2 gián đoạn, tổng lưu trữ là 10.681 mẫu. Số mẫu không chứng minh chip chạy chính xác tuyệt đối 50 Hz. Cả bốn lượt hoàn chỉnh không báo lỗi I2C/FIFO/gap trong log và không rơi trace; A1 có một khoảng timestamp 40 ms, không giấu bằng cách resample hoặc sửa thời gian. B2 gián đoạn không có JSON chẩn đoán gốc vì công cụ cũ bị lỗi lúc USB ngắt; các bộ đếm chưa lưu phải coi là chưa biết.

### Các file local

Mọi file dưới đây ở `backend/storage/local/`, đã được Git bỏ qua. Giữ dữ liệu đo cá nhân và credential ngoài Git.

| Lượt | Raw CSV và sidecar | WebSocket |
|---|---|---|
| A1 | `ppg-20261107-143727-69bc62.csv/.json` | `hr-A1-20261107-143727-df30b0-ws.json` |
| B1 | `ppg-20261107-144120-c09b18.csv/.json` | `hr-B1-20261107-144121-d2388d-ws.json` |
| B2 | `ppg-20261107-144615-79ab14.csv`; **không có sidecar gốc** | `hr-B2-20261107-144616-e7f085-ws.json` |
| A2 | `ppg-20261107-150835-f55320.csv/.json` | `hr-A2-20261107-150835-8bec03-ws.json` |
| B2 đo lại | `ppg-20261107-152207-29b374.csv/.json` | `hr-B2-repeat-20261107-152207-3b2a88-ws.json` |

Sự kiện B2 được ghi riêng trong `hr-B2-20261107-interrupted.json`, không dựng lại metadata như thể nó đã được công cụ ghi tại thời điểm đo. Manifest đầu vào/hashes: `hr-optical-manifest-20261107.json`.

CSV có `t_ms`, `red`, `ir`: thời gian mẫu ước lượng theo đồng hồ monotonic thiết bị và ADC quang dạng counts, không phải HR. Timestamp telemetry trong phiên có thể theo epoch phiên; không tự ghép hai loại timestamp chỉ vì cùng đơn vị ms. Cửa sổ và clock của replay phải được ghi rõ.

## Kết quả phân tích sau đợt thu

Đã replay bằng bộ lọc C++ thực tế và các ứng viên có sẵn, lưu hashes source. Với bốn trace hoàn chỉnh, dùng cùng các cửa sổ kết thúc ở giây 13–44: **32 cửa sổ mỗi trace**. Các cửa sổ chồng nhau, không phải 128 thí nghiệm độc lập. Phân tích cũ dùng khoảng 13–30 để gồm B2 gián đoạn vẫn được giữ trong `hr-optical-series-20261107.json`, nhưng không thay bộ so sánh đầy đủ mới.

- Baseline và hybrid strict đều 0/32 trên cả bốn trace.
- Hybrid balanced cũ: A1 0/32, A2 0/32, B1 4/32, B2 đo lại 3/32. Các ứng viên B1 khoảng 75,2–82,6 bpm, B2 đo lại 72,1–73,4 bpm; chưa có tham chiếu để chấm đúng/sai và chúng không được firmware gửi lên FE.
- Hai lượt che có thêm một số ứng viên offline so với hai lượt không che: đây là dấu hiệu mô tả đáng giữ khi thiết kế bộ lọc, **chưa xác nhận ánh sáng là nguyên nhân hoặc các ứng viên đó là nhịp thật**. Không đổi sang balanced chỉ để có số; cấu hình này từng nhận nhầm nhiễu trong benchmark cũ.
- Qua 128 cửa sổ IR chồng nhau của bốn trace đầy đủ: 36 bị loại sớm vì khoảng đỉnh ngoài dải, 39 vì 8s/4s bất đồng, 16 không đủ đỉnh, 3 đỉnh quá cũ; còn 34 tính được đủ đặc trưng trước cổng quality. Đây là lý do loại đầu tiên của nhánh quality, không phải mọi lý do loại baseline.
- Raw còn trôi nền và xung; sau bộ lọc vẫn có dao động không đều. Chỉ nới template/độ đều ở tầng cuối chưa xử lý được phần lớn cửa sổ bị loại trước đó.
- **Chưa đủ bằng chứng quy nguyên nhân chính cho ánh sáng**, cũng chưa chứng minh ánh sáng không ảnh hưởng. Tiếp xúc/lực chạm, nhiệt và độ rọi không được đo độc lập; các lượt nằm ở nhiều boot, B2 đo lại sau A2. Không kết luận chỉ do phần cứng hoặc chỉ do thuật toán.

Biểu đồ [bốn lượt đầy đủ, cùng đoạn giây 22–30](../../backend/storage/local/hr-optical-complete-20261107.png) đã được kiểm tra hiển thị; báo cáo [replay và source/input hashes](../../backend/storage/local/hr-optical-complete-20261107.json). Phổ tính theo FIFO danh định 50 Hz; đỉnh phổ không phải HR tham chiếu. Trục biên độ của các hàng có thang riêng, không so độ cao pixel như cùng đơn vị hiển thị.

## Giới hạn và việc tiếp theo

- Không có HR tham chiếu đồng bộ. Không tính MAE, độ chính xác hoặc gán các đoạn này là nhịp đúng. HR null không phải nhịp 0; không điền thành 0 để train hoặc đánh giá.
- Toàn bộ chuỗi này là dữ liệu phát triển đã xem, không gọi lại là test độc lập khi chỉnh thuật toán.
- Trung báo chip nóng và rút USB ở B2 đầu. Trước A2 và B2 đo lại, Trung xác nhận không nóng bất thường và sẵn sàng; cả hai lượt hoàn tất không lỗi capture. Không có nhiệt độ đo, nên Clean/build hoặc việc thu đủ không xác nhận đã xử lý nguyên nhân nóng. Sau thu đã hướng dẫn rút USB trong lúc phân tích. [Hồ sơ nhiệt](05-THERMAL-CHECK.md).
- Công cụ thu đã sửa lỗi mất sidecar khi USB ngắt; 6 test giả lập đạt. A2 và B2 đo lại dùng bản sửa, ghi `capture_status=complete`, đủ 45 giây, không lỗi thu hoặc dọn cổng. Không đổi firmware để sửa công cụ trên laptop.

**Bước tiếp theo chỉ làm offline:** xử lý nền/xung nhưng bảo toàn sóng yếu; xem lại cách tìm đỉnh, loại ngoại lệ RR và đối chiếu cửa sổ ngắn; chấm chất lượng bằng chứng mềm thay vì bắt mọi khoảng nhịp/hình dạng đều đẹp. So với baseline trên dữ liệu tham chiếu và mô phỏng có HR gốc, báo cả nhận nhầm nhiễu. Chỉ chọn ứng viên khi có bằng chứng sai số/khả năng có kết quả; không làm mượt số sai hoặc điền HR cũ.

Phần phân tích tiếp nêu trên đã được thực hiện với đủ hai ứng viên; xem [kết quả vòng offline](05-HR-WEAK-SIGNAL-EXPERIMENT.md). Chưa chọn bản đạt để nạp, chưa mở thêm vòng đo người, chưa đánh DONE HR hoặc nhánh 5 từ việc chốt dữ liệu này.
