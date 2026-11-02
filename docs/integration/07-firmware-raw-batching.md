# 07 — Bộ đệm raw và gửi batch trên ESP32

| Mục | Nội dung |
|---|---|
| Nhánh | `feature/firmware-raw-batching` |
| Phụ trách | Trung — IT; Tân xác nhận driver/tốc độ |
| Phụ thuộc |05/06 và có số đo rate/timestamp |
| Ước lượng |1,5–3 ngày, chưa tính chờ board |
| Tiến độ |[Dòng07](PROGRESS.md) |

## Kết quả và phạm vi

Thu chuỗi trước EMA, gửi raw HTTP đúng đặc tả, giữ batch bất biến khi retry và tiếp tục lấy mẫu khi mạng mất. MQTT telemetry/lệnh vẫn từ05, không đưa raw vào broker. Theo [kiến trúc](MQTT_ARCHITECTURE.md).

Thêm bộ đệm/đóng batch/JSON và HTTP uploader trong include/, src/acquisition/ hoặc src/communication/. Tích hợp tối thiểu sensor/main, ưu tiên đường lấy mẫu riêng thay đổi thuật toán đo. Tách cấu hình HTTP/broker, thêm bộ đếm và tests/giai đoạn07–08. USB/parse Pretty JSON trên laptop không thay raw thật.

## Phải kiểm tra trước

- [ ] Đo số mẫu từng luồng theo clock; tách rate chip PPG khỏi FIFO sau trung bình.
- [ ] Driver PPG trả snapshot cuối chưa đủ; expose từng cặp red/IR có thứ tự, không nhân bản cùng giá trị100 lần.
- [ ] Chỉ thêm khi có sample mới; lỡ mẫu dùng null/gap theo đặc tả.
- [ ] IMU trước EMA đúng g/degrees/s; GSR ADC sau trung bình nhưng trước EMA, ghi rõ phép xử lý.
- [ ] Đo rate/jitter/loss và căn mẫu0 chung. Không đáp ứng clock1.0 thì đề xuất version mới, không giả alignment.

## Bộ đệm và mạng

- [ ] Một epoch/phiên, ID tăng; chỉ reset khi phiên mới, không khi Wi-Fi nối lại.
- [ ] Vị trí mẫu theo clock/rate; thiếu giữ null, không dồn thời gian.
- [ ] Cửa sổ thử1 s; tính số mẫu, byte JSON, RAM đỉnh và độ sâu hàng đợi trước chốt.
- [ ] Không giả có PSRAM; hàng đợi có hạn, tránh copy lớn/cấp phát vô hạn.
- [ ] Quyền sở hữu buffer rõ, task mạng không sửa vùng đang thu.
- [ ] Batch đóng giữ nguyên ID/timestamp/nội dung trong mọi retry.
- [ ] Chỉ HTTP ACK đúng batch đã lưu mới release; response lỗi, PUBACK hay ACKStop không đủ.
- [ ] Khi đầy: drop policy/bộ đếm/gap đúng đặc tả, không chờ mạng trong loop hoặc xoá mẫu âm thầm.
- [ ] Mất mạng lâu vẫn giữ timeline; số mẫu/batch bị bỏ không đếm đôi do retry.
- [ ] Reboot không giả queueRAM còn; ghi phần mất/chưa ACK, phiên mới khi đổi epoch; không tự thêm ghi flash.
- [ ] Lệnh/telemetry được xử lý kịp nhưng raw không bị bỏ đói; đo số gửi thành công/retry/drop/thời gian.
- [ ] HTTP chậm không chặn MQTT keepalive/Stop hoặc sensing; tính tổng stack/heap/TLS và RAM khi hai kênh lỗi.
- [ ] Broker mất/HTTP còn vẫn gửi raw của phiên hợp lệ; HTTP mất/MQTT còn phải báo thiếu dù chart chạy. Không đổi phiên khi một kênh nối lại.

## Stop và gửi nốt

- [ ] Chốt cutoff, đóng batch cuối ngắn theo số mẫu thật, không chèn0.
- [ ] MQTT ACKStop/tổng kết có finalID/mất mẫu; lặp không tạo batch cuối lần2.
- [ ] Tổng kết có thể trước/sau rawHTTP; backend đối chiếu độc lập thứ tự.
- [ ] Gửi backlog trong hạn hữu hạn, không đợi Wi-Fi mãi.
- [ ] Chỉ báo đủ sau raw ACK/đối chiếu; timeout phải thiếu.
- [ ] Thử phiên mới khi phiên cũ đang gửi nốt, không nhầm epoch/ID/buffer, giữ quy tắc một phiên hoạt động.

## Kiểm thử

| Ca | Cần đối chiếu |
|---|---|
| Mẫu có thứ tự biết trước | Số mẫu, thứ tự, đơn vị và ranh batch không trùng |
| Batch cuối ngắn | Timestamp/count đúng, không padding0 |
| Backend đã ghi nhưng mất ACK | Retry cùng payload, ACKtrùng, release đúng |
| Mất Wi-Fi ngắn | Gửi bù đúng, không trùng |
| Mất lâu/quá queue | RAM hữu hạn, có gap/loss, vẫn lấy mẫu |
| Có/không mạng trên board | Rate/jitter/heap/queue thực |
| Cảm biến lỗi/reboot/timeoutStop | Null/gap/ABORTED, không biến cache thành mẫu mới |
| Lỗi riêng MQTT/HTTP | Không báo đủ giả |
| HTTP chậm khi Stop tới | Xử lý Stop hữu hạn, batch cuối bất biến |
| MQTT+HTTP+sensing đồng thời | Có số đo tài nguyên, không chỉ build |

Sóng giả chạy trên board vẫn là SYNTHETIC. DEVICE chỉ dành dữ liệu cảm biến thật.

## Nghiệm thu và khôi phục

- [ ] JSON raw qua schema, build và CI đạt.
- [ ] Có bảng rate/window/queue/RAM, retry/overflow tests.
- [ ] Log board đối chiếu với file lưu, có Stop/gửi nốt.
- [ ] Thiếu board/rate thì WAITING_HARDWARE, không đóng giai đoạn08.
- [ ] Commit gợi ý: `feat(firmware): đệm và gửi batch raw đúng thứ tự`.

Có thể tắt raw upload để giữ telemetry/Serial; giữ bản ghi/log. Không reset ID giữa phiên để né lỗi server.

## Nhật ký

| Ngày/commit | Việc | Bằng chứng | Kết quả |
|---|---|---|---|
|—|—|—|Chưa thực hiện|
