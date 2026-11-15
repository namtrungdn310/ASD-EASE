# Chất lượng bốn nhóm số đo — telemetry 1.2

Cập nhật 15/11/2026: mỗi nhóm nhận thêm `sample_count` tùy chọn (số nguyên không âm hoặc null), đếm trực tiếp trong 8 giây thu mẫu đã hoàn tất trên ESP. Không đếm telemetry hoặc mẫu HR tạm tính; firmware cũ chưa gửi vẫn được nhận. Xem [quy ước số mẫu](../integration/05-SENSOR-SAMPLE-COUNTS.md).

Cập nhật14/11/2026: firmware từ `0.4.0-tracker` phát method `engineering-v2`.
Backend/frontend nhận cả v1 và v2. Chi tiết công thức mới, điều chỉnh LED,
khử nhiễu IMU và kết quả kiểm tra ở [HR v2](../integration/05-HR-OPTIMIZATION-V2.md).
Phần mô tả `trackingEvidence` bên dưới ghi lại công thức v1; v2 dùng SQI từ
các thành phần sóng đã chuẩn hóa, đối chiếu hai kênh và ảnh hưởng chuyển động.

Ngày 2026-11-09. Firmware `0.3.27-tracker` bổ sung điểm kỹ thuật `engineering-v1`;
giữ nguyên bộ HR của 0.3.26, LED, tốc độ lấy mẫu, bộ lọc và cổng nhận HR.
Không đổi topic, raw, control, API URL hoặc xác thực. Backend/frontend tiếp tục nhận 1.0/1.1.

## Gói dữ liệu

1.2 giữ các trường của telemetry1.1, thay `signal_quality` bằng:

```json
{
  "method": "engineering-v1",
  "window_ms": 8000,
  "hr": {"score": 0.32, "reason": "weak_signal"},
  "gsr": {"score": 1, "reason": "ok"},
  "acceleration": {"score": 0.95, "reason": "saturated"},
  "rotation": {"score": null, "reason": "calibrating"}
}
```

Đây là ví dụ cấu trúc, không phải kết quả đo. `score` là số hữu hạn 0–1;
FE nhân100 và làm tròn để hiển thị. `null` khác0. Trường ngoài khai báo, bool/chuỗi giả số,
NaN/Infinity bị từ chối. 1.0/1.1 vẫn dùng `ppg/gsr/imu`; không đổi ý nghĩa0 của firmware cũ.

## Cách tính và giới hạn

- Mỗi driver ghi nhận **từng mẫu mới trước bộ lọc phần mềm**. Cache `read()` không thêm mẫu.
  PPG/IMU50Hz, GSR20Hz; một mẫu GSR là trung bình8 lần ADC, bị đánh dấu nếu bất kỳ lần nào chạm rail0/4095.
- Dùng8 bucket giây đã hoàn tất, cộng bucket hiện tại để phát hiện dữ liệu cũ;
  khởi động cần khoảng8–9giây. Lỗi/mất FIFO làm thiếu mẫu, không tạo bù.
- `coverage = min(1, số mẫu nhận / số mẫu danh định trong8giây)`.
  `usable = số mẫu không chạm giới hạn / số mẫu nhận` (không có mẫu thì0).
  Điểm thu mẫu=`coverage × usable`. Dưới98% coverage ghi `missing_samples`;
  nếu có mẫu chạm rail, ưu tiên lý do `saturated` và vẫn giữ điểm theo tỷ lệ.
- Gia tốc và gyro theo dõi chạm rail riêng trên số nguyên thô của ba trục,
  dùng ngưỡng hiện có ±32760. Chuyển động lớn còn trong dải không tự làm chất lượng thấp.
  Gyro đang hiệu chỉnh thì cả hai điểm IMU tạm `null` theo trạng thái driver hiện tại.
- GSR chỉ đánh giá thu ADC/rail; điện áp ngoài vùng đọc hiện có vẫn dùng trạng thái lỗi của driver.
  **Không xác nhận tiếp xúc điện cực tốt, độ dẫn đã hiệu chuẩn hoặc phản ứng sinh lý đúng**.
- HR lấy điểm thu PPG nhân `trackingEvidence` hữu hạn0–1 từ cửa sổ sóng8giây mới nhất
  (tracker đã phối hợp cửa sổ8/4giây, phổ, tự tương quan và độ lặp hình dạng).
  Không dùng `massScore`, tuổi/số HR đã làm mượt, dự báo FE hoặc nhịp nghỉ mong muốn.
  Chỉ dùng analysis cùng generation và tuổi≤1500ms; không có thì điểm `null`.
  Không tiếp xúc, quá tải quang hoặc cổng chuyển động đang chặn → điểm0 và lý do tương ứng.
  Evidence<0,5 ghi `weak_signal` nếu không có lỗi thu mẫu ưu tiên hơn.
- Điểm thu mẫu cập nhật theo giây; điểm sóng thuộc cửa sổ phân tích gần nhất,
  không phải toàn bộ chúng được đo tại đúng một thời điểm. Tuổi mẫu PPG/GSR/IMU>1000ms
  hoặc snapshot chờ mạng quá lâu → điểm `null/stale`, không gia hạn từ cache.

**Không phải phần trăm độ chính xác hoặc xác suất HR đúng.** Dao động nhiễu có tính chu kỳ
vẫn có thể có điểm cao. Điểm GSR/IMU100% chỉ nói rằng các kiểm tra thu mẫu này chưa thấy lỗi.
Chưa có nhãn chất lượng trên người để hiệu chuẩn thang điểm. Điểm chỉ để quan sát,
không làm thay đổi HR, loại mẫu raw, dự đoán AI hoặc điều khiển phiên.

## Lý do và giao diện

`warming_up/stale/calibrating/unavailable` yêu cầu score=null.
Các lý do có điểm: `ok/no_contact/motion/saturated/missing_samples/weak_signal`.
Dashboard đặt điểm cùng lý do dưới số đo của từng card, không chỉ dùng màu.
80%/50% là mốc màu giao diện, chưa phải ngưỡng được hiệu chuẩn.
Mất kết nối thì ẩn phần trăm cũ, ghi “Không có dữ liệu mới”. HR nét đứt tạm tính
không tạo hoặc nâng điểm chất lượng. Firmware cũ ghi “Chưa đánh giá”, không suy điểm từ biểu đồ.

## Kiểm tra

- `python scripts/check_measurement_quality.py`: cửa sổ, cache, mất mẫu, chạm rail,
  clock64bit, cổng PPG, TTL, bốn gói serializer C++ qua schema backend.
- `python scripts/check_sensor_drivers.py`: driver thật với fake I2C/ADC/clock,
  gồm thu đủ PPG, rail GSR và gyro chạm giới hạn độc lập gia tốc.
- `backend/tests/test_metric_quality.py`: schema1.2, HTTP/MQTT→WS, duplicate, số sai/null,
  tương thích phiên bản.
- `frontend/tests/metric-quality.test.mjs`: parser,0/null, mất mạng, điểm IMU riêng,
  giữ sáu trục trong history.

Kiểm thử phần mềm không thay xác nhận độ chính xác HR cổ tay hoặc độ an toàn nhiệt của thiết bị.

Đã nạp trên ESP máy Trung và nhận20 frame DEVICE thực quaMQTT→BE→WS,
đúng0.3.27/schema1.2. Trong lượt kiểm kết nối, HR0/no_contact, GSR cuối lượt0/saturated,
gia tốc/gyro1/ok; không xác nhận có đặt lên da nên đây không phải phép đo chất lượng trên người.
Replay20frame qua parser/history và render Dashboard thật: cả4card giữ đúng điểm/lý do;
chuyển stale ẩn mọi phần trăm. Trình duyệt tự động hiện không có kết nối,
chưa kiểm hình ảnh trên browser. Bằng chứng local:
`ppg-new-usb-link-20261109-200318-7fd8f0.json`, `metric-quality-20261109-frontend.json`.
