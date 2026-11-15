# Kiểm tra mất dữ liệu khi đo HR

**Cập nhật:** lượt cổ tay 0.3.22 sau kiểm trên bàn đã nhận đủ 45/45 frame, khoảng nhận tối đa 1,063 giây; RSSI -65 đến -62 dBm, không lỗi mạng mới. HR vẫn thấp và thiếu. Sau phân tích đã tìm lỗi trộn smoother khi đổi chu kỳ, nạp 0.3.23; [chi tiết sửa và kiểm thử](05-HR-TRACK-SWITCH.md). Chưa coi sự cố mạng gián đoạn trước đó đã được khắc phục hoàn toàn.

Cập nhật 2026-11-08. HR cổ tay chưa đạt yêu cầu ổn định và gần đúng. Vòng này kiểm tra đường truyền trước khi đổi tiếp bộ tính HR.

## Lượt dùng dây USB mới

Sau khi Trung thay dây, kiểm trên bàn 20 giây nhận 20 frame DEVICE; khoảng nhận lớn nhất 2,641 giây. Không phát sinh lỗi I2C hoặc kết nối ở khoảng kiểm này. Đây chưa phải bằng chứng dây mới đã khắc phục mọi gián đoạn; ESP đã reboot nên counter cũng bắt đầu lại.

Sau xác nhận sẵn sàng, thu cổ tay 60 giây, không đè cụm mạch:

- Raw `ppg-20261108-004647-291ca1.csv/.json`: đủ 3.003 mẫu, interval tối đa 20 ms, không dropped, timestamp lùi hoặc lỗi capture; I2C/FIFO không báo lỗi trong lượt.
- WS `ppg-manual-pair-20261108-004748-a5e45a.json`: chỉ 13 frame, frame đầu đến sau 43,407 giây; 2 frame có HR 40,2–40,3 bpm. Không coi khoảng không nhận được dữ liệu là nhịp tim bằng 0.
- Log ESP vẫn `wifi=1`, nhưng MQTT chuyển sang 0, mất đồng bộ và có lỗi transport 32774. USB mới vẫn thu liên tục; chưa có bằng chứng quy sự cố lần này cho đứt nguồn hoặc rớt cổng USB. Chưa xác định nguyên nhân lỗi TCP.
- Trung xác nhận nghe bíp nhưng chưa đếm được mạch. Giữ tham chiếu lượt này là **chưa có**, không ghi 0 nhịp và không gán số 75 đã đếm riêng trước đó.

## Bản chẩn đoán 0.3.22-tracker

Giữ nguyên core HR 0.3.20, cổng chuyển động, LED, tần số, GSR/IMU và schema. Chỉ bổ sung chẩn đoán vào Serial:

```text
[NET-LINK] rssiDbm=... reconnects=... errorAtMs=... mqttErrorType=... tlsStackError=... socketError=...
```

- `rssiDbm`: RSSI Wi-Fi, đọc ở worker mạng theo nhịp metrics 5 giây; -127 là chưa có Wi-Fi, không phải phép đo tín hiệu ở trạng thái đó.
- `reconnects`: số lần MQTT đã đi qua CONNECT và SUBACK trong boot hiện tại.
- Các trường lỗi mô tả **lỗi gần nhất**, giữ qua reconnect. `errorAtMs` là mốc lỗi theo `millis()` của boot, không phải thời gian UTC; 0 lúc chưa ghi lỗi. Không dùng việc mã lỗi còn hiện để nói kết nối hiện vẫn lỗi.
- Với loại lỗi TCP, lưu thêm lỗi stack và socket errno từ error handle của SDK đang cài. Không dùng mã 32774 đơn lẻ để tự kết luận yếu Wi-Fi, lỗi tường lửa hoặc broker.

Không đọc RSSI hoặc chờ mạng trong vòng sensing; không đổi timeout/backoff/công suất Wi-Fi trong cùng phép thử. Bộ thu raw đã lưu thêm dòng `[NET-LINK]`. Không ghi SSID, mật khẩu, token hoặc payload điều khiển vào log chẩn đoán này.

43 ca core HR và 6 ca bộ thu raw đạt. Build/nạp và kiểm trên máy thật được cập nhật sau khi chạy. Chưa gọi bản chẩn đoán này là bản sửa HR hoặc đã xử lý xong gián đoạn mạng. Không cần Trung giữ tay hoặc tiếp tục đếm ở bước kiểm trên bàn.

## Kiểm sau nạp 0.3.22

Đã build/nạp thành công và xác nhận hash khi upload. Core HR đúng hash 0.3.20; 43 ca core, 6 ca bộ thu raw và 4 tổ hợp header đạt. Nguồn/binary khóa ở `backend/storage/local/hr-link-diagnostics-sources-20261108/`. Hai schema có thay đổi riêng của Trung được giữ đúng hash trước vòng này.

Kiểm kết nối 20 giây sau nạp: 20 frame, khoảng nhận tối đa 1,031 giây, RSSI khoảng -59 dBm, chưa có lỗi transport mới. Sau đó bật xuất raw USB 60 giây khi không yêu cầu tiếp xúc da: 3.001 mẫu raw và 59 frame DEVICE, không lỗi capture. Đây là ca kiểm thêm có chủ đích để phân biệt tải xuất Serial với điều kiện khi đo cổ tay, không phải một lượt đo HR và không có tham chiếu.

Raw `ppg-20261108-005740-53acc8.csv/.json`, WS `ppg-link-raw-check-20261108-005740-e0762f.json`; số liệu mạng/RSSI tổng hợp trong `ppg-link-raw-bench-analysis-20261108.json`. Dòng `[NET-LINK]` đã có trong bản thu thật. Kết quả một lượt chưa loại trừ tác động CPU/radio khi có tiếp xúc da và worker HR bắt đầu chạy.

Bước tiếp: một lượt cổ tay ngắn với cùng firmware/log để so RSSI và lỗi socket; **không cần đếm mạch**. Chỉ bắt đầu khi Trung báo sẵn sàng, không yêu cầu đè cụm mạch. Chưa thay thuật toán, không mở thêm vòng chỉnh ngưỡng theo số 75.
