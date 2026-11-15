# HR cổ tay — điều chỉnh quang học và xử lý IMU

Firmware bàn giao: `0.4.2-tracker`. Ngày triển khai: 14/11/2026.
Đây là bản phát triển trên MAX30102 hiện tại; cần kiểm chứng trên cổ tay,
chưa xác nhận độ chính xác tương đương đồng hồ thương mại.

## Bốn phần đã triển khai

| Phần | Cách hoạt động | File chính |
|---|---|---|
| Điều chỉnh LED | RED/IR độc lập, có giới hạn, đọc lại thanh ghi và bỏ quá độ sau đổi dòng | `ppg_exposure.h`, `MAX30102Sensor.cpp` |
| Chọn kênh | Chấm từng kênh, ưu tiên kênh có chu kỳ rõ; hai kênh rõ nhưng mâu thuẫn vẫn bị từ chối | `ppg_cycle_tracker.h` |
| Khử nhiễu IMU | Sáu trục có timestamp, lọc cùng băng với PPG, NLMS có kiểm tra đoạn cuối | `ppg_motion.h`, `ppg_rate.h`, `ppg_hybrid_worker.cpp` |
| Chất lượng v2 | Kết hợp thu mẫu, phổ, chu kỳ, hình dạng, độ nhất quán và chuyển động | `ppg_cycle_tracker.h`, `measurement_quality.h` |

Các header nằm trong `ai/edge_firmware/include/processing/`.

## Điều chỉnh LED

- Giữ cấu hình 200 Hz/gộp4, FIFO50 Hz, xung411 µs, ADC18 bit.
- Mỗi LED nằm trong16–100 count, tương đương khoảng3,2–20 mA danh định;
  khởi động50 count (~10 mA). Đây là giới hạn phát triển, không dùng dòng tối đa của chip.
- DC dưới20.000 count mới đề nghị tăng; trên180.000 hoặc có quá tải đề nghị giảm.
  DC lớn không chứng minh có sóng mạch.
- Tăng chỉ khi có tiếp xúc ổn định và IMU cho biết tay đang yên.
  Cần ít nhất50 mẫu liên tiếp đủ điều kiện; không lấy trung bình mẫu hở da
  trộn với lúc vừa đặt tay để đề nghị tăng dòng.
  Giai đoạn dò ban đầu tối đa5 bước, cách nhau ít nhất1 giây;
  sau đó khoảng cách điều chỉnh ít nhất20 giây.
- Quá tải có thể đề nghị giảm sau ít nhất1 giây, không chờ hết khoảng giữ20 giây.
- Khi vừa có HR được tracker chấp nhận, không tăng LED để đuổi theo một ngưỡng DC.
- Shutdown tạm PPG, ghi từng LED, đọc lại xác nhận, xóa FIFO rồi mở lại.
  Một giao dịch I2C mỗi poll, không chặn GSR/IMU để chờ.
  Lỗi ghi/đọc lại dẫn tới phục hồi và không phát HR từ cấu hình chưa xác nhận.
- Đổi dòng tạo generation phân tích mới, bỏ1 giây quá độ và thu lại cửa sổ;
  không nối sóng thuộc hai mức LED như cùng một cấu hình.

## Ghép IMU và xử lý chuyển động

- Observer lấy từng mẫu IMU trước EMA; gia tốc chia9,80665, gyro chia90 để chuẩn hóa.
  Dữ liệu GSR và hai vector hiển thị vẫn giữ cách tính/đơn vị hiện có.
- Tìm mẫu IMU gần nhất trong25 ms theo clock monotonic cùng boot.
  Mỗi cửa sổ8 giây lưu cả cờ ghép đúng; cần ít nhất95% mẫu ghép được.
- IMU được lọc cùng băng0,5–4 Hz với PPG. Bộ lọc NLMS dùng6 trục,
  3 tap/trục; học hệ số trên6 giây đầu, đóng băng và kiểm trên2 giây cuối.
- Chỉ dùng sóng sau khử khi năng lượng dư trên đoạn kiểm còn8–90% đầu vào,
  và bằng chứng chu kỳ cải thiện hoặc ứng viên cũ bị IMU chỉ ra là nhịp chuyển động.
- Nếu ứng viên HR trùng thành phần tuần hoàn mạnh của IMU, chưa công nhận HR.
  Không tạo nhịp từ gia tốc hoặc ép về nhịp nghỉ mong muốn.
- Có thể phát HR khi tay chuyển động nếu cửa sổ PPG/IMU đủ bằng chứng;
  IMU mất/mẫu cũ vẫn không cho vượt cổng chuyển động bằng kết quả cũ.
- Task phân tích chạy riêng; cửa sổ lớn nằm trong BSS/queue cố định, không trên stack.

## Điểm chất lượng `engineering-v2`

Giữ schema telemetry1.2 và các trường hiện có. Backend/frontend đọc cả v1/v2;
firmware mới phát method `engineering-v2`.

1. Trong mỗi kênh, tính bốn thành phần0–1: độ lặp chu kỳ, tập trung năng lượng phổ,
   độ lặp hình dạng và nhất quán giữa cửa sổ8/4 giây.
2. Lấy trung bình nhân bốn thành phần; kết hợp hai kênh theo bằng chứng của từng kênh.
3. Giảm điểm khi RED/IR bất đồng hoặc còn thành phần trùng chuyển động.
   Một kênh đơn được hệ số0,85 vì thiếu đối chiếu kênh còn lại.
4. Nhân với tỷ lệ mẫu nhận đủ và không chạm rail. Quá tải/mất tiếp xúc/cử động
   chưa xử lý được vẫn có lý do riêng; chưa đủ dữ liệu hoặc analysis cũ thì null.

Điểm này là chỉ báo kỹ thuật, chưa được hiệu chuẩn bằng nhãn người.
Không phải xác suất HR đúng. Không dùng posterior, BPM đã làm mượt hoặc dự báo frontend
để tăng điểm. GSR/gia tốc/gyro giữ nguyên công thức thu mẫu v1.

## Kiểm tra và bằng chứng

Các lệnh chạy từ root bằng Python trong `.venv`:

```powershell
python scripts/check_ppg_optimization.py
python scripts/check_ppg_tracker.py --unit-only
python scripts/check_ppg_hybrid_driver.py --tracker
python scripts/check_sensor_drivers.py
python scripts/check_measurement_quality.py
python scripts/test_capture_ppg_trace.py
python -m platformio run -d ai/edge_firmware -e esp32s3_supermini
```

Đã giữ snapshot core trước sửa trong thư mục local được Git bỏ qua,
biên dịch hai phiên bản và replay cùng đầu vào. Bộ so sánh ghi SHA256 đầu vào;
không gán nhãn HR cho dữ liệu người thiếu tham chiếu đồng bộ.

- Sóng mô phỏng sạch40–200 bpm: độ phủ được giữ, sai số trung bình dưới1 bpm.
- Sóng mô phỏng có nhiễu tuần hoàn được IMU đo: sau khử, sai số trung bình dưới1 bpm
  trong các trường hợp đã thử; đây là mô hình nhiễu cộng tuyến tính thuận lợi,
  không thay độ chính xác trên cổ tay thật.
- Chỉ có chuyển động tuần hoàn: bản cũ nhận48/49 cửa sổ; bản mới nhận0/49.
- Nhiễu trắng và nhiễu màu vẫn còn lần nhận nhầm: lần lượt3/49 và10/49,
  không tăng so với bản trước. Điểm trung bình các lần nhận này khoảng0,39.
  Không sửa nhãn hoặc giấu các trường hợp này để báo đạt hoàn toàn.
- Bốn lượt cổ tay cũ: số cửa sổ có HR không tăng. File cũ không chứa IMU đồng bộ
  nên không kiểm chứng được khử nhiễu; cũng không có HR tham chiếu để tính sai số.
- Backend:132 test đạt. Frontend build và kiểm tra parser/quality/hook kết nối thủ công v2 đạt.
  Lượt chạy toàn bộ frontend cũ có27 test lỗi do còn kỳ vọng tự mở WebSocket/
  giao diện chọn thiết bị cũ; không sửa hành vi kết nối đã được người dùng chốt để chạy theo test cũ.
- Core mới:14 tình huống AGC/kênh/SQI/IMU đạt;12 tình huống tích hợp driver/AGC/snapshot đạt;
  46 ca tracker,20 ca dải nhịp,46 ca hình dạng,92 ca driver cảm biến,
  29 ca chất lượng và7 ca công cụ thu đạt. Các nhóm có phạm vi khác nhau, không cộng thành số thí nghiệm người.

## Thu dữ liệu mới

`capture_ppg_trace.py` vẫn lưu CSV PPG3 cột như cũ. Firmware v2 bổ sung file
`*-motion.csv` cùng timestamp PPG, timestamp IMU, cờ ghép,6 trục chuẩn hóa,
hai mức LED và generation exposure. Sidecar ghi số dòng/đơn vị.
Không tự bổ sung IMU cho các file lịch sử thiếu dữ liệu.

Log `[PPG-OPT]` cho biết mức LED hiện tại, số lần đổi, SQI, bằng chứng RED/IR,
tỷ lệ ghép IMU, mức trùng chuyển động và việc có dùng sóng khử nhiễu.
Log `[PPG-HYBRID]` giữ thời gian/stack của worker; `[NET]` giữ heap/gap/mạng.

## Trạng thái

Đã build/nạp và kiểm đường truyền v2. Lượt cổ tay đầu tiên dùng `0.4.0-tracker`:

- Thu40 giây,2.002 mẫu PPG +2.002 dòng IMU; khoảng mẫu tối đa20 ms,
  không rơi trace, lỗiI2C, overflow hoặc gap.
- WebSocket37 gói;13 gói có HR80,3–82 bpm. Điểm chất lượng cao nhất khoảng0,68;
  nhiều cửa sổ vẫn yếu hoặc không có HR, chưa đạt liên tục.
- IMU ghép đủ100% khi đã có cửa sổ. Lượt này chủ yếu yên, `corrected=0`;
  chưa chứng minh khử nhiễu chuyển động thật đã cải thiện HR.
- Worker tối đa408.779 µs/cửa sổ, stack còn5.908 byte;
  vòng sensing tối đa13 ms, heap thấp nhất81.612 byte. MQTT không lỗi gửi.
- Replay đúng file mới trên hai bản:29 cửa sổ đánh giá, bản trước có2 cửa sổ HR,
  bản mới có3. Replay bắt đầu tại đầu file, còn firmware đã có lịch sử trước lúc
  bắt đầu thu; không so trực tiếp3 cửa sổ replay với13 gói live như cùng mốc khởi tạo.
- Không có nhịp tham chiếu đồng thời nên không kết luận số80–82 là nhịp thật.

Sau lượt này, `0.4.1` bổ sung điều kiện50 mẫu tiếp xúc ổn định trước khi tăng LED
và giảm kịp thời khi quá tải. Không thay thuật toán chọn HR để đuổi theo kết quả lượt đo.
Hai điều kiện đã được kiểm bằng test riêng; phép đo trên người ở trên vẫn được ghi đúng là0.4.0.

Lượt40 giây trên `0.4.1`, giữ yên rồi được hướng dẫn cử động cổ tay nhẹ:

- Thu2.001 mẫu PPG +IMU, khoảng mẫu tối đa20 ms, không rơi trace/lỗiI2C/overflow/gap.
- WebSocket39 gói đúng phiên bản; **0 gói có HR**. Kính bị mất tiếp xúc ở cuối lượt;
  ngay đầu lượt khi tiếp xúc ổn định vẫn chưa tách được chu kỳ đủ bằng chứng.
- RED/IR giữ50 count (~10 mA); DC đủ cao nên không tăng dòng chỉ để tăng điểm.
- IMU ghép100%, có chuyển động được ghi nhận. `corrected=0`: thuật toán không
  tìm được phương án khử nhiễu cải thiện bằng chứng để chọn. Chưa xác nhận hiệu quả thực trên cổ tay.
- Worker tối đa739.377 µs/cửa sổ, không ghi đè queue; stack còn5.972 byte,
  heap thấp nhất82.900 byte; vòng sensing tối đa13 ms. Không có lỗi gửi MQTT.

`0.4.2` đọc kết quả worker một lần cho cả HR và SQI để hai giá trị không bị lấy
từ hai cửa sổ khác nhau khi task cập nhật. Đã kiểm driver và build/nạp;
các lượt trên người giữ đúng nhãn0.4.0/0.4.1, không đổi thành bằng chứng cho0.4.2.
Kiểm sau nạp nhận5 gói WebSocket đúng0.4.2/engineering-v2, self-test worker đạt,
Wi-Fi/MQTT/sync hoạt động, không lỗi gửi/I2C/gap. Ở lúc kiểm cuối không có tiếp xúc quang:
IR khoảng991, LED giữ10 mA, HR null. Đây là kiểm đường truyền và trạng thái hở,
không phải lượt đo HR mới. Manifest lưu hash source/binary cuối, không lưu credential.

Trạng thái: **đã triển khai bốn phần và kiểm phần mềm/đường truyền;
HR cổ tay ổn định và độ chính xác vẫn CHƯA ĐẠT NGHIỆM THU**.
Không tiếp tục nới ngưỡng hoặc tăng điểm dựa trên hai lượt đo để tuyên bố đạt.

Bằng chứng local ở `backend/storage/local/hr-v2-20261114-201405/`:
`wrist-capture.json`, `wrist-ws.json`, `ppg-20261114-203703-46e47b.csv`,
`ppg-20261114-203703-46e47b-motion.csv`, sidecar và
`comparison-20261114-204215.json`. Các file này được Git và Docker build bỏ qua.
Lượt cử động nhẹ: `wrist-motion-capture.json`, `wrist-motion-ws.json`,
`ppg-20261114-204714-3761be.csv` và file motion/sidecar cùng tên.
Bản cuối: `release-manifest.json`, `final-runtime-ws.json`, `final-runtime-log.json`.
