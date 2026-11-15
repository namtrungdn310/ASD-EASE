# Gia tốc và tốc độ xoay trên Dashboard

Ngày2026-11-05. Theo yêu cầu Trung, firmware0.3.0 gửi **telemetry1.1**, tách dữ liệu MPU6050 thành hai nhóm ba trục. API `/api/v1`, sáu topic MQTT hiện có, control1.0 và raw1.0 không đổi. Không dùng USB làm đường dữ liệu Dashboard.

## Gói dữ liệu

Từ firmware0.3.2: FIFO50Hz/DLPF10Hz, EMA mặc định1; vector gyro đã bù offset sau bước đứng yên ban đầu, raw trước bù vẫn riêng trong driver. Trong lúc lấy offset gửi vector null. Schema và đơn vị không đổi; chi tiết tại [chuỗi đo0.3.2](SENSOR_ACQUISITION_0_3_2.md).

Các trường khác giữ như telemetry1.0. Phần movement của1.1 có dạng sau; đây là ví dụ cấu trúc, không phải số đo thực:

```json
{
  "schema_version": "1.1",
  "movement": {
    "score": null,
    "acceleration": {"x": -0.5, "y": 0, "z": 9.806},
    "angular_velocity": {"x": -90, "y": 0, "z": 20.5}
  }
}
```

| Nhóm | Trục hiển thị | Đơn vị | Nguồn |
|---|---|---|---|
| acceleration | Ax, Ay, Az | m/s² | ax/ay/az sau EMA của driver MPU6050 |
| angular_velocity | Gx, Gy, Gz | degrees/s (°/s) | gx_deg/gy_deg/gz_deg sau EMA, không dùng rad/s |

Cả hai lấy từ cùng một lần đọc thành công, theo dấu/hệ trục driver hiện tại. Driver đã đảo Y/Z; không đảo lại ở serializer/backend/frontend. Gia tốc bao gồm trọng lực, không phải gia tốc tuyến tính đã loại trọng lực. Không lấy norm làm thay ba trục.

Mỗi ô Dashboard hiển thị nổi bật một độ lớn tổng hợp `sqrt(x²+y²+z²)`, cùng đơn vị của nhóm; ba giá trị có dấu vẫn nằm bên dưới. Frontend tính từ cùng snapshot, không tạo trường đo mới hoặc gửi số tổng hợp ngược về backend. Thiếu vector thì cả số chính/trục là dấu —, không tính thành0. Gia tốc tĩnh thường gần9,81 m/s² do trọng lực; độ lớn này không phải điểm0–1 và không thay feature trích xuất theo cửa sổ khi train.

Firmware gửi snapshot mới nhất mỗi1000 ms như trước; đây không phải luồng raw50 Hz. Nhóm vector có đủ x/y/z là số hữu hạn; nếu chưa đọc được/lỗi/cũ hơn1000 ms thì cả nhóm null. Số0 và số âm đều hợp lệ, không thay mẫu thiếu bằng0. Serializer kiểm tra giới hạn hiện tại ±20 m/s²/trục và ±250 degrees/s/trục, làm tròn3 chữ số; thay thang MPU phải rà soát giới hạn. Score có thể vẫn dùng motion-rms-v1 độc lập, không được dùng để suy ngược các trục.

## Tương thích và kiểm tra

- Backend/frontend tiếp tục đọc1.0 với movement chỉ có score. Không tạo thêm trục hoặc số0 cho firmware cũ; giao diện báo chưa có số đo.
- Chỉ1.1 được có hai nhóm mới; phải khai cả acceleration và angular_velocity, mỗi nhóm là vector đầy đủ hoặc null. Gói1.0 kèm nhóm mới hoặc1.1 thiếu nhóm bị từ chối. Chuỗi giả số/bool/NaN/Infinity/trường lạ cũng bị từ chối.
- Hai model tương thích trong schemas/telemetry.py và raw_batch.py của Trung được giữ nguyên. `schemas/imu.py` thêm model1.1; ingestion dùng model tương ứng phiên bản và giữ quy tắc xác thực/phiên/DB→WS.
- Chuẩn hoá số cho kiểm tra trùng giữ giá trị số nguyên/số thực tương đương; không bỏ trục khỏi payload khi broadcast.
- History frontend giữ tối đa60 điểm; đổi phiên/nguồn/thiết bị/phiên bản hoặc thời gian quay lại thì tách history. Null tạo khoảng trống, không nối qua mẫu thiếu. Mỗi nhóm có biểu đồ riêng, ba đường có nhãn trục, màu và kiểu nét khác nhau.
- Ô và biểu đồ điểm chuyển động được thay bằng gia tốc/tốc độ xoay trên Dashboard. Điểm0–1 vẫn có thể dùng trong payload cho tính toán tiếp, không phải AI. Quality/model/prediction không đổi theo việc có trục IMU.

## Cập nhật trên máy Trung và Tân

1. Lấy cùng code, giữ credential/network_config.h riêng từng máy. Khởi động lại npm run dev để launcher build backend mới; máy Trung đã build/chạy backend1.1 trong buổi này.
2. Nạp env esp32s3_supermini với header local đúng Wi-Fi/IP/account, qua cổng USB thực. Kiểm tra firmware_version=0.3.0, schema_version=1.1.
3. Dashboard có Ax/Ay/Az và Gx/Gy/Gz. Để yên rồi nghiêng/xoay nhẹ MPU; so sánh dấu/đơn vị với Serial. Gia tốc tĩnh có thành phần trọng lực nên không mong cả ba bằng0.

Build/native/API/broker tests không thay nghiệm thu board. Ghi rõ phần đã nạp/đã nhìn thấy thật trong05-VERIFICATION; chưa kết luận độ chính xác đo từ việc hiện số.
