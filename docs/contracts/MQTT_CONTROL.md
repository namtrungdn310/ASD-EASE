# Điều khiển MQTT 1.0 — đặc tả

Ngày 2026-10-31. Dùng cùng [quy tắc nhận dữ liệu](INGESTION_V1.md) và [đặc tả API](../API_CONTRACT.md).

Backend04 đã triển khai và thử broker thật ngày2026-11-01, xem [bàn giao](../integration/04-HANDOFF.md). Firmware05/raw06–07 vẫn cần triển khai/đo riêng; các mục dưới là quy tắc đích, không tự là bằng chứng đã nghiệm thu toàn hệ thống.

Chọn MQTT3.1.1 và Mosquitto cục bộ. Nhánh04/05 chốt phiên bản broker/thư viện sau kiểm tra tương thích. Firmware hiện dùng Arduino: phải chứng minh thư viện **gửi được QoS1**, không chỉ nhận QoS1; kiểm tra build, TLS, kích thước gói và bộ nhớ. Không coi API ESP-IDF dùng được ngay với mọi thư viện Arduino.

## Topic và quyền truy cập

Tiền tố: asd-ease/v1/{data_origin}/{device_id}/. Nguồn viết đúng DEVICE/SYNTHETIC; ID theo allowlist. Topic, nội dung và tài khoản phải cùng thiết bị/nguồn. Topic tối đa256 byte UTF-8, JSON4096 byte; raw không có topic MQTT.

| Phần cuối topic | Bên gửi → bên nhận | QoS | Retain |
|---|---|---|---|
| telemetry | Thiết bị → backend | 0 | false |
| command | Backend → thiết bị | 1 | false |
| ack | Thiết bị → backend | 1 | false |
| state/request | Thiết bị → backend | 1 | false |
| state/response | Backend → thiết bị | 1 | false |
| presence | Thiết bị/LWT → backend | 1 | true |

Mỗi tài khoản thiết bị chỉ gửi4 topic của mình và nhận2 topic từ backend của mình. Backend có quyền đối ứng cần thiết, không dùng tài khoản quản trị broker. UI không kết nối MQTT hoặc nhận credential.

QoS áp dụng cả lúc gửi và đăng ký nhận. PUBACK chỉ xác nhận một chặng truyền, không xác nhận DB đã ghi/thiết bị đã thực thi. Tham khảo [OASIS MQTT3.1.1](https://docs.oasis-open.org/mqtt/mqtt/v3.1.1/os/mqtt-v3.1.1-os.html).

## Trường chung của gói điều khiển

Không áp dụng bảng này cho telemetry. Control là JSON object, không có trường ngoài khai báo.

| Trường | Quy tắc |
|---|---|
| control_version | Chuỗi đúng1.0 |
| message_type | COMMAND/ACK/STATE_REQUEST/STATE_RESPONSE/PRESENCE |
| device_id | Khớp topic và danh tính đã xác thực |
| data_origin | DEVICE/SYNTHETIC |
| boot_id | ID mới sau mỗi reboot; giữ qua reconnect cùng boot |
| connection_id | Nonce mới mỗi lần nối MQTT, không chỉ mỗi reboot |

request_id đối chiếu lượt đồng bộ; command_id là ID lệnh lưu bền trong DB. generation là số nguyên>=1, tăng theo thiết bị, không đặt lại theo phiên/backend restart. Lệnh chỉ chạy sau đồng bộ kết nối hiện hành, đúng boot/connection. Trường bắt buộc không được bỏ; chỉ trường cho phép mới dùng null.

## STATE_REQUEST — hỏi trạng thái và xác nhận ACK

Thêm các trường:
- request_id;
- actual_state: IDLE/RECORDING/STOPPED;
- session_id, last_command_id: ID hoặc null;
- last_generation: số nguyên>=0;
- timestamp_ms: thời gian theo phiên/boot;
- last_ack: gói ACK hoặc null.

Khi nối MQTT: đăng ký command/state-response → nhận SUBACK → gửi STATE_REQUEST với nonce mới. Chưa gửi telemetry có phiên trước đồng bộ.

Backend kiểm tra tài khoản/boot/trạng thái, lưu và đối chiếu rồi trả STATE_RESPONSE cùng request_id/connection_id. Boot mới có phiên cũ thì đánh gián đoạn, không nối clock. Start chờ cho boot cũ bị huỷ; muốn thu lại cần yêu cầu Start mới.

## STATE_RESPONSE — trạng thái backend đã xác nhận

Thêm: request_id, session_id(ID/null), state(IDLE/STARTING/RECORDING/STOPPING/STOPPED/ABORTED), generation>=0, accepted_command_id(ID/null), pending_command(COMMAND/null), error_code(mã/null).

Bỏ yêu cầu cũ/sai boot và ghi log; không thay kết nối đang có. Chỉ kèm lệnh còn hợp lệ về trạng thái, danh tính và thời hạn. Thiết bị đối chiếu trước khi thực thi.

Backend restart có thể mất thông tin kết nối sống. Thiết bị hỏi STATE_REQUEST định kỳ15 s dù broker còn kết nối; trước đồng bộ lại, backend bỏ telemetry chưa biết boot/kết nối và báo suy giảm. Lệnh chờ chỉ phát khi đã đồng bộ hiện hành.

## COMMAND — yêu cầu Start/Stop

Thêm: request_id, command_id, generation>=1, session_id, action(START/STOP), expires_in_ms(1..30000), acquisition_profile.

START có acquisition_profile gồm ppg_hz/imu_hz/gsr_hz nguyên1..1000 và window_ms=1000. STOP dùng profile=null. Thiết bị kiểm tra có đáp ứng cấu hình không; không âm thầm sửa/clamp rate. Cấu hình50/50/20 là danh định, chưa phải số đo; không đáp ứng thì PROFILE_UNSUPPORTED hoặc chặn nghiệm thu thật.

### Thời hạn không phụ thuộc UTC trên ESP32

Backend giữ thời hạn lệnh trong DB. Thiết bị tính thời hạn bằng đồng hồ tăng đơn điệu từ lúc gửi STATE_REQUEST tương ứng; lệnh phải khớp request_id và còn trong expires_in_ms, tối đa30 s.

Bản lệnh lặp không gia hạn. Sau30 s, thiết bị cần lượt đồng bộ mới để nhận quyền thực thi mới; backend vẫn không gia hạn thời hạn nghiệp vụ của lệnh. Gói quá muộn/sai lượt đồng bộ bị từ chối, kể cả cùng boot.

Cùng ID/generation/action/session trong boot: trả lại ACK, không chạy lại hoặc đặt lại mốc thu. Cùng ID nhưng nội dung lệnh khác trả COMMAND_CONFLICT; generation thấp trả STALE_COMMAND. STOP generation cao hơn có thể thay START.

Thiết bị giữ lệnh/ACK cần thử lại trong RAM có giới hạn. Reboot đổi boot ID nên không phát lại lệnh cũ. Thông tin này không đưa vào JSON raw1.0.

## ACK — xác nhận đã thực thi

Thêm: request_id, command_id, generation>=1, session_id, action(START/STOP), result(STARTED/STOPPED/REJECTED), timestamp_ms, reason(mã/null), final_summary(object/null).

- STARTED: actionSTART, reason=null, final_summary=null, timestamp0. Thiết bị đã đặt mốc thu, giữ mẫu trong bộ đệm có giới hạn; gửi ACK rồi hỏi STATE_REQUEST(last_ack=ACK) tới khi backend xác nhận accepted_command_id/trạng thái đúng. Sau xác nhận mới gửi dữ liệu theo phiên; PUBACK không thay bước này. Trong lúc chờ vẫn xử lý STOP.
- STOPPED: actionSTOP, reason=null, timestamp=cutoff; bắt buộc final_summary. Nhánh05 chưa bộ ghi raw có thể báo zero-batch và raw_recording_enabled=false, không bịa dữ liệu đã thu. Nhánh07 mới hoàn tất raw.
- REJECTED: reason có mã, summary=null. Báo trạng thái thực qua STATE_REQUEST; backend không coi đây là bắt đầu/dừng thành công.
- Sau reconnect, ACK được bọc lại với connection/request hiện hành nhưng giữ nội dung nghiệp vụ, kết quả, mốc thu và tổng kết. Backend chống trùng theo nghiệp vụ, không coi nonce mới là lệnh mới.
- Chỉ xác nhận accepted_command_id sau khi ACK lưu bền. Cùng lệnh nhưng cutoff/counts khác trả ACK_CONFLICT, không ghi đè. ACK lệnh bị thay thế chỉ lưu để tra soát, không đổi vòng đời hiện hành.

## Final summary — tổng kết lúc dừng

| Trường | Ý nghĩa/điều kiện |
|---|---|
| cutoff_timestamp_ms | Mốc dừng nguyên>=0 |
| final_batch_id | Nguyên>=0 hoặc null khi không có batch |
| total_generated_batches | Tổng batch đã tạo; có batch thì bằng final_batch_id+1 |
| dropped_batches | Batch bị bỏ, không vượt tổng |
| slot_counts | Object ppg/imu/gsr: tổng vị trí mẫu trên timeline, kể cả thiếu/bị bỏ |
| missing_samples | Cùng3 khoá: mẫu cảm biến thiếu, không vượt slot_counts; không cộng lại mất do transport |
| dropped_batch_ranges | Tối đa64 object first/last, hai đầu tính cả, tăng và không chồng, nằm trong0..final |
| loss_ranges_truncated | Có phải đã rút gọn chi tiết mất batch không |
| raw_recording_enabled | Có bật ghi raw hay chỉ telemetry |

Nếu không rút gọn, số ID trong ranges phải khớp dropped_batches. Khi rút gọn, vẫn giữ tổng đúng và đánh bản ghi không đầy đủ.

Backend đối chiếu số slot với cutoff/rate và batch thực nhận. Tổng kết có thể đến trước/sau raw HTTP cuối. Chỉ HTTP202 đúng batch mới giải phóng raw; ACK Stop không làm việc đó.

Không có mẫu: cutoff0, finalnull, totals0, ranges[]. Đây là phiên rỗng, không phải bộ dữ liệu hữu ích.

## PRESENCE và LWT

Thêm status=ONLINE/OFFLINE. Đăng ký LWT OFFLINE trước connect; ngắt chủ động cũng gửi OFFLINE. Retained presence có thể cũ, không chứng minh thiết bị đang gửi mới hay đang ghi.

OFFLINE của kết nối cũ không được ghi đè kết nối mới. Backend/WS đang mở không có nghĩa thiết bị đang sống.

## Lỗi, thử lại và phục hồi

Giữ nguyên mã:
MALFORMED_JSON, SCHEMA_INVALID, IDENTITY_MISMATCH, SESSION_NOT_FOUND,
SESSION_NOT_ACCEPTING, PROFILE_UNSUPPORTED, STALE_COMMAND, COMMAND_CONFLICT,
ACK_CONFLICT, BOOT_MISMATCH, CONNECTION_MISMATCH, LEASE_EXPIRED, BUSY,
COMMAND_TIMEOUT, INTERRUPTED_REBOOT, DRAIN_TIMEOUT, STORAGE_UNAVAILABLE.

Gói không có danh tính an toàn thì bỏ/ghi log/bộ đếm, không phản hồi vào topic do client tuỳ chọn. Lệnh đúng danh tính nhưng sai nghiệp vụ trả ACK REJECTED có đối chiếu. ACK/state sai thì báo lỗi qua response khi có yêu cầu hợp lệ, không giả accepted. MQTT không trả HTTP422/409.

Backend lưu yêu cầu/ý định/lệnh chờ trước HTTP202, phát sau commit:
- Lỗi sau lưu, trước phát: phát lại cùng lệnh từ DB.
- Thiết bị đã chạy nhưng mất ACK: lệnh lặp nhận lại ACK, không chạy lại.
- Backend nhận ACK chưa lưu: thử lại qua last_ack.
- Đã lưu nhưng mất xác nhận: lượt hỏi sau được xác nhận lại.

Thử lại không đổi command ID/generation hoặc gia hạn nghiệp vụ. Sau30 s không ACK thật thì ABORTED/trạng thái chưa rõ, không suy thiết bị dừng. Đã ACK dừng nhưng raw thiếu thì chờ30 s rồi STOPPED/incomplete. Chưa Start mới khi trạng thái cũ chưa rõ.

Baseline dùng phiên MQTT sạch; DB giữ lệnh bền, không dựa hàng đợi offline của broker. Muốn dùng phiên bền phải bổ sung quyết định/kiểm thử chống lệnh cũ. Một tiến trình nhận MQTT để tránh sự kiện/WS đôi khi reload/nhiều worker. Retry/hỏi trạng thái có giới hạn, không chặn lấy mẫu.

## Chuỗi cần kiểm thử ở04–07

1. HTTPStart → lưu lệnh → đồng bộ → COMMANDSTART → STARTEDACK → lưu ACK → xác nhận trạng thái → gửi dữ liệu.
2. Stop generation cao hơn → cutoff/tổng kết → raw tới bất kỳ thứ tự → đủ/thiếu được phân biệt.
3. Stop thay Start đang chờ; ACK Start muộn không quay lại RECORDING.
4. Gửi lặp, hết thời hạn, lệnh retained cũ, LWT cũ không đặt lại epoch hoặc báo live sai.
5. Reboot thiết bị không trộn clock; backend restart phục hồi lệnh; broker restart tạo nonce kết nối mới.
6. Mất từng kênh, đầy hàng đợi, tổng kết rút gọn, zero-batch không báo đủ sai.

[examples.json](examples.json) chỉ là mẫu. Kiểm thử broker/board, C++ và gây lỗi có kiểm soát thuộc04–07/10; không tick đã chạy chỉ vì có tài liệu này.
