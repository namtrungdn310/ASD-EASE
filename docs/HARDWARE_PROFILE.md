# Cấu hình và kiểm chứng phần cứng

## Tình trạng

Chưa kiểm chứng phần cứng thật. Tên ESP32-S3 Super Mini không đảm bảo cùng sơ đồ chân, flash, PSRAM, USB hoặc mạch nguồn/sạc.

Giai đoạn 00 cần ghi: ký hiệu board, nguồn mua/sơ đồ nếu có; chip, CPU, flash, PSRAM, heap; phiên bản firmware; chân/bus I2C, ADC1; USB và thông số nguồn/pin an toàn. MAC nếu thu được chỉ lưu trong hồ sơ phù hợp, không công khai khi không cần.

## Cấu hình trong code, không phải số đo

| Mục | Hiện tại | Cần kiểm chứng |
|---|---|---|
| MAX30102 | Wire, SDA8/SCL9 | Dây nối, tốc độ, mất mẫu |
| MPU6050 | Wire1, SDA10/SCL11 | Dây nối, hướng trục, hiệu chuẩn |
| GSR | PIN_GSR_ADC=7 sau PR #11 | Tân xác nhận chân thật, điện áp, mô-đun; GPIO4 trong ghi chú cũ đã lỗi thời |
| PPG | Chip100 Hz, averaging2 → FIFO50 Hz danh định | Số mẫu thực, jitter và tràn FIFO |
| IMU/GSR | Lịch gọi50/20 Hz | Tốc độ, thời gian và mất mẫu thực |
| Firmware | esp32s3_supermini, esp32-s3-devkitc-1, phiên bản0.2.0, flash cấu hình4 MB | Board, dung lượng thật và PSRAM |
| Header tương thích | pins.h/sensor_config.h dùng board_config.h | Build không xác nhận phần cứng |
| HardwareProfiler | Có trong src/hardware/HardwareProfiler.cpp; setup chưa gọi | Cần chạy chẩn đoán trên board và lưu kết quả |

Availability/EngineeringState nằm trong common_types.h; trạng thái cảm biến và hằng số ở board_config.h. Không đổi giá trị chỉ để khớp comment cũ.

MAX30102 trả số đếm red/IR; MPU6050 trả gia tốc/vận tốc góc; GSR trả ADC có lấy trung bình. Không gọi ADC là độ dẫn đã hiệu chuẩn. Xem [ánh xạ driver](contracts/DRIVER_MAPPING.md) để đổi đơn vị và phân biệt số thô/số đã lọc.

Giai đoạn 00 vẫn NOT_STARTED theo hồ sơ hiện có. Chỉ DONE khi có bằng chứng kiểm chứng thật.

