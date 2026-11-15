# Rà soát và dọn mã

## Chốt HR và dọn sau các vòng thử — 2026-11-08

Trung xác nhận giữ kết quả hiện tại. Bản đã chốt là **0.3.23-tracker**, không đổi lõi HR, bộ lọc, ngưỡng hoặc cách dự báo FE. Không nạp lại ESP hoặc thu thêm dữ liệu trong lần dọn này.

### Đã bỏ

| Phần thừa | Lý do |
|---|---|
| Năm env `esp32s3_ppg_led10`, `esp32s3_ppg_baseline`, `esp32s3_wrist_12ma`, `esp32s3_wrist_dense`, `esp32s3_hr_demo` | Các lượt thử đã kết thúc; không còn cần bản firmware riêng để nạp |
| Các nhánh chọn LED6,2/12,4mA, chip400Hz/gộp8, phiên bản cũ và profile demo trong cấu hình driver | Cấu hình chạy thống nhất theo bản đã đo: LED10mA, chip200Hz/gộp4, FIFO50Hz |
| Nhánh worker firmware dùng bộ quality cũ thay tracker | Firmware chỉ dùng tracker đã chốt; quality/PpgRate vẫn dùng cho đối chiếu offline |
| Bốn lựa chọn CLI kiểm driver theo profile thử cũ và bốn lệnh tương ứng trong CI | Không giữ bài kiểm cho cấu hình nạp đã bỏ; các ca kiểm lỗi/thu mẫu/serializer vẫn chạy |
| `ai/edge_firmware/include/README`, `lib/README`, `test/README` | Hướng dẫn mẫu do PlatformIO tạo, không mô tả dự án; kiểm thử thực ở `tests/native/` |
| `ai/edge_firmware/test/.gitkeep`, `src/communication/.gitkeep` | Marker thư mục test rỗng cũ và marker dư trong thư mục đã có nguồn |
| `mosquitto/mosquitto.conf`, `mosquitto/config/.gitkeep` | Broker cũ không có caller; Compose/script hiện dùng `infra/mosquitto/` có ACL |

Tổng lượt này xóa **7 file**, bỏ **5 env thử** và các nhánh cấu hình chạy cũ. Có bản sao/hash trước dọn ở `backend/storage/local/hr-final-cleanup-20261108/`, đã được Git bỏ qua. Không dùng `git clean`, không xóa dữ liệu đo hoặc credential.

### Cấu hình còn dùng

- `esp32s3_supermini`: build/nạp mặc định, nay dùng HR0.3.23-tracker. Trước đây lệnh không ghi `-e` có thể build thuật toán cũ.
- `esp32s3_hr_tracker`: alias cùng cấu hình, giữ các lệnh nạp trước đây hoạt động.
- `esp32s3_network_check`, `esp32s3_serial_check`: kiểm build mạng/tắt mạng, không phải bản HR khác.
- CI vẫn giữ 6 tên check bảo vệ nhánh; build cả 4 env còn lại.

### Rà soát toàn dự án

Đã quét danh sách file Git và file nguồn chưa theo dõi, import frontend từ entrypoint, include/khai báo C++, hàm Python, caller trong test/script/CI và tham chiếu các cấu hình cũ. Tất cả module `frontend/src` có đường import từ entrypoint. Những hàm Python bị bộ quét đánh dấu vẫn có caller trong cùng module, nên giữ lại.

Các module AI, giao diện dùng chung và model placeholder nằm trong kế hoạch tiếp theo; không trình bày chúng là mô hình đã chạy. Script benchmark, mô phỏng và native baseline có mục đích kiểm hồi quy cụ thể, không kết nối MQTT hay thay dữ liệu DEVICE. Tùy chọn `--dense` hiện chỉ đổi mô hình đầu vào offline, không còn thay cấu hình driver; báo cáo ghi riêng chip/gộp mẫu của driver để tránh nhầm.

Giữ tài liệu và dữ liệu đo lịch sử để đối chiếu quyết định. Các trang bàn giao/chạy hằng ngày đã chỉ rõ bản hiện tại, tách phần lịch sử. Giữ rule bỏ qua credential broker cũ dù đã bỏ config nguồn. Không xóa cache công cụ, DB, venv, node_modules hoặc bộ logo đã chọn.

### Kiểm chứng sau dọn

| Kiểm tra | Kết quả |
|---|---|
| Tracker / tích hợp driver tracker | PASS 45 / 8 ca |
| Driver cảm biến native / serializer qua schema | PASS 89 ca / 12 snapshot |
| Bộ HR đối chiếu / tích hợp baseline / FIFO / selector | PASS 76 / 8 / 34 / 10 ca |
| Bộ thu raw | PASS 6 ca |
| Protocol firmware C++ | PASS 39 ca |
| Frontend tests và build | PASS 64/64; còn cảnh báo bundle >500kB đã có |
| Backend / AI | PASS 111 / 15 ca; có cảnh báo deprecation từ dependency |
| Hai mô hình đầu vào cổ tay offline | PASS các assertion, mỗi mô hình 10 tình huống; vẫn ghi nhận nhiễu tuần hoàn gây nhận nhầm, không coi là kiểm độ đúng cổ tay |
| Build ESP32 / tổ hợp header | PASS 4/4 env và 4/4 tổ hợp |
| Compose | PASS `docker compose config --quiet` |
| Cấu hình HR trước/sau | Probe C++ cho kết quả giống nhau: phiên bản, chip/gộp mẫu, LED, FIFO, pulse width, ADC range, ngưỡng tiếp xúc, thời gian settle và motion guard |
| Nguồn cần giữ nguyên | Hash 11 file không đổi, gồm core/filter/contact/motion guard, driver PPG/GSR/IMU, utility hiển thị HR, hai schema và header Wi-Fi local |

Log build/header, bản so cấu hình, manifest trước/sau và báo cáo tổng nằm trong thư mục backup local nêu trên. Đây là kiểm tại máy, **chưa chạy CI GitHub, chưa commit/push/merge**. Không dùng kết quả dọn mã để thay kết luận về độ chính xác HR hoặc đánh nhánh5 DONE.

## Lịch sử dọn trước vòng cải thiện HR

Ngày 2026-11-07, nhánh `fix/esp32-local-mqtt-integration`, HEAD trước dọn `d693fd4`. Working tree có nhiều thay đổi chưa commit từ các bước trước; giữ nguyên các phần ngoài phạm vi. Chưa commit/push hoặc nạp firmware trong bước dọn này.

## Cách xác định phần thừa

Đã lập danh sách 387 file được Git theo dõi hoặc chưa theo dõi, chưa tính file ignored. Kiểm import frontend từ `main.tsx`, tham chiếu nguồn/test/CI, include C++, cấu hình dependency và 44 module Python trong `backend/app`/`ai/src`. Static scan chỉ cho ứng viên; kiểm lại nội dung và mục đích trước khi xóa. Không coi mọi file chưa có caller là rác.

Trước dọn: 30 module frontend, 27 module có đường import từ entrypoint. Sau khi kiểm tham chiếu, ba module còn lại đúng là trang giữ chỗ/biểu đồ cũ không được ứng dụng sử dụng.

## Đã dọn

| Thành phần | Bằng chứng và lý do |
|---|---|
| `frontend/src/components/MovementChart.tsx` | Không có import/caller; Dashboard dùng gia tốc và tốc độ xoay riêng qua `ImuReadings`/`ImuChart` |
| `frontend/src/pages/History.tsx` | Chỉ có đoạn placeholder tiếng Anh, không được nối vào App/router/test |
| `frontend/src/pages/Sessions.tsx` | Chỉ có placeholder, không phải `SessionControl`/`useDeviceSession` đang chạy |
| `tests/native/stubs/MAX30105.h` | Không có include; driver PPG đã khởi tạo/đọc thanh ghi trực tiếp, stub cũ không được harness sử dụng |
| Bốn dependency PlatformIO | SparkFun MAX3010x, Adafruit MPU6050, Unified Sensor và BusIO không có include/caller ở nguồn hiện tại. Giữ ArduinoJson 7.4.3 và Wire |
| Chín hằng `board_config.h` không có bên đọc | `PPG_AC_MIN_AMPLITUDE`, `PPG_LOWPASS_HZ`, `PPG_EMA_ALPHA_HR`, `PPG_EMA_ALPHA_SPO2`, hai giới hạn SpO2; `GSR_ADC_FULL_SCALE_MV`, hai giới hạn conductance cũ. Chúng không điều khiển thuật toán đang dùng |
| Ba trường PPG thừa | `rawHeartRate`, `medianHeartRate` chỉ được ghi bằng cùng một HR, không có bên đọc; `rawSpO2` không được dùng. Giữ `heartRate` và trường SpO2 chưa triển khai còn được log đọc |
| Hai rule CSS không có bên dùng | `.context-separator`, `.session-reference`; không đổi bố cục đang hiển thị |

Firmware: các đường dẫn `tests/...` và `include/...` trong báo cáo này tương đối với `ai/edge_firmware/`. Các phép tính/tần số/LED đang dùng không đổi. Việc bỏ hằng GSR không có caller không đổi thuật toán GSR; không sửa driver GSR/IMU.

Đã cập nhật kế hoạch nhánh 09 để không nói hai trang placeholder vẫn tồn tại. Chưa tạo lại trang rỗng để giữ tên file.

## Giữ lại có chủ đích

- Các harness, mock ngoại vi còn được test/CI dùng; script benchmark, mô phỏng và thu raw có lệnh chạy thực.
- Baseline HR và các profile thử LED/lấy mẫu có test và hồ sơ đối chiếu. Chúng không phải các bản chạy đồng thời; chưa xóa bằng chứng thất bại hoặc tự đổi mặc định.
- Policy/hash benchmark cũ và báo cáo lịch sử: giữ nguyên để kiểm được quyết định trước đây, không sửa kết quả cũ theo source mới.
- `model_generated.h`, `model_config.h`, `interfaces.h` và package AI giữ chỗ có mục đích trong kế hoạch xuất mô hình/giao diện dùng chung. Không gọi chúng là mô hình đang hoạt động.
- Credential local, dữ liệu đo, DB, cache PlatformIO/venv/node_modules không thuộc đợt xóa source. Không dùng `git clean` hoặc xóa thư mục sinh dữ liệu.

Đã lưu bản sao các file nguồn bị dọn trong `backend/storage/local/hr-cleanup-20261107/`, kèm manifest/hash; thư mục ignored. Bản inventory trước dọn: `backend/storage/local/hr-cleanup-audit-before.json`. Giữ bản sao để khôi phục riêng từng file, không ghi đè working tree khác.

## Kiểm chứng

| Kiểm tra | Trạng thái |
|---|---|
| Frontend tests | PASS 60/60 sau khi bỏ ba module không dùng |
| Frontend build | PASS; còn cảnh báo bundle lớn hơn 500 kB, không phải lỗi build |
| Driver C++ sản xuất | PASS 89 ca + 12 snapshot qua serializer/schema ở cả bốn profile |
| Bộ HR | PASS 76 ca mỗi profile |
| FIFO / hybrid driver / selector | PASS 34 / 8 / 10 ca |
| Protocol | PASS 39 ca |
| Quality C++/Python | PASS 95 cửa sổ parity; không chạy lại toàn bộ benchmark lịch sử 10.800 cửa sổ |
| Build bảy env ESP32 | PASS 7/7; tổng 12 phút 14 giây, có rebuild framework sau thay dependency |
| Bốn tổ hợp header | PASS 4/4, chạy sau build |
| Rà tham chiếu sau dọn | PASS frontend 27/27 module có đường import; không còn tham chiếu symbol đã bỏ trong nguồn/test firmware |
| Hash hai schema của Trung | Giữ nguyên SHA256 của `raw_batch.py` và `telemetry.py` |
| Tài liệu / diff | PASS link cục bộ, UTF-8, whitespace tài liệu mới và `git diff --check` trong phạm vi dọn |

Các kiểm tra phần mềm trên không phải đo người hoặc CI GitHub mới. Chưa đổi bản đang nạp trên ESP. Hai schema `backend/app/schemas/raw_batch.py` và `telemetry.py` không thuộc nội dung chỉnh của bước dọn.

Log cục bộ: `hr-cleanup-build.log`, `hr-cleanup-headers.log`, `hr-cleanup-frontend-tests.log`, `hr-cleanup-frontend-build.log` và `hr-cleanup-verification.json` trong `backend/storage/local/`. Không xóa cả thư mục này vì còn raw và hồ sơ đối chiếu. Kiểm build frontend lại sau khi bỏ hai rule CSS cũng đạt.

Kiểm trạng thái máy trong lượt này: không thấy thiết bị USB VID `303A`, backend local chưa truy cập được. Không coi đây là lỗi cảm biến hoặc lỗi thuật toán; chưa bắt đầu phiên đo mới, chưa yêu cầu người dùng giữ tay.

Kế hoạch tiếp theo: [tìm nguyên nhân và cải thiện HR cổ tay](05-HR-ROOT-CAUSE-PLAN.md). Chưa kết luận không còn bất kỳ mã thừa nào bằng static scan; các phần đã xóa ở trên có bằng chứng cụ thể và kiểm hồi quy tương ứng.

## Đợt dọn ngày 15/11/2026

- Gỡ profile `PpgRate::Demo`, trạng thái trung vị/EMA riêng và script/harness thử Demo đã ngừng dùng. Bộ xử lý cửa sổ chuẩn vẫn cung cấp thông tin chất lượng.
- Gỡ hàm chọn HR dự phòng `freshHybrid` không còn bên gọi và script/harness chỉ kiểm hàm đó. Kiểm tích hợp hiện xác nhận worker chất lượng không ghi đè HR của bộ RR, không tự tạo HR khi tín hiệu phẳng hoặc mất tiếp xúc.
- Gỡ đoạn gán timestamp HR từ bộ cửa sổ trong `processRate`; HR được chọn duy nhất qua bộ RR.
- Bỏ đồng thời cột Demo khỏi bộ phát lại C++ và bộ đọc Python. Gỡ các lệnh kiểm đã lỗi thời khỏi CI; sửa thụt lề lệnh kiểm chất lượng đang dùng.
- Giữ giao diện, hằng số thuật toán HR hiện tại, cấu hình local, DB, raw và bộ dữ liệu tham chiếu. Giữ tài liệu lịch sử.

Kiểm chứng trong đợt này:

- Build firmware `esp32s3_supermini`: ĐẠT, RAM 130268 byte, flash 964005 byte.
- Bộ phân tích chất lượng, dải nhịp và hình dạng chu kỳ: ĐẠT 46 + 20 + 46 ca.
- Tích hợp RR chính, worker chất lượng và tự chỉnh LED: ĐẠT cả hai cấu hình native.
- Bộ cửa sổ chuẩn: ĐẠT 76 ca; không nhận HR ở 2400 cửa sổ chỉ có nhiễu.
- Toàn bộ bộ kiểm driver: CHƯA ĐẠT tại `HR step still locked to old RR/slow EMA`. Phép kiểm yêu cầu đáp ứng nhanh của bộ cửa sổ trước đây; bộ RR hiện tại chưa đáp ứng yêu cầu đó. Giữ nguyên lỗi, không bỏ qua hoặc đổi bộ làm mượt để lấy kết quả đạt.
- Chỉ build, chưa nạp ESP trong đợt dọn này. Chưa chạy CI GitHub, commit, push hoặc merge.

Xóa dữ liệu sinh ra bị cơ chế kiểm soát lệnh tự động chặn. Cả lệnh dọn đệ quy và lệnh thu hẹp chỉ xóa file đều bị từ chối. Chưa xóa file nào trong local storage. Danh sách nằm ở `backend/storage/local/cleanup-20261115-manifest.json`: 282 file, khoảng 6,84 MiB gồm log, file thực thi tạm, ứng viên C++ và bản sao nguồn thử cũ. Danh sách không gồm raw CSV, hồ sơ đo JSON/PNG, baseline đối chiếu hiện tại, bộ dữ liệu tham chiếu hay credential. Trạng thái: `inventory_only_not_deleted`.
