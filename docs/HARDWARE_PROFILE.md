# Cấu hình và kiểm chứng phần cứng

## Tình trạng

Đã nhận dạng một phần board thật ngày2026-11-05 trên máy Trung bằng esptool4.11.0/COM7: ESP32-S3 QFN56 rev0.2, flash4 MB XMC, chip báo PSRAM nhúng2 MB AP_3v3, crystal40 MHz, USB-Serial/JTAG. eFuse báo flash Quad/3.3 V. Chưa kiểm tra PSRAM runtime, dây/nguồn, nhịp mẫu hoặc dữ liệu cảm biến. Không lưu MAC vào tài liệu công khai.

Tên ESP32-S3 Super Mini không đảm bảo mọi board cùng sơ đồ chân, flash, PSRAM, USB hoặc mạch nguồn/sạc. Kết quả trên chỉ áp dụng board Trung đang cầm; xem [tiến độ chạy thật](integration/05-LOCAL-BRINGUP.md).

Trung xác nhận dây theo GPIO trong bảng dưới, cả3 cảm biến cấp3V3 và chung GND. Chưa đo nguồn/ADC bằng đồng hồ, chưa chạy driver hoặc xác nhận tốc độ cảm biến.

Giai đoạn 00 cần ghi: ký hiệu board, nguồn mua/sơ đồ nếu có; chip, CPU, flash, PSRAM, heap; phiên bản firmware; chân/bus I2C, ADC1; USB và thông số nguồn/pin an toàn. MAC nếu thu được chỉ lưu trong hồ sơ phù hợp, không công khai khi không cần.

## Cấu hình trong code, không phải số đo

| Mục | Hiện tại | Cần kiểm chứng |
|---|---|---|
| MAX30102 | Wire, SDA8/SCL9 | Dây nối, tốc độ, mất mẫu |
| MPU6050 | Wire1, SDA5/SCL11 | Dây nối, hướng trục, hiệu chuẩn |
| GSR | PIN_GSR_ADC=7 sau PR #11 | Tân xác nhận chân thật, điện áp, mô-đun |
| PPG | Chip100 Hz, averaging2 → FIFO50 Hz danh định | Số mẫu thực, jitter và tràn FIFO |
| IMU/GSR | Lịch gọi50/20 Hz | Tốc độ, thời gian và mất mẫu thực |
| Firmware | esp32s3_supermini, esp32-s3-devkitc-1, phiên bản0.2.0, flash cấu hình4 MB khớp chip thật | Đã đọc flash4 MB/PSRAM nhúng2 MB; còn kiểm tra PSRAM runtime và firmware nạp thật |
| Header tương thích | pins.h/sensor_config.h dùng board_config.h | Build không xác nhận phần cứng |
| HardwareProfiler | Có trong src/hardware/HardwareProfiler.cpp; setup chưa gọi | Cần chạy chẩn đoán trên board và lưu kết quả |

Availability/EngineeringState nằm trong common_types.h; trạng thái cảm biến và hằng số ở board_config.h. Không đổi giá trị chỉ để khớp comment cũ.

MAX30102 trả số đếm red/IR; MPU6050 trả gia tốc/vận tốc góc; GSR trả ADC có lấy trung bình. Không gọi ADC là độ dẫn đã hiệu chuẩn. Xem [ánh xạ driver](contracts/DRIVER_MAPPING.md) để đổi đơn vị và phân biệt số thô/số đã lọc.

Giai đoạn 00 vẫn NOT_STARTED theo hồ sơ hiện có. Chỉ DONE khi có bằng chứng kiểm chứng thật.
