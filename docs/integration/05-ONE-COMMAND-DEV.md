# Chạy local bằng một lệnh trên máy Trung và Tân

Cập nhật2026-11-05. Yêu cầu mới của Trung thay bước đăng nhập DevTools: nối laptop/ESP cùng LAN, chạy `npm run dev`, mở localhost để nhận dữ liệu. MQTT Explorer là công cụ chẩn đoán tuỳ chọn, không phải broker và không bắt buộc.

## Cách hoạt động

- Lệnh từ root hoặc frontend dùng chung launcher, khởi động Docker broker/backend rồi Vite loopback5173.
- Cấu hình thiết bị lấy từ network_config.h local; Compose đồng bộ IP/cổng broker từ file này. Khi đổi Wi-Fi/host phải nạp lại firmware đã sửa.
- Mỗi máy tự tạo/reuse credential local, không đưa secret vào Git; lần tạo mới đồng bộ credential MQTT vào header local và thông báo cần nạp lại.
- Vite dev có bridge POST phiên local, chỉ nhận loopback với Host/Origin đúnglocalhost5173. Bridge đọc operator token phía Node, đổi lấy cookie HttpOnly qua backend; không trả token cho JS, không nới auth backend.
- React tự khởi tạo/gia hạn cookie trước khi mở Dashboard, có trạng thái chờ/lỗi và thử lại. Production không bật bridge này.
- Kiểm tra cả luồng tự động cookie→WS bằng frame DEVICE thật trên máy Trung. Máy Tân cần chạy cùng code với cấu hình/phần cứng thực; không tuyên bố đã kiểm thử từ xa.

## Dùng hằng ngày

Mở Docker Desktop, kết nối laptop/ESP vào LAN đã cấu hình và bật ESP. Tại root repo hoặc thư mục frontend:

```powershell
npm run dev
```

Lệnh tự bật broker/backend, chờ healthy, chạy frontend và mở **http://localhost:5173**. Dashboard tự cấp cookie và nhận dữ liệu; không cần nhập token, DevTools hay MQTT Explorer.

Giữ terminal đang chạy. Ctrl+C dừng frontend; broker/backend tiếp tục để không gián đoạn phiên thiết bị. Muốn dừng hai dịch vụ, chạy ở root:

```powershell
npm run dev:stop
```

Lệnh stop giữ dữ liệu/credential. Nếu5173 đang dùng, dừng phiên frontend cũ trước; launcher không tự chuyển5174 hoặc tắt ứng dụng khác.

## Cài lần đầu trên máy Tân hoặc máy mới

Cần Git, Node22+, Python3.12+ và Docker Desktop có Compose. MQTT Explorer chỉ là client xem/debug topic, không bắt buộc. Lần tải image/dependencies đầu cần Internet; các lần sau dùng bộ đã cài nếu source/package-lock không đổi.

Lấy nhánh `fix/esp32-local-mqtt-integration` sau khi được push. Kiểm tra git status trước khi chuyển nhánh và giữ code đang sửa nếu có. Chạy npm run dev; launcher tự cài frontend theo lockfile nếu thiếu/đã đổi, tạo bộ credential khi chưa có rồi bật dịch vụ.

Nếu chưa có network_config.h, launcher tạo từ example, điền IP LAN/tài khoản MQTT DEVICE riêng. Mở header điền Wi-Fi, giữ các dòng MQTT được đồng bộ. Nạp ESP từ terminal khác. Cài PlatformIO một lần nếu máy chưa có:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install platformio==6.2.0
.\.venv\Scripts\python.exe -m platformio device list
# COM7 là ví dụ; thay bằng cổng ESP thực trên máy đó.
.\.venv\Scripts\python.exe -m platformio run -d ai/edge_firmware -e esp32s3_supermini -t upload --upload-port COM7
```

Không tạo lại .venv đang dùng. Env esp32s3_network_check chỉ build, không dùng để kết nối thật. Đối chiếu GPIO/board trước khi nạp theo05-LOCAL-BRINGUP.md.

## Đổi Wi-Fi hoặc chuyển ESP sang laptop khác

Sửa file ai/edge_firmware/include/network_config.h local:

```cpp
#define WIFI_SSID "TEN_WIFI"
#define WIFI_PASSWORD "MAT_KHAU_WIFI"
#define MQTT_BROKER_HOST "IP_LAN_CUA_LAPTOP_CHAY_BROKER"
#define MQTT_BROKER_PORT 1883
```

Lấy IPv4 adapter Wi-Fi bằng Get-NetIPConfiguration. Host phải là IP laptop, không phải router/iPhone/ESP. Với iPhone bật Tăng tối đa khả năng tương thích; 5G di động khác Wi-Fi5 GHz.

Chạy lại npm run dev để Compose dùng IP/cổng mới, rồi **nạp lại ESP** từ header đã sửa. Chỉ sửa file trên laptop không thay firmware trong board. Stop phiên ghi trước khi đổi mạng/nạp lại.

Mỗi máy có bộ local/DB/tài khoản riêng. Chuyển ESP sang máy kia cần dùng header và nạp từ máy đó vì IP/credential broker có thể khác. Không copy secret vào Git. Đây là mỗi máy chạy môi trường riêng, không phải2 broker cùng nhận một ESP đồng thời.

## Cấu hình được quản lý

- Header local giữ SSID/password Wi-Fi người dùng điền; launcher đồng bộ ID/credential MQTT theo bộ local và không in secret.
- .env root đồng bộ Compose project, thư mục local, IP/cổng từ header. App bind loopback.
- infra/mosquitto/local/ chứa registry/ACL/credential và cache. Reuse khi chạy lại; cấu hình dở hoặc identity khác thì báo lỗi, không ghi đè.
- Git bỏ qua cả3 đường trên. Máy Trung dùng bộ esp32-trung; máy mới mặc định dev.
- Khi MQTT timeout, kiểm tra IP/cổng, firewall đúng adapter/LAN và client isolation. Launcher không tắt firewall hoặc mở toàn mạng; cùng SSID chưa tự là bằng chứng thông kết nối.

Bridge chỉ có ở Vite dev localhost; token nằm trong Node, browser chỉ nhận cookie HttpOnly. Backend vẫn kiểm tra quyền/phiên/schema. Không bật bypass theo Origin/token URL; build/serve production không có bridge này. Chỉ cây frontend được Vite phục vụ, cấu hình private bị chặn.

## Kết quả và giới hạn

- [x] Helper chuẩn bị local và launcher chung root/frontend.
- [x] Bridge localhost và tự mở/gia hạn phiên trong App, có retry.
- [x] Tests bridge, cấu hình/reuse/đổi IP và hồi quy backend/frontend: backend77, frontend41 đạt.
- [x] Chạy thật cả2 entry và stop/start trên máy Trung; client không đọc token lấy cookie rồi nhận3 frame DEVICE thật qua WS, cả sau restart. Origin ngoài bị403, file private bị403/404. Lần chạy lại dùng cache, không build lại backend.
- [x] Build TypeScript/Vite, audit và kiểm tra token không có trong bundle; Vite pin8.3.6 sửa advisory của8.3.2.
- [x] Hướng dẫn một cách chạy cho cả hai máy; không cần DevTools.
- [ ] UI trực quan: browser tool không khả dụng; tests DOM không thay xác nhận hiển thị thật của người dùng.
- [ ] Chạy trực tiếp máy Tân: chưa truy cập máy; helper đã thử bằng checkout giả lập mới/reuse/đổi IP. Tân cần cùng code và phần cứng/cấu hình thực.

Nhánh05 vẫn còn Start/Stop, các ca lỗi và bài đo hiệu năng, gồm spike loopGap106 ms. Không đánh DONE toàn nhánh chỉ từ luồng live.
