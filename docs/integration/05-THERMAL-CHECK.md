# Tạm dừng đo vì chip ESP32-S3 nóng

**Checkpoint cập nhật:** sau khi Trung yêu cầu tiếp tục và xác nhận không nóng bất thường, A2 và B2 đo lại đều thu đủ 45 giây trên cùng cấu hình HR/điện năng, sau Clean/build/upload. Đã đủ bốn lượt thu hoàn chỉnh, B2 gián đoạn vẫn giữ riêng; đã hướng dẫn rút USB trong lúc phân tích. Không có số đo nhiệt, không coi thu thành công là xác nhận đã khắc phục nguyên nhân nóng. [Bàn giao dữ liệu](05-HR-DATA-HANDOFF.md). Các mục dưới giữ hồ sơ sự kiện và kiểm tra phần mềm.

Cập nhật 2026-11-07. Trung báo chip ESP32-S3 trên mạch đen nóng và đã rút USB; không thấy mùi khét, khói hoặc linh kiện biến dạng. **Giữ thiết bị ngắt nguồn, không đeo hoặc cấp nguồn lại để thu A2 ở bước này.** Chưa đo nhiệt độ, dòng hoặc điện áp nên chưa xác định mức nhiệt và nguyên nhân điện/nhiệt.

## Bằng chứng và điều chỉnh kết luận B2

- B2 dự kiến 45 giây, nhưng raw chỉ còn 1.673 mẫu, trải 33,413 giây: `ppg-20261107-144615-79ab14.csv`.
- Script cũ lỗi đọc USB (`ClearCommError`), rồi lỗi gửi `q` che lên lỗi ban đầu. CSV đã đóng/lưu, nhưng JSON chứa chẩn đoán chưa được ghi.
- WebSocket nhận 31 frame, gồm 29 frame ở phiên cũ và 2 frame ở phiên mới, đều chưa có HR. Không gộp các timestamp ở hai phiên thành một lượt liên tục.
- Thông tin người dùng rút USB vì nóng giải thích việc đường thu bị ngắt. Mã phiên mới chứng minh đã có boot khác, **không chứng minh ESP tự crash, watchdog hoặc brownout do code**. Không suy ra nguyên nhân của boot chỉ từ mất USB hoặc timestamp quay về nhỏ.
- Đây là lượt bị gián đoạn; không gọi là B2 hoàn chỉnh hoặc tự yêu cầu đo bù. A2 tạm dừng. Hồ sơ riêng `backend/storage/local/hr-B2-20261107-interrupted.json`; không tạo lại metadata chẩn đoán như thể script cũ đã ghi được.

## Rà code khi thiết bị ngắt nguồn

| Quan sát | Diễn giải đúng |
|---|---|
| `mqtt_transport.cpp` gọi `WiFi.setSleep(false)` | Trong framework đang cài, bool false ánh xạ sang `WIFI_PS_NONE`, tắt modem sleep. Đây là một yếu tố phần mềm có thể làm tăng tiêu thụ điện; chưa chứng minh là nguyên nhân duy nhất gây nóng |
| Code đặt công suất phát 17 dBm | Là cấu hình được yêu cầu; chưa có đo dòng/RF hoặc xác nhận giá trị áp dụng thực. Không tự tăng công suất để chữa kết nối |
| Board build có `f_cpu=240000000L` | Mục tiêu build 240 MHz, chưa có phép đo tải/nhiệt tương ứng. Không giảm xung hàng loạt khi chưa xem lại thời gian xử lý và FIFO |
| Worker PPG chờ queue; network có `vTaskDelay(20 ms)`; loop sensing có delay theo nhịp | Không thấy vòng bận vô hạn hiển nhiên ở các đường này. Không đồng nghĩa đã đo toàn bộ tải CPU hoặc loại trừ lỗi khác |
| Chưa log nhiệt nội tại/reset reason | Không thể xác nhận quá nhiệt, nhiệt vỏ, mức an toàn tiếp xúc da hoặc loại reset từ những log đang có |

Cơ sở: [Wi-Fi ESP32-S3 — modem sleep](https://docs.espressif.com/projects/esp-idf/en/v4.4.1/esp32s3/api-guides/wifi.html) mô tả việc tắt modem sleep làm tăng tiêu thụ điện để giảm độ trễ nhận. [Temperature sensor ESP32-S3](https://docs.espressif.com/projects/esp-idf/en/v5.0/esp32s3/api-reference/peripherals/temp_sensor.html) đo nhiệt nội tại; không thay phép đo nhiệt bề mặt chạm da. Đã đọc thêm implementation `WiFiGenericClass::setSleep` của framework local, không chỉ dựa vào tên API.

## Việc đã sửa và việc chưa làm

- Đã sửa `scripts/capture_ppg_trace.py`: lưu raw/chẩn đoán thu dở, ghi trạng thái `interrupted`, giữ lỗi đọc gốc riêng với lỗi dọn cổng, đóng cổng và không tự reconnect/reset ESP. Dữ liệu rỗng không báo hoàn chỉnh.
- PASS 6 test giả lập: lượt hoàn chỉnh/lọc bỏ CONFIG chứa secret; rút USB; lỗi gửi `q` không che lỗi đọc; không mở được cổng; người dùng ngắt; không có mẫu. Tests chỉ dùng cổng/đồng hồ giả và thư mục tạm, không cấp nguồn thiết bị. Thêm lệnh này trong job firmware CI hiện có; chưa chạy CI GitHub mới.
- Chưa đổi chế độ Wi-Fi, công suất phát, xung CPU hoặc thuật toán HR; chưa nạp bản mới sau báo nóng. Không gọi việc sửa công cụ ghi log là sửa được nhiệt.

## Trình tự sau checkpoint này

### Clean/build theo đề nghị của Tân — 2026-11-07

Trung xác nhận “clean code” ở đây là Clean PlatformIO rồi build lại. Đã xác minh đường dẫn project/build nằm trong workspace và chạy tuần tự:

```powershell
.\.venv\Scripts\python.exe -m platformio run -d ai/edge_firmware -e esp32s3_ppg_led10 -t clean
.\.venv\Scripts\python.exe -m platformio run -d ai/edge_firmware -e esp32s3_ppg_led10
```

Clean PASS (0,66 giây), fresh build PASS (46,74 giây); RAM static 79.236 byte, flash chương trình 944.941 byte. Có `firmware.bin` mới; log/hash lưu local trong `hr-clean-rebuild-20261107.log/.json`. **Chưa upload, không thay thuật toán HR hoặc cấu hình điện năng.** Clean xóa sản phẩm build, không chứng minh đã xử lý nguyên nhân nóng chip. Lượt A2 chưa bắt đầu.

**Cập nhật sau khi Trung báo đã cắm USB:** đã nhận COM7, Wi-Fi/MQTT/sync hoạt động; nạp đúng binary clean ở env `esp32s3_ppg_led10`, PASS 10,48 giây và hash flash verified. Hash binary khi upload khớp bản vừa clean/build. WebSocket sau boot mới nhận 3 frame DEVICE `0.3.13-led10`, GSR và hai vector IMU đầy đủ. Không đổi thuật toán/cấu hình điện năng, chưa đo nhiệt và không kết luận hết nóng. Log `hr-clean-upload-20261107.log` và `hr-clean-upload-20261107-ws.json` giữ local. Chưa bắt đầu A2; vẫn cần xác nhận tư thế và không nóng bất thường trước thu, dừng ngay nếu nóng trở lại.

### Điều kiện trước khi đo lại

1. Giữ ngắt nguồn, để nguội và không đeo thử. Ghi nhận vị trí nóng đã có; không yêu cầu chạm chip hoặc bật lại chỉ để xác định.
2. Phần phần mềm có thể chuẩn bị offline: cấu hình thử bật modem sleep thay vì ép radio luôn thức; log thưa nhiệt nội tại/reset reason, có kiểm tra lỗi; đo lại độ trễ MQTT khi có điều kiện kiểm trên bàn. Không dùng deep/light sleep của CPU khiến đứt lịch lấy mẫu hoặc USB, và không hạ xung CPU thiếu số đo.
3. Chưa được coi các thay đổi đó là chứng minh thiết bị an toàn. Nếu có lỗi nguồn, chập hoặc module hỏng, chỉ lọc HR/giảm tải không xác nhận khắc phục được; cần kiểm nguồn và mạch với Tân trước khi quay lại đo đeo.
4. Trong lúc chưa kiểm thiết bị, vẫn dùng A1/B1 và các trace cũ để đánh giá thuật toán offline. Không yêu cầu người dùng giữ cổ tay hoặc lặp ánh sáng để bù B2 gián đoạn.

Kế hoạch HR và các bằng chứng khác: [kế hoạch hiện hành](05-HR-ROOT-CAUSE-PLAN.md). Tiêu chí sai số/khả năng có kết quả vẫn giữ; không dùng việc chip nóng để kết luận sóng yếu hoàn toàn do thuật toán hoặc ngược lại.
