# Chạy local: mở web trước, kết nối thiết bị khi cần

`npm run dev` chỉ chuẩn bị broker/backend và mở Dashboard. ESP không cần cắm USB để mở trang. Trên web, chọn thiết bị đã đăng ký rồi bấm **Kết nối**; trạng thái chỉ chuyển thành **Đã kết nối** sau khi Dashboard nhận telemetry DEVICE mới của đúng thiết bị. Nếu quá15giây chưa có gói, trang báo nguyên nhân cần kiểm tra và cho phép thử lại.

**Ngắt kết nối** dừng riêng luồng theo dõi của trang này. Nó không gửi lệnh tới ESP, không ngắt Wi-Fi/MQTT và không dừng phiên tự động trên backend. Phiên vẫn được backend tạo/tiếp tục khi ESP đồng bộ như trước.

`npm run dev` không build hoặc nạp firmware. Khi đổi Wi-Fi, broker host/credential hoặc cần cập nhật firmware, cắm cáp USB truyền dữ liệu và chạy `npm run device:flash` ở thư mục gốc. Lệnh này đồng bộ cấu hình local, build firmware `esp32s3_supermini` và nạp đúng ESP32-S3 đang cắm. Mở web hằng ngày không cần USB.

Launcher vẫn tự đồng bộ IP broker khi địa chỉ cũ không còn trên laptop và chỉ tìm được một adapter LAN vật lý có gateway. Header local và Compose dùng IP mới; không chọn IP WSL/VMware/VPN. Nếu không xác định duy nhất được adapter, lệnh yêu cầu cấu hình IP thay vì đoán. Đổi Wi-Fi vẫn có thể cần sửa SSID/mật khẩu trong header rồi nạp lại firmware.

Thiết bị mới được đăng ký và cấu hình ở local, không thêm từ Dashboard. Mỗi ESP cần ID DEVICE cùng tài khoản MQTT/ACL riêng trong registry local, và firmware được nạp với đúng cấu hình. Sau khi đăng ký, thiết bị xuất hiện trong danh sách kể cả khi offline; xem [hướng dẫn thiết lập broker và thiết bị](04-SETUP.md). Trạng thái chỉ thành đã kết nối sau khi Dashboard nhận telemetry DEVICE mới.

# Chạy local bằng một lệnh trên máy Trung và Tân

**2026-11-11 — chọn và theo dõi thiết bị:** danh sách và trạng thái nằm trên cùng hàng; nút **Kết nối** là thao tác riêng, việc chọn không tự mở luồng live. Trạng thái online chỉ có bằng chứng khi WebSocket nhận telemetry DEVICE mới của thiết bị đang chọn. **Ngắt kết nối** chỉ đóng theo dõi ở Dashboard.
API `/api/v1/devices` có cả thiết bị đã đăng ký nhưng chưa gửi gói đầu tiên,
chỉ trả ID/nguồn/phiên bản/lần nhận telemetry cuối; không trả credential.
Dashboard chỉ đưa nguồn `DEVICE` vào ô chọn và nhận live; `SYNTHETIC` không xuất hiện.
Danh mục tải lại sẽ loại mục giả lập/cũ trong bộ nhớ lựa chọn. Công cụ giả lập của
backend vẫn dành cho kiểm thử, không được trình bày như thiết bị thật trên Dashboard.
Một thiết bị thì hiện sẵn tên và không cần mở chọn. Nhiều thiết bị thì ưu tiên
lựa chọn dùng gần đây nhất trên trình duyệt; nếu chưa lưu, chọn thiết bị có lần
nhận telemetry gần nhất ở backend. Không tự chuyển sang thiết bị khác khi có gói mới.
Launcher truyền ID đã cấu hình qua `VITE_DEFAULT_DEVICE_ID` để có tên dự phòng ngay
khi mở lần đầu; API bổ sung danh sách đầy đủ. Trình duyệt chỉ lưu ID/danh sách đã biết,
không lưu token hoặc số đo; nếu storage bị chặn vẫn xem/chọn được trong lượt mở trang.
Đổi thiết bị không trộn biểu đồ/phiên. Tên đã biết, thời gian last_seen hoặc danh mục
không làm trạng thái thành đã kết nối: phải có gói mới trên WebSocket hiện hành.

**2026-11-09 — bổ sung chất lượng:** firmware `0.3.27-tracker` dùng telemetry1.2,
thêm điểm cho bốn card; bộ HR vẫn như0.3.26. Chờ khoảng8–9giây để đủ cửa sổ thu mẫu.
Điểm là kiểm tra kỹ thuật, không phải phần trăm độ chính xác. [Công thức và giới hạn](../contracts/MEASUREMENT_QUALITY_V1_2.md).
Các bản firmware tiếp theo trong tài liệu là lịch sử.

**HR hiện tại, 2026-11-08:** bản thử `0.3.26-tracker`, thêm độ lặp hình dạng khi chọn chu kỳ và giữ lịch sử có giới hạn qua cửa sổ yếu; **chưa nghiệm thu HR cổ tay**. Lượt thật0.3.25 trước đó chưa đạt. Cấu hình vẫn LED10mA, chip200Hz/avg4, FIFO50Hz. Bản này có thể bỏ nhiều cửa sổ hơn thay vì phát một nhịp thiếu bằng chứng. Xem [bàn giao và giới hạn](05-HR-TRACK-SWITCH.md). Env mặc định `esp32s3_supermini` và alias `esp32s3_hr_tracker` cùng dùng bản này; các env thử cũ đã bỏ. `npm run dev` không tự nạp firmware.

Cập nhật2026-11-05. Yêu cầu mới của Trung thay bước đăng nhập DevTools: nối laptop/ESP cùng LAN, chạy `npm run dev`, mở localhost để nhận dữ liệu. MQTT Explorer là công cụ chẩn đoán tuỳ chọn, không phải broker và không bắt buộc.

## Cách hoạt động

### Dùng Wi-Fi quán qua hotspot laptop

Đã kiểm ngày 2026-11-07 trên máy Trung: laptop vẫn nhận Internet từ Wi-Fi quán và phát Mobile hotspot 2.4 GHz cho ESP. Không dùng data iPhone. ESP nối vào Wi-Fi do laptop phát; broker bind vào IPv4 của adapter hotspot, không dùng IP của laptop trên mạng quán. Đọc IP thực trước khi cấu hình, không mặc định mọi máy đều cùng địa chỉ.

Tên/mật khẩu hotspot và địa chỉ broker nằm trong `network_config.h` local đã được Git bỏ qua. Sau khi đổi các giá trị này phải nạp lại firmware. Không dùng tài khoản MQTT của backend cho ESP hoặc đưa mật khẩu hotspot vào tài liệu/Git.

Khi dùng hằng ngày, bật Mobile hotspot trước `npm run dev` để adapter/IP broker tồn tại. Nếu SSID, mật khẩu và IP hotspot giữ nguyên thì việc laptop đổi Wi-Fi đầu vào không tự yêu cầu nạp lại ESP. Nếu chúng thay đổi, kiểm và đồng bộ lại. Không tắt tường lửa hoặc mở broker trên mọi interface để né lỗi.

Lượt kiểm mạng này: bản đối chứng `0.3.13-led10`, chip 200 Hz/gộp 4/FIFO 50 Hz, MQTT và đồng bộ phiên thành công; WebSocket nhận 11 frame DEVICE có GSR và hai vector IMU. Chưa đặt cảm biến để đo HR, HR null không được diễn giải là lỗi thuật toán. Bằng chứng riêng trên máy Trung: `backend/storage/local/hr-hotspot-preflight-20261107-ws.json` và `hr-hotspot-upload-20261107.log`; chưa xác nhận trên máy Tân.

### Luồng launcher

- Lệnh từ root hoặc frontend dùng chung launcher, khởi động Docker broker/backend rồi Vite loopback5173. Launcher không build/nạp firmware.
- Chọn thiết bị và bấm **Kết nối** để mở WebSocket. Khi trang đóng hoặc bấm **Ngắt kết nối**, socket Dashboard dừng; ESP tiếp tục Wi-Fi/MQTT.
- Phiên theo dõi vẫn tự mở theo boot/đồng bộ ESP, độc lập thao tác Kết nối của Dashboard. F5/reconnect/chạy lại npm tiếp tục phiên phù hợp. Xem [phiên tự động](05-AUTOMATIC-SESSIONS.md).
- Cấu hình thiết bị lấy từ network_config.h local; Compose đồng bộ IP/cổng broker từ file này. Khi đổi Wi-Fi/host phải nạp lại firmware đã sửa.
- Mỗi máy tự tạo/reuse credential local, không đưa secret vào Git; lần tạo mới đồng bộ credential MQTT vào header local và thông báo cần nạp lại.
- Vite dev có bridge POST phiên local, chỉ nhận loopback với Host/Origin đúnglocalhost5173. Bridge đọc operator token phía Node, đổi lấy cookie HttpOnly qua backend; không trả token cho JS, không nới auth backend.
- React tự khởi tạo/gia hạn cookie trước khi mở Dashboard, có trạng thái chờ/lỗi và thử lại. Production không bật bridge này.
- Kiểm tra luồng cookie local → người dùng bấm **Kết nối** → WebSocket nhận frame DEVICE thật trên máy Trung. Máy Tân cần chạy cùng code với cấu hình/phần cứng thực; không tuyên bố đã kiểm thử từ xa.

## Dùng hằng ngày

HR hiện dùng bản thử `0.3.26-tracker`. Nét liền là HR thiết bị; nếu thiếu ngắn, FE có thể nối bằng nét đứt “Tạm tính” tối đa15giây, không điền dữ liệu gốc. Độ liền mạch không xác nhận nhịp đã đúng. Khi đổi Wi-Fi, sửa `network_config.h` local rồi nạp lại env mặc định hoặc `esp32s3_hr_tracker`.

ESP máy Trung đã quay về **0.3.13-led10**, LED10mA/chip200Hz/avg4/FIFO50Hz, làm đối chiếu. Bản400Hz/avg8/0.3.15 cũng chưa có HR ổn định; sau khôi phục, GSR/IMU vẫn truyền đủ. **HR cổ tay chưa nghiệm thu**, chưa chọn cấu hình tối ưu. [Kết quả và giới hạn](05-WRIST-SAMPLING-TRIAL.md), [các mức LED](05-WRIST-PROFILE.md). `npm run dev` không đổi hoặc tự nạp firmware; USB cần lúc nạp/log, dữ liệu Dashboard vẫn qua Wi-Fi/MQTT.

**Bản hiện tại: 0.3.12 trên máy Trung**, đã nạp bộ HR hybrid C++ để thử bước 4. Lệnh chạy, Wi-Fi và MQTT giữ nguyên. Chưa nghiệm thu HR cổ tay; xem [bằng chứng mới nhất](05-PPG-FIRMWARE-TRIAL.md). Các cập nhật phiên bản dưới là lịch sử.

Cập nhật mới nhất: board máy Trung đã nạp **0.3.11** để chẩn đoán lỗi I2C; bộ HR giữ như0.3.10. `npm run dev` và luồng MQTT không đổi. Xem [bước đang kiểm chứng](05-PPG-I2C-DIAGNOSIS.md); các mô tả phiên bản tiếp theo là lịch sử.

Cập nhật 2026-11-06: board máy Trung đã nạp **0.3.10**, sửa lỗi nhận nửa nhịp. Luồng chạy giữ nguyên; HR cổ tay chưa nghiệm thu. Xem [bằng chứng hiện tại](05-SENSOR-RECOVERY.md). Mô tả 0.3.9 tiếp theo là mốc trước.

Firmware0.3.9 đã nạp trên máy Trung: PPG chip200Hz/averaging4, FIFO vẫn50Hz; đánh giá tín hiệu yếu theo mức nhiễu và chọn IR/RED đủ điều kiện. HR cửa sổ8s, kiểm tra1s, cần hai lượt thống nhất; tiếp xúc mới cần khoảng13s trước kết quả đầu. Tín hiệu chưa đủ rõ vẫn để HR trống. Xem [tiến độ](05-WRIST-MEASUREMENT.md), [bằng chứng và giới hạn](05-SENSOR-RECOVERY.md). Không cần tháo/đổi dây. Sau nạp, giữ mạch yên vài giây để lấy lệch gyro. GSR vẫn hiển thị ADC; delta/µS chưa hiệu chuẩn để null. Chưa nghiệm thu HR cổ tay.

Mở Docker Desktop, kết nối laptop/ESP vào LAN đã cấu hình và bật ESP. Tại root repo hoặc thư mục frontend:

```powershell
npm run dev
```

Lệnh tự bật broker/backend, chờ healthy, chạy frontend và mở **http://localhost:5173**. Dashboard tự cấp cookie local nhưng chưa mở WebSocket thiết bị. Chọn thiết bị rồi bấm **Kết nối** để nhận telemetry; không cần nhập token, DevTools hay MQTT Explorer.

Phiên cũng tự mở khi ESP đồng bộ. Dashboard hiện mã AUTO-… theo thiết bị đã chọn. Phiên không bị dừng khi bấm Ngắt kết nối hoặc đóng frontend; đây chưa phải bộ raw hoàn chỉnh để xuất/train.

Sau khi bấm **Kết nối**, trang tự phục hồi WebSocket nếu mạng gián đoạn và giữ history đang xem; xem [kiểm tra thời gian thực](05-REALTIME-RECOVERY.md). Mở cookie local có timeout8 giây; WebSocket mở tối đa10 giây, socket im lặng được ping/pong rồi thử lại khi lỗi. Khi vừa mở Dashboard, WebSocket thiết bị vẫn đóng cho tới khi người dùng bấm **Kết nối**. Chờ dữ liệu trong lúc ESP chưa online vẫn là trạng thái đúng; heartbeat không thay số đo cảm biến. Không cần nạp lại ESP cho cập nhật này.

Giữ terminal đang chạy. Ctrl+C dừng frontend; broker/backend tiếp tục để không gián đoạn phiên thiết bị. Muốn dừng hai dịch vụ, chạy ở root:

```powershell
npm run dev:stop
```

Lệnh stop giữ dữ liệu/credential. Nếu5173 đang dùng, dừng phiên frontend cũ trước; launcher không tự chuyển5174 hoặc tắt ứng dụng khác.

## Cài lần đầu trên máy Tân hoặc máy mới

Cần Git, Node22+, Python3.12+ và Docker Desktop có Compose. MQTT Explorer chỉ là client xem/debug topic, không bắt buộc. Lần tải image/dependencies đầu cần Internet; các lần sau dùng bộ đã cài nếu source/package-lock không đổi.

Lấy nhánh `fix/esp32-local-mqtt-integration` sau khi được push. Kiểm tra git status trước khi chuyển nhánh và giữ code đang sửa nếu có. Chạy `npm run dev`; launcher tự cài frontend theo lockfile nếu thiếu/đã đổi, tạo bộ credential local khi chưa có rồi bật dịch vụ.

Nếu chưa có network_config.h, launcher tạo từ example, điền IP LAN/tài khoản MQTT DEVICE riêng. Mở header điền Wi-Fi, giữ các dòng MQTT được đồng bộ. Nạp ESP từ terminal khác. Cài PlatformIO một lần nếu máy chưa có:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install platformio==6.2.0 pyserial
npm run device:flash
```

`device:flash` build/nạp firmware một cách rõ ràng, không mở Dashboard. Khi chưa cài Python/PlatformIO, thực hiện các lệnh cài ở trên trước. Đóng Serial Monitor trước khi nạp.

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
