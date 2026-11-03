# Prompt giao Tân triển khai nhánh 5

Soạn ngày 2026-11-02, đối chiếu repo tại dev `7ff5a2c` sau PR #13. Đây là hướng dẫn giao việc, không phải bằng chứng nhánh 5 đã triển khai. Tân gửi **toàn bộ phần bên dưới** cho AI có quyền đọc/sửa bản clone ASD-EASE trên máy mình. Không cần gửi mật khẩu/token trong hội thoại; AI phải đọc đúng repo trước khi viết code.

---

Bạn là kỹ sư firmware ESP32/Arduino/PlatformIO và kỹ sư tích hợp MQTT. Hãy cùng tôi triển khai hoàn chỉnh **nhánh 5 của ASD-EASE** trên repo hiện có. Tôi là **Tân**, phụ trách phần cứng/firmware của nhóm; **Trung** là chủ repo, phụ trách backend/frontend và review PR.

Hãy thực sự đọc repo, viết code, chạy kiểm thử và bàn giao. Không dừng ở đề xuất kiến trúc hoặc trả một đoạn code mẫu rời rạc. Làm theo các mốc bên dưới, ghi tiến độ để có thể tiếp tục sau khi hội thoại dài. Không giả vờ đã chạy lệnh, đã có phần cứng hoặc đã thấy Dashboard hoạt động.

## 1. Mục tiêu và ranh giới công việc

Nhánh phải có tên:

```text
feature/firmware-telemetry-client
```

Luồng dữ liệu cần hoàn thành:

```text
Cảm biến thật trên ESP32
  → Wi-Fi LAN
  → Broker MQTT trên laptop
  → Backend FastAPI
  → WebSocket
  → Dashboard React hiện tại ở http://localhost:5173
```

Luồng điều khiển:

```text
Yêu cầu Start/Stop qua API backend
  → lưu phiên/lệnh trong DB
  → MQTT command
  → ESP32 thực thi
  → MQTT ACK + đồng bộ trạng thái
  → backend cập nhật trạng thái phiên
```

Mục tiêu không chỉ là publish một gói JSON lên broker. Phải chứng minh dữ liệu cảm biến thật đi hết tới Dashboard và Start/Stop/ACK/reconnect đúng đặc tả.

Trong nhánh 5:

- Triển khai Wi-Fi, MQTT, đóng telemetry, đồng bộ, nhận lệnh và ACK trên ESP32.
- Giữ việc đọc cảm biến độc lập với việc mạng có hoạt động hay không.
- Giữ Serial để chẩn đoán; USB chỉ dùng nạp/log, không làm kênh truyền dữ liệu tới Dashboard thay MQTT.
- Có chế độ networking tắt để build CI và dùng Serial-only.
- Chỉ sửa phần hỗ trợ cấu hình LAN/đăng ký thiết bị bên backend khi thật sự cần, phạm vi nhỏ và có giải thích.

Không mở rộng sang:

- Nhánh 6: backend lưu raw bền/JCS/chống trùng/đối chiếu đủ dữ liệu.
- Nhánh 7: firmware gom raw theo lô, hàng đợi raw và gửi HTTP.
- Nhánh 8–9: xuất dữ liệu, giao diện điều khiển ghi hoàn chỉnh.
- Huấn luyện/tạo mô hình AI hoặc tự suy luận trạng thái trên laptop.
- Thiết kế lại Dashboard hoặc thay thuật toán cảm biến hàng loạt.

Live telemetry không đồng nghĩa đã bắt đầu phiên ghi. Sau đồng bộ, ESP32 có thể gửi telemetry ngoài phiên với session_id=null theo đặc tả. Start/Stop là mốc nghiệm thu riêng, vẫn phải hoàn thành.

## 2. Đọc repo và xác nhận điểm xuất phát

Trước khi sửa, tìm và đọc AGENTS.md/SKILL.md áp dụng tại repo. Tự xác định hệ điều hành, thư mục gốc, công cụ và phiên bản thực tế. Không giả định máy tôi có đường dẫn giống máy Trung.

Đọc ít nhất các tài liệu sau theo thứ tự:

1. `docs/integration/05-firmware-telemetry-client.md`.
2. `docs/API_CONTRACT.md`.
3. `docs/contracts/INGESTION_V1.md`.
4. `docs/contracts/MQTT_CONTROL.md`.
5. `docs/contracts/DRIVER_MAPPING.md`.
6. `docs/contracts/examples.json` và công cụ kiểm tra mẫu đi kèm.
7. `docs/integration/04-SETUP.md`, `04-HANDOFF.md`.
8. `docs/integration/MQTT_ARCHITECTURE.md`, `PROGRESS.md`.
9. `docs/HARDWARE_PROFILE.md`, `docs/GIT_WORKFLOW.md`.
10. `docs/phases/PHASE_07_WIFI_BACKEND.md`.

Đọc code thực thi, không chỉ dựa vào tài liệu:

- `ai/edge_firmware/platformio.ini`.
- `ai/edge_firmware/src/main.cpp`.
- Header và implementation MAX30102, MPU6050, GSR, EMA, HardwareProfiler.
- `board_config.h`, `common_types.h`, `interfaces.h`, `pins.h`, `sensor_config.h`, `network_config.example.h`.
- `backend/app/schemas/ingestion.py`: bộ kiểm tra telemetry thực tế.
- `backend/app/schemas/control.py`: bộ kiểm tra điều khiển thực tế.
- `backend/app/services/control_service.py`, `mqtt_runtime.py`, `session_service.py`, `telemetry_service.py`.
- `backend/app/core/security.py`, `config.py`.
- `ai/simulator/mqtt_device.py`: đối chiếu luồng giả lập đã chạy, không sao chép như firmware production.
- `scripts/setup_local_mqtt.py`, `scripts/check_mqtt_integration.py`.
- `compose.yaml`, `infra/mosquitto/`, `.github/workflows/ci.yml`.
- Phần nhận dữ liệu hiện tại ở frontend: types, parser, `useLiveTelemetry.ts`, `Dashboard.tsx`.

Mốc đã biết: nhánh 4 merge PR #13 vào dev tại `7ff5a2c`, có backend MQTT, registry/ACL/xác thực, quản lý phiên và simulator. CI PR và CI dev tại mốc đó đều đạt 6/6. Đây là bằng chứng lịch sử, không thay CI của commit bạn chuẩn bị tạo.

Nhánh 3 là đặc tả, nhánh 4 là backend. Không nhầm số nhánh với số phase: phase 03 là MAX30102.

Nếu repo mới hơn mốc này, đọc diff liên quan và sử dụng phiên bản hiện tại. Nếu code và tài liệu khác nhau, nêu rõ khác biệt và đề xuất sửa tối thiểu với Trung; không âm thầm đổi protocol hoặc nới backend cho gói sai được nhận.

Sau khi đọc, báo ngắn:

- Repo/branch/SHA hiện tại.
- Backend và firmware đang có gì, còn thiếu gì.
- Danh sách file dự kiến sửa/tạo.
- Các thông tin phần cứng/cấu hình thật cần tôi cung cấp.

Tiếp tục những phần không phụ thuộc câu trả lời trong lúc chờ. Không yêu cầu tôi gửi lại thông tin đã có trong repo. Chưa cần mật khẩu/token trong chat.

## 3. Quy trình Git và bảo vệ code đang có

Kiểm tra `git status`, merge/rebase dở và nhánh hiện tại trước mọi thao tác. Không reset --hard, git clean, force-push, xoá stash hoặc ghi đè thay đổi của người khác.

Luồng chuẩn khi working tree phù hợp:

```powershell
git status
git fetch origin
git switch dev
git pull --ff-only origin dev
git switch -c feature/firmware-telemetry-client
```

Nếu nhánh 5 đã tồn tại, kiểm tra rồi tiếp tục đúng nhánh; không tạo nhánh trùng hoặc bắt đầu lại. Nếu có thay đổi chưa commit, giữ nguyên và cô lập công việc bằng worktree khi cần; báo rõ vị trí. Không trộn thay đổi của người khác vào commit của mình.

Không code trực tiếp trên dev/main. Không push trực tiếp dev/main. Không tạo PR vào main.

Tôi được triển khai nhánh 5 theo phân công mới của Trung trong prompt này; bảng phân công cũ trong docs có thể vẫn ghi Trung chủ trì/Tân hỗ trợ. Chỉ cập nhật mô tả nhánh 5 cho đúng, không tự chuyển quyền repo hoặc đổi phân công các nhánh khác.

## 4. Xác nhận phần cứng trước nghiệm thu thật

Đối chiếu bo mạch, dây và log thật; không suy board/flash/PSRAM từ tên môi trường PlatformIO.

Code tại mốc đã đọc có cấu hình:

- ESP32-S3, Arduino, PlatformIO env `esp32s3_supermini`.
- Board build tạm `esp32-s3-devkitc-1`, flash cấu hình 4 MB; chưa chứng minh phần cứng thực tế.
- MAX30102 SDA8/SCL9; MPU6050 SDA10/SCL11; GSR ADC7.
- PPG chip100 Hz, averaging2 → FIFO50 Hz danh định; IMU50 Hz; GSR20 Hz.
- Loop mục tiêu10 ms; telemetry mục tiêu1000 ms.

Các giá trị này phải đọc lại trong repo hiện tại, không tự đổi GPIO theo thói quen. Hỏi tôi xác nhận ảnh/sơ đồ dây/log nhận dạng nếu thiếu. Khi có công cụ và board, đo tốc độ/số mẫu/khoảng trống trước và sau khi bật mạng. Không ghi “đã đo50 Hz” chỉ vì hằng số là50.

Chỉ sửa driver tối thiểu để bổ sung cờ mẫu mới/timestamp/trạng thái cần thiết. Không thay bộ lọc/ngưỡng/hiệu chuẩn để làm số liệu đẹp hơn. Ghi rõ thay đổi driver và tác động.

## 5. Kiến trúc firmware và chọn thư viện

Tách trách nhiệm, có thể đặt module trong:

```text
ai/edge_firmware/include/communication/
ai/edge_firmware/src/communication/
```

Tên file/lớp do bạn quyết định sau khi đọc code, nhưng phải có trách nhiệm rõ:

- Cấu hình mạng và bật/tắt transport.
- Wi-Fi manager/reconnect.
- MQTT client, callback và hàng đợi hữu hạn.
- Đồng hồ boot/epoch phiên.
- Máy trạng thái phiên và kiểm tra lệnh.
- Snapshot nhất quán của cảm biến, freshness và mapping.
- Telemetry serializer, control parser/serializer.
- Thống kê mạng, độ trễ, hàng đợi và tài nguyên.

Sửa main.cpp ở các điểm tích hợp cần thiết, giữ các driver/chế độ chẩn đoán hiện có.

Trước khi chọn thư viện MQTT:

1. Đọc tài liệu chính thức/mã nguồn tương ứng phiên bản, kiểm tra tương thích Arduino/framework đang dùng.
2. Chứng minh thư viện **publish QoS1 được**, không chỉ subscribe QoS1.
3. Kiểm tra clean session, SUBACK, PUBACK, LWT, TLS, giới hạn buffer và hành vi reconnect/offline queue.
4. Chạy ví dụ tối thiểu qua broker thật, rồi mới tích hợp vào lịch lấy mẫu.
5. Pin phiên bản dependency mới; ghi lý do chọn và bằng chứng. Không nâng toàn bộ dependencies không liên quan.

Mạng phải chạy ở task/lịch riêng thích hợp. Không chờ Wi-Fi, DNS, MQTT connect hoặc PUBACK trong vòng đọc cảm biến10 ms. Có timeout, retry có giới hạn, ưu tiên task hợp lý và shutdown/reconnect sạch.

Callback chỉ kiểm tra kích thước/copy gói vào hàng đợi, không chạy xử lý nặng hoặc chặn lấy mẫu. Snapshot liên task phải copy giá trị nhất quán, có đồng bộ; không giữ con trỏ vào vùng dữ liệu đang bị sửa.

Đo thời gian thật. Không gọi “non-blocking” chỉ vì dùng callback hoặc delay ngắn. Theo dõi heap thấp nhất, block cấp phát, stack watermark, queue byte/count, loop gap và số lần mất mẫu; xác nhận đơn vị của API đo theo framework. Không giả board có PSRAM.

## 6. Cấu hình và kết nối LAN đúng

Phân biệt ba địa chỉ:

```text
ESP32: broker = IP LAN laptop, cổng MQTT
Backend container: broker = tên service broker trong mạng Compose
Browser laptop: frontend localhost:5173, API localhost:8000, WS tương ứng
```

ESP32 không dùng localhost/127.0.0.1 hoặc hostname service Docker để trỏ laptop. Browser cũng không kết nối MQTT trực tiếp.

Điểm cần xử lý thật: compose.yaml ở mốc nhánh 4 publish broker trên `127.0.0.1:1883`. ESP32 ngoài laptop không truy cập được địa chỉ này. Tạo cách cấu hình LAN bằng biến môi trường/override phù hợp, mặc định vẫn loopback. Không commit IP riêng của máy. Kiểm tra port mapping thực, tránh cách merge override vô tình mở thêm listener trên mọi interface.

Xác nhận:

- Laptop và ESP32 ở mạng có thể truy cập nhau; kiểm tra Wi-Fi/AP isolation/VPN khi cần.
- Docker Desktop đang chạy và port mapping đúng IP LAN laptop.
- Broker có credential/ACL thiết bị thật.
- Backend dùng registry đúng, MQTT connected.
- Browser dùng backend/WS hiện tại, không mở nhầm frontend dự án khác trên5173.

Nếu cần tường lửa, chỉ hướng dẫn/quy tắc cho cổng, profile Private và phạm vi thiết bị/LAN cần thiết; không tắt tường lửa toàn máy, không mở Internet hoặc dùng public broker để né lỗi LAN. Thao tác cần quyền quản trị máy phải giải thích và để tôi xác nhận.

Cấu hình local cần có Wi-Fi SSID/password, device_id, MQTT host/port/client ID/username/password, lựa chọn TLS/CA; giữ phần HTTP host/port riêng cho nhánh7. Có networking enabled flag.

`network_config.h` là file local. Xác nhận bằng `git check-ignore -v` và `git ls-files`, không chỉ tin comment. Mở rộng file example bằng placeholder, CI build không cần secret và không cần file local. Không commit credential vào mã nguồn, fixture, image, log hoặc PR.

Không in toàn bộ `.env`, registry hoặc output `docker compose config` có chứa secret. Dùng `docker compose config --quiet` khi chỉ kiểm tra cấu hình.

Ngoài LAN phát triển riêng phải dùng TLS có kiểm tra CA/hostname; không tắt kiểm tra chứng chỉ. Nếu demo dùng TCP1883 trên LAN riêng, ghi rõ đây là ngoại lệ plaintext, không gọi là mã hoá.

## 7. Đăng ký thiết bị thật và quyền MQTT

Tool setup hiện sinh SIM-001/SIM-OTHER nguồn SYNTHETIC, với profile giả lập100/50/20. **Không lấy nguyên tài khoản/profile giả lập gắn cho board rồi đổi nhãn thành DEVICE.**

Chuẩn bị identity riêng, ví dụ `ESP32-001`, thống nhất trong cấu hình firmware, registry, topic, payload và ACL:

- data_origin=DEVICE.
- transport=mqtt.
- mqtt_username riêng, không dùng tài khoản backend.
- HTTP token riêng trong registry theo schema hiện có, không dùng OPERATOR_TOKEN; token raw dành nhánh7, không tự gửi telemetry HTTP song song.
- acquisition_profile theo cấu hình thiết bị;50/50/20 là danh định hiện tại, không phải100/50/20 của simulator.

Tạo mật khẩu ngẫu nhiên/nhập local, lưu băm cho broker. Không ghi đè thư mục cấu hình đang dùng hoặc xoá account simulator. Nếu helper hiện tại chưa hỗ trợ thêm DEVICE, thực hiện cấu hình local có hướng dẫn hoặc bổ sung tối thiểu helper theo convention, có kiểm thử, không xây hệ quản trị tài khoản mới.

Tiền tố topic:

```text
asd-ease/v1/DEVICE/ESP32-001/
```

| Suffix | Hướng | QoS | Retain |
|---|---|---|---|
| telemetry | ESP32 → backend | 0 | false |
| command | backend → ESP32 | 1 | false |
| ack | ESP32 → backend | 1 | false |
| state/request | ESP32 → backend | 1 | false |
| state/response | backend → ESP32 | 1 | false |
| presence | ESP32/LWT → backend | 1 | true |

Thiết bị chỉ publish4 topic của mình, chỉ subscribe command/state-response của mình. Backend có quyền đối ứng. Không dùng wildcard readwrite cho toàn repo hoặc disable auth để test xanh.

## 8. Telemetry phải đúng dữ liệu và schema

Không gửi nguyên Pretty JSON chẩn đoán của main.cpp. Tạo serializer riêng; dữ liệu gửi qua MQTT phải được kiểm tra bằng **InboundTelemetry trong schemas/ingestion.py**, không chỉ Telemetry tương thích trong schemas/telemetry.py.

Ví dụ cấu trúc hợp lệ dưới đây chỉ minh hoạ; các số không được dùng thay cảm biến thật:

```json
{
  "schema_version": "1.0",
  "device_id": "ESP32-001",
  "session_id": null,
  "timestamp_ms": 12000,
  "data_origin": "DEVICE",
  "hr_bpm": null,
  "gsr": {"raw": 1800, "delta": null},
  "movement": {"score": null},
  "signal_quality": {"ppg": 0, "gsr": 0, "imu": 0},
  "prediction": {"probability": null, "state": "UNCERTAIN"},
  "firmware_version": "0.2.0",
  "model_version": "none"
}
```

Firmware version lấy từ bản build thật, không hardcode theo ví dụ. Khi có phiên, session_id là ID backend cấp qua command, không tự tạo một ID khác trên ESP32.

Quy tắc bắt buộc:

- ID1–64 ký tự theo `^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$`.
- Không thêm boot_id/connection_id/status/debug/SpO2/trục IMU vào telemetry1.0. Các thông tin đó thuộc control hoặc Serial; đổi schema phải thảo luận riêng.
- JSON object UTF-8, không khoá lặp, không trường ngoài schema; null là JSON null, không chuỗi "null".
- Không NaN/Infinity, chuỗi giả số, bool thay số hoặc số thực thay trường nguyên. Timestamp/counter không vượt2^53-1.
- hr_bpm: chỉ có giá trị khi driver xác nhận hợp lệ, hữu hạn20..240 và còn mới. Sentinel0/lỗi/cũ dùng null; không clamp số hỏng cho hợp lệ.
- GSR raw: ADC nguyên0..4095, trung bình8 lần theo driver, trước EMA; không thay bằng điện áp/độ dẫn.
- GSR delta: percentChange/100 khi valid/còn mới và baselineConductance_uS>0.05; không đưa deltaConductance_uS vào trường tỷ lệ.
- movement.score chưa có thuật toán định nghĩa0..1 thì null. Không lấy accelMagnitude m/s² làm score hoặc clamp vào0..1.
- Chưa có mô hình: model_version="none", probability=null. GSR/IMU đang CALIBRATING → CALIBRATING; còn lại UNCERTAIN. VALID không tự thành NORMAL/ATTENTION.
- Chưa có bộ ước lượng chất lượng thì cả3 quality=0 theo quy ước bảo thủ. Không gán0.9/1 cho đẹp; ghi rõ0 này là chưa chứng minh chất lượng, không phải phép đo chất lượng.
- TTL phát triển: HR3000 ms từ nhịp/cập nhật hợp lệ thực; GSR/IMU1000 ms từ phép đọc mới thành công.
- Gọi read() rồi nhận cache không chứng minh có mẫu mới. Thêm timestamp/sequence nội bộ từ đúng điểm driver cập nhật; nếu không xác định được tuổi thì để trường liên quan null.
- Không đảo lại trục IMU Y/Z driver đã đảo; giữ đơn vị hiện tại trong log. Nhánh5 chưa gửi các trục raw lên API.

Nhịp telemetry mặc định1000 ms, độc lập sensing. Chỉ giữ snapshot mới nhất, không gom backlog telemetry để xả khi reconnect; dữ liệu cũ không được làm Dashboard live trở lại.

Dashboard hiện có HR/GSR/movement/probability. Với movement/probability null, phần đó có thể không có đường biểu đồ — đây là kết quả đúng. Không tạo số để mọi biểu đồ chuyển động. Kiểm tra IMU bằng log/mẫu kiểm thử đúng phạm vi, không tự thêm chart/schema.

## 9. Đồng hồ, phiên và vòng đời control

Đọc các trường chính xác trong control.py và MQTT_CONTROL.md, không tự rút gọn gói vì phần dưới chỉ nhấn mạnh logic.

### ID và thời gian

- boot_id mới mỗi lần reboot, giữ qua reconnect cùng boot.
- connection_id mới trước mỗi MQTT CONNECT/reconnect; LWT phải chứa nonce của kết nối sắp mở, không nonce cũ.
- request_id mới cho mỗi lượt STATE_REQUEST; command_id do backend cấp, generation tăng theo thiết bị.
- Đồng hồ boot/epoch dùng monotonic64 bit hoặc rollover handling đúng. Không dùng giờ UTC chưa đồng bộ làm sample timestamp.
- Ngoài phiên: timestamp_ms từ boot. START thực thi: đặt epoch trước mẫu đầu, chỉ một lần. Trong phiên: timestamp_ms từ epoch đó.
- Mất Wi-Fi/broker/backend, gửi lặp hoặc đồng bộ định kỳ không đặt lại epoch. Không gửi timestamp0 vào phiên cũ sau reboot.
- Đổi boot/phiên và quay lại telemetry ngoài phiên phải giữ phân tách mốc, không lẫn cursor/thời gian.

### Khi kết nối

```text
Wi-Fi sẵn sàng
→ chọn connection_id và khai báo LWT OFFLINE trước CONNECT
→ MQTT CONNECT với clean session
→ subscribe command + state/response
→ đợi SUBACK thành công
→ STATE_REQUEST
→ kiểm tra STATE_RESPONSE đúng device/origin/boot/connection/request
→ mới cho telemetry/lệnh theo trạng thái đã xác nhận
```

STATE_REQUEST hỏi lại mỗi15 s kể cả broker vẫn online, vì backend có thể đã restart. Giữ timestamp gửi request bằng monotonic để kiểm tra lease.

Chưa đồng bộ không tự Start, không tự gán session và không gửi telemetry theo phiên chưa được xác nhận. Presence retained chỉ là gợi ý, không bằng chứng live hoặc RECORDING.

### Khi nhận command START

1. Kiểm tra kích thước, JSON/schema, danh tính, boot/connection/request, action/session/generation/profile/thời hạn.
2. Command có thể tới topic command hoặc nằm trong pending_command của STATE_RESPONSE; phải dùng chung bộ xử lý, chống thực thi hai lần.
3. START phải có profile đúng thiết bị hỗ trợ; STOP có profile=null. Sai thì ACK REJECTED với mã phù hợp, không âm thầm đổi rate.
4. Tính lease từ lúc gửi STATE_REQUEST tương ứng; expires_in_ms1..30000. Gói lặp không gia hạn. Không lấy lúc nhận command làm mốc mới.
5. Nếu là Start mới hợp lệ, đặt epoch/phiên và thực thi một lần; tạo ACK STARTED với timestamp_ms=0, reason=null, final_summary=null.
6. Gửi ACK QoS1, rồi STATE_REQUEST có last_ack để backend lưu/xác nhận. Chỉ khi accepted_command_id/state/session phù hợp và không có error mới gửi telemetry theo phiên.
7. Trong lúc đợi xác nhận vẫn xử lý STOP, timeout và reconnect, không chờ vô hạn.

PUBACK chỉ là ACK truyền tải; không thay ACK đã thực thi hoặc STATE_RESPONSE xác nhận backend đã lưu.

### Lặp, nonce và reconnect

- Cùng command ID/generation/action/session/profile trong cùng boot: trả lại kết quả cũ, không chạy lại/reset epoch.
- Cùng command ID nhưng nội dung nghiệp vụ khác → COMMAND_CONFLICT; generation cũ → STALE_COMMAND. Bộ so sánh phải gồm profile khi liên quan.
- Lệnh retained, sai boot/kết nối/request hoặc hết lease không được chạy.
- Backend hiện kiểm tra ACK request_id phải là nonce đã được đồng bộ hiện hành, trong cửa sổ hợp lệ. Tránh nhiều lượt sync chồng nhau làm ACK mang nonce cũ bị từ chối.
- Khi gửi lại last_ack trong STATE_REQUEST mới/reconnect, bọc bằng connection_id/request_id hiện hành theo code backend; giữ command/generation/action/session/result/timestamp/reason/summary của kết quả đã thực thi.
- Không sửa cutoff/counts của cùng một ACK khi thử lại; backend có thể trả ACK_CONFLICT.
- Giữ hàng chờ/ACK hữu hạn; không dựa broker phát lại lệnh offline. Kiểm tra cả hàng đợi reconnect nội bộ của thư viện.
- Nếu gặp lỗi protocol thực tế, ghi payload đã che secret/counter/log và báo chính xác; không xoá DB hoặc đổi generation để né.

### Stop và giới hạn nhánh5

- STOP generation cao hơn có thể thay START đang chờ.
- ACK START đến muộn không được làm thiết bị/backend quay từ ý định Stop về ghi tiếp.
- Stop dừng **phiên ghi**, không nhất thiết tắt cảm biến/chẩn đoán. Có thể về live ngoài phiên khi đồng bộ phù hợp; không gửi tiếp session đã đóng.
- Thực hiện Stop rồi mới ACK STOPPED, không ACK trước thao tác thực tế.
- Nhánh5 chưa ghi raw: dùng summary zero-batch/raw_recording_enabled=false theo backend hiện tại. Cấu trúc điển hình:

```json
{
  "cutoff_timestamp_ms": 0,
  "final_batch_id": null,
  "total_generated_batches": 0,
  "dropped_batches": 0,
  "slot_counts": {"ppg": 0, "imu": 0, "gsr": 0},
  "missing_samples": {"ppg": 0, "imu": 0, "gsr": 0},
  "dropped_batch_ranges": [],
  "loss_ranges_truncated": false,
  "raw_recording_enabled": false
}
```

Trong chế độ này ACK STOPPED.timestamp_ms phải khớp cutoff0 để qua schema hiện tại. Đây là quy ước không có timeline raw, không phải tuyên bố Stop xảy ra ngay lúc Start. Ghi thời gian/độ trễ Stop thật riêng trong log; không tự đặt raw cutoff khác0 hoặc raw_recording_enabled=true cho có dữ liệu.

Backend có thể báo STOPPED nhưng recording_complete=false/RAW_RECORDING_DISABLED: đó là kết quả mong đợi của nhánh5. Không sửa backend để giả complete=true. Nếu cần thay đổi biểu diễn thời gian telemetry-only, nêu đề xuất riêng cho Trung, không âm thầm đổi protocol.

## 10. Giới hạn mạng và tài nguyên

- JSON telemetry/control tối đa4096 byte; topic tối đa256 byte UTF-8. Buffer MQTT phải tính thêm topic/header và kiểm tra kết quả serialize/publish.
- Telemetry latest-only, tối đa1 snapshot chờ.
- Control tối đa8 gói và32768 byte đang gửi/chờ; một lệnh hiện hành mỗi thiết bị. Bộ nhớ serializer/task stack tính riêng.
- Keepalive15 s; lease/chờ ACK nghiệp vụ tối đa30 s theo đặc tả.
- Reconnect backoff1,2,4,8,16,30 s, jitter tối đa20%, reset sau thành công; log có giới hạn, không tight-loop.
- Phân biệt mất Wi-Fi, broker từ chối, backend chưa sync/không ACK, schema sai và quá tải.
- Không retry vô hạn gói sai/cấu hình sai; retry transport không đổi ID nghiệp vụ hoặc tự gia hạn lệnh.
- Không chờ PUBACK ở task sensing; nếu thư viện có thao tác đồng bộ phải cô lập, đo và giới hạn thời gian.
- Chừa tài nguyên cho HTTP raw của07. Không tự thêm lưu flash/NVS để che mất dữ liệu nếu chưa có thiết kế.

## 11. Cách triển khai theo mốc

Tạo/cập nhật file theo dõi như `docs/integration/05-IMPLEMENTATION-LOG.md`, ghi ngắn sau mỗi mốc: việc xong, file, lệnh/kết quả, phần chưa thử, bước tiếp. Không đưa secret vào nhật ký.

### Mốc A — Đối chiếu và khung

Đọc repo, xác nhận Git/board/cấu hình, chọn thư viện bằng bằng chứng QoS1, tạo module và networking-disabled build. Ghi thiết kế task/bộ đệm/máy trạng thái ngắn trước khi tích hợp.

### Mốc B — Payload và logic không cần board

Viết serializer/parser/epoch/session state machine và tests. Dùng fake clock/transport để kiểm thử logic thực tế, không viết tests chỉ kiểm tra chuỗi có trong source. Dữ liệu giả phải nằm trong fixture/test và gắn nguồn đúng, không thay dữ liệu thật chạy production.

### Mốc C — Broker/registry/LAN

Chuẩn bị cấu hình local của thiết bị DEVICE, ACL/profile và port LAN. Thử backend/broker trước, rồi firmware connect/subscribe/sync. Chưa có board thì dừng tuyên bố ở phần mềm, không ghi hardware PASS.

### Mốc D — Live từ cảm biến thật tới Dashboard

Đăng nhập browser, chọn đúng device_id và chứng minh chuỗi ESP32→MQTT→BE→WS→FE. Kiểm tra tuổi mẫu/null/nguồn/nhịp gửi và cảm biến lỗi khi mạng vẫn tốt. Không thêm UI mới để né lỗi dữ liệu.

### Mốc E — Start/Stop và lỗi

Thử đủ ACK/lặp/Stop-thay-Start/reboot/restart/mất mạng như ma trận dưới. Đo ảnh hưởng lấy mẫu và bộ nhớ khi bật mạng, so với Serial-only.

### Mốc F — Kiểm tra hồi quy và bàn giao

Cập nhật docs, chuẩn bị commit/PR, chờ CI. Nếu thiếu phần cứng hoặc quyền chạy một bài, ghi NOT_RUN/WAITING_HARDWARE với lý do, đưa tôi đúng thao tác kiểm tra còn cần; không gán PASS.

Sau mỗi mốc giải thích ngắn, dễ hiểu: file vừa làm để làm gì, logic quan trọng, kết quả và giới hạn. Không đổ toàn bộ code vào chat nếu đã sửa file trên máy. Nếu tôi yêu cầu học/gõ từng file thì chuyển sang nhịp từng file và chờ tôi xác nhận xong file đó.

## 12. Đăng nhập Dashboard và thử API hiện có

Đọc 04-SETUP.md trước. Backend đã bảo vệ WebSocket bằng cookie người vận hành; thấy MQTT publish thành công chưa có nghĩa browser đã đăng nhập.

- Dùng OPERATOR_TOKEN local của backend thử nghiệm, không dùng tài khoản MQTT làm token người vận hành.
- Có thể dựng backend riêng trên máy tôi bằng tool tạo credential; không cần xin secret thật của máy Trung hoặc quyền admin repo.
- Dùng POST `/api/v1/auth/login` và cookie HttpOnly, credentials=include theo hướng dẫn04. Không đưa token vào VITE_*, localStorage, query URL hoặc firmware.
- Dùng cùng hostname localhost cho browser/API khi thử trên laptop để cookie đúng; tải lại Dashboard sau đăng nhập.
- Kiểm tra `/api/v1/health/mqtt` bằng quyền người vận hành và theo dõi log từ backend.

Dashboard hiện chưa có giao diện Start/Stop ghi hoàn chỉnh của09. Thử qua API/PowerShell, không tự làm thêm màn hình đó:

```powershell
# OPERATOR_TOKEN được nạp từ cấu hình local, không dán giá trị vào source/chat.
$operatorHeaders = @{ Authorization = "Bearer $env:OPERATOR_TOKEN" }
$recordingId = 'DEVICE-SESSION-' + [guid]::NewGuid().ToString('N')
$startBody = @{ session_id = $recordingId; device_id = 'ESP32-001' } | ConvertTo-Json
Invoke-RestMethod http://localhost:8000/api/v1/sessions/start -Method Post -Headers $operatorHeaders -ContentType application/json -Body $startBody
Invoke-RestMethod http://localhost:8000/api/v1/sessions -Headers $operatorHeaders
$stopBody = @{ session_id = $recordingId } | ConvertTo-Json
Invoke-RestMethod http://localhost:8000/api/v1/sessions/stop -Method Post -Headers $operatorHeaders -ContentType application/json -Body $stopBody
```

Device ID/URL phải thay theo cấu hình thật, không tự sửa payload nếu thấy lỗi. Tạo ID phiên mới cho lần thu mới, không tái sử dụng phiên đã đóng. Nên cho thiết bị online/sync trước khi Start để không hết hạn lệnh.

## 13. Ma trận kiểm thử bắt buộc

Lập bảng PASS/FAIL/NOT_RUN, ghi command/log/fixture/ảnh hoặc số đo thực cho từng ca. Không coi bài Python simulator của04 là nghiệm thu firmware C++.

| ID | Ca | Kết quả cần |
|---|---|---|
| F01 | Build không file credential local | Compile thành công, networking tắt/mẫu có kiểm soát, không secret |
| F02 | Gói do serializer C++ thực sự tạo | Qua InboundTelemetry/control.py; không dùng JSON Python viết tay thay bằng chứng serializer |
| F03 | HR/GSR lỗi, cũ, NaN,0 hoặc chưa baseline | Null/quy tắc đúng, không số cũ hợp lệ, không chuỗi/bool giả số |
| F04 | Có broker LAN thật | ESP32 connect/subscribe/SUBACK/sync; đúng ID/DEVICE/ACL |
| F05 | Live không có phiên | session=null, timestamp boot; backend/WS/Dashboard nhận đúng |
| F06 | Start→ACK→confirmation | Backend STARTING rồi RECORDING, timestamp theo epoch; không từ PUBACK |
| F07 | Command trùng qua topic và pending_command | Một lần thực thi/đặt epoch, ACK nhất quán |
| F08 | Sai profile/ID/boot/connection/nonce/generation/lease | Không thực thi, lý do rõ, không reset state |
| F09 | Stop bình thường | STOPPED đúng, zero-batch/raw-disabled và complete=false phù hợp05 |
| F10 | Stop khi Start/confirmation đang chờ, ACK Start muộn | Không treo, không quay lại ghi sau ý định Stop |
| F11 | Wi-Fi sai/mất rồi khôi phục | Lấy mẫu tiếp, backoff/log/bộ đệm có giới hạn, không xả backlog |
| F12 | Broker stop/restart | Nonce kết nối/LWT mới, sync lại, không reset epoch phiên còn hợp lệ |
| F13 | Backend stop/restart khi broker còn | Không coi broker online/PUBACK là confirmation; sync lại và giữ phiên theo backend |
| F14 | Reboot ESP32 khi đang ghi | boot mới, backend không nối timestamp0 vào phiên cũ, không tự Start |
| F15 | Cảm biến ngắt khi mạng tốt | Dữ liệu lỗi thành null, mạng vẫn live; không giả đo lường bình thường |
| F16 | Sai mật khẩu/ACL, retained command/presence cũ, quá gói | Bị từ chối/bỏ đúng; không live/Start giả |
| F17 | So sensing trước/sau bật Wi-Fi/MQTT/Serial | Có count/rate/gap/độ trễ/heap/stack thật, nêu thiếu số đo |
| F18 | Dashboard hiện tại | Chọn đúng thiết bị, HR/GSR hợp lệ hiển thị, nguồn DEVICE, stale/mất kết nối đúng |
| F19 | Hồi quy backend/AI/frontend/firmware/CI | Không làm hỏng luồng giả lập đã có hoặc đổi tên6 check |

F02 nên có native C++ tests hoặc harness thích hợp của dự án để xuất fixture thực từ serializer, rồi Python dùng đúng schema runtime kiểm tra. Nếu môi trường không chạy được phần C++, ghi rõ và cung cấp lệnh tái hiện; không ghi PASS bằng fixture tự viết.

Các bài hồi quy tham khảo, điều chỉnh đường Python cho máy tôi:

```powershell
.\.venv\Scripts\python.exe -m platformio run -d ai/edge_firmware
.\.venv\Scripts\python.exe .github/scripts/check-firmware-headers.py
Push-Location backend
..\.venv\Scripts\python.exe -m pytest -q
Pop-Location
Push-Location ai
..\.venv\Scripts\python.exe -m pytest -q
Pop-Location
npm --prefix frontend test
npm --prefix frontend run build
docker compose config --quiet
.\.venv\Scripts\python.exe .github/scripts/check-mock-transport.py
.\.venv\Scripts\python.exe scripts/check_mqtt_integration.py
```

Đọc thêm test command hiện tại trong repo. Thêm tests/CI cần thiết cho firmware05 nhưng giữ nguyên6 tên check bảo vệ nhánh. Không skip bài lỗi hoặc sửa expected chỉ để CI xanh. Nếu lỗi do môi trường, tìm nguyên nhân và báo đúng.

## 14. Tài liệu và bàn giao

Tạo/cập nhật tối thiểu:

- Kế hoạch05 và dòng05 trong tracker: người thực hiện Tân, Trung review; trạng thái dựa bằng chứng.
- `05-IMPLEMENTATION-LOG.md`: tiến độ, quyết định, bước tiếp qua từng mốc.
- `05-SETUP.md`: dựng LAN/registry/ACL/credential local, build/upload, login Dashboard, Start/Stop, troubleshooting.
- `05-VERIFICATION.md`: ma trận F01–F19, lệnh/kết quả, board/commit/profile, số đo và giới hạn.
- `05-HANDOFF.md`: file chính làm gì, thư viện/phiên bản, cách chạy, phần còn thiếu và điểm nối cho07.
- Phase07/CHANGELOG/API docs khi thay đổi thực tế liên quan; không tự đánh phase07 DONE khi thiếu board/lan thật.

Mọi log/ảnh/fixture phải che secret và chỉ có dữ liệu được phép chia sẻ. Mẫu nguồn SYNTHETIC không được trình bày là đo DEVICE. Thiết bị nghiên cứu kỹ thuật này không chẩn đoán ASD/lo âu; không tự diễn giải HR/GSR như kết luận y khoa.

Phân biệt ba mức kết quả:

1. Code/build/tests phần mềm đạt, chưa có board → READY_FOR_REVIEW hoặc WAITING_HARDWARE, ghi rõ ca NOT_RUN; chưa hoàn tất nghiệm thu nhánh5.
2. Có board, live/StartStop/lỗi/tài nguyên đạt → đủ bằng chứng đề nghị Trung review.
3. PR đủ CI và được Trung approve/merge → mới ghi nhánh5 DONE theo tracker.

Sau khi code/tests/docs sẵn sàng, được commit/push nhánh5 và mở PR vào dev nếu tài khoản GitHub trên máy tôi có quyền; không thay quyền repo, không tự approve hoặc merge. Nếu auth/tool không cho phép, bàn giao commit/diff và lệnh cụ thể để tôi push, không giả đã tạo PR.

Commit nên chia theo phần có thể review: cấu hình/thư viện → serializer/đồng hồ/máy trạng thái → MQTT/Wi-Fi/tích hợp → tests/docs. Commit message tiếng Việt ngắn, ví dụ:

```text
feat(firmware): gửi telemetry MQTT và xác nhận lệnh phiên
```

PR phải ghi vấn đề/hành vi cuối, cách thử và giới hạn; base=dev, reviewer=@namtrungdn310. Giữ rõ nhánh6/7 chưa triển khai. Tân/AI không có ngoại lệ tự merge PR cộng tác viên; Trung là người quyết định merge.

## 15. Cách bắt đầu ngay

Hãy bắt đầu bằng kiểm tra repo/Git, đọc các file nguồn và báo kết quả ngắn cùng kế hoạch file. Sau đó triển khai mốc A và B trước, đồng thời hỏi tôi những thông tin phần cứng còn thiếu. Tiếp tục qua các mốc tới khi bàn giao đầy đủ phần được kiểm chứng; nếu thiếu board/dịch vụ bên ngoài, hoàn thiện mọi phần độc lập rồi nêu đúng việc cần tôi thực hiện, không bịa kết quả hoặc dừng ở một bản demo publish đơn giản.
