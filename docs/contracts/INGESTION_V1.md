# Quy tắc nhận dữ liệu 1.0 — nhánh 04–07

Thiết kế ghi ngày 2026-10-31, **chưa có mã chạy thực tế**. [API](../API_CONTRACT.md) là mục tra cứu; file này quy định nguồn, thời gian, phiên và lưu raw. [Điều khiển MQTT](MQTT_CONTROL.md) quy định lệnh/xác nhận. Mẫu đi kèm là SYNTHETIC, không phải số đo board.

## Định danh, phiên bản và kiểm tra đầu vào

- Nhận JSON object UTF-8; từ chối NaN/Infinity, khoá lặp, bool/chuỗi giả số và trường ngoài khai báo ở mọi cấp. Trường nguyên phải là số nguyên JSON, không bool. Pydantic hiện còn ép kiểu và thiếu kiểm tra ở cấp lồng nhau; 04/06 phải bổ sung kiểm thử gói sai.
- ID dài1–64, theo `^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$`. ID tuỳ chọn thiếu dùng null, không chuỗi rỗng. Bên gọi Start tạo session_id duy nhất toàn DB, không tái dùng. Timestamp/số đếm/generation không vượt `2^53-1`.
- Bảng đăng ký ràng buộc tài khoản với device_id và nguồn; một thiết bị chỉ có một nguồn. Không tin tiền tố tên hoặc data_origin tự khai. Bên gửi phải khai nguồn rõ dù schema hiện mặc định DEVICE.
- HTTP nhận dữ liệu dùng `Authorization: Bearer <local-device-token>`; điều khiển/tra cứu dùng quyền người vận hành riêng. MQTT dùng tài khoản/ACL riêng cho từng thiết bị. Không đưa token vào URL, log, Git hoặc VITE_*/mã trình duyệt. Trước UI09, nhánh04 phải có cách đăng nhập/phiên hoặc proxy cục bộ giữ token ngoài bundle, không hardcode.
- Không cho truy cập ẩn danh. Ngoài LAN phát triển riêng phải dùng TLS có kiểm tra chứng chỉ. Ngoại lệ TCP1883/HTTP8000 chỉ dành LAN riêng đã ghi rủi ro; không gọi đó là mã hoá. Không mở broker ra Internet hoặc tắt tường lửa.
- Giữ đường HTTP cho simulator nhưng phải cập nhật thông tin xác thực; không giữ API bỏ qua quyền. Một luồng chỉ có một bên gửi qua một transport, không gửi đôi HTTP+MQTT.

<a id="clock-and-sampling"></a>
## Thời gian và lấy mẫu

- Khi Start thực thi, thiết bị đặt mốc thu trước mẫu đầu, chỉ một lần. Timestamp là ms từ mốc đó, không phải giờ nhận gói. Retry/kết nối lại không đặt lại đồng hồ.
- Dùng đồng hồ tăng đơn điệu64 bit hoặc mở rộng khi millis() tràn. Reboot có boot_id mới, phiên cũ bị gián đoạn; không nối thời gian trở về0 vào phiên cũ.
- Telemetry không session dùng ms từ boot. Chỉ nhận MQTT sau khi đồng bộ đúng boot/kết nối; không ghép biểu đồ khác boot/phiên. Cấu hình lấy mẫu giữ cố định trong phiên.
- Mẫu thứ i ở `start_timestamp_ms+i*1000/rate`. Mẫu0 mọi luồng cùng mốc; null giữ chỗ thiếu. Mất cặp PPG thì red/IR cùng null; mất mẫu IMU thì cả6 trục null.
- Thiết kế phát triển cho board là PPG50/IMU50/GSR20 Hz danh định, **chưa đo**. Simulator100/50/20 là cấu hình giả lập riêng hợp lệ. Rate là số nguyên1..1000 Hz theo cấu hình phiên, không lấy tốc độ chip thay tốc độ FIFO. Xem [ánh xạ driver](DRIVER_MAPPING.md).
- Cửa sổ thường1000 ms; batch0 bắt đầu0, batch n bắt đầu n*1000. Đoạn thời gian gồm đầu, không gồm cuối: [start,end). Số mẫu mỗi luồng = duration_ms*rate/1000, phải nguyên.
- Batch cuối có thể ngắn1..1000 ms. Mốc dừng phải nằm trên lưới thời gian chung: rates50/50/20 có bước chung100 ms. Làm tròn Stop lên mốc chung gần nhất, ngừng tại đó và báo mốc thực; không chèn0. Dừng đúng ranh1000 ms không sinh batch rỗng. Chưa thu gì: cutoff0, không batch, final_id=null.
- Batch bị bỏ để lại khoảng trống ID, không đánh số lại. Vòng loop10 ms chưa chứng minh đồng bộ. Nếu driver không đáp ứng thời gian đều/cùng mốc, chặn nghiệm thu thật và đề xuất phiên bản có timestamp theo luồng/mẫu; không gán thời gian giả. Raw1.0 không bảo toàn jitter tuỳ ý.

## Telemetry và chất lượng

- Dùng cấu trúc trong [API](../API_CONTRACT.md). Mặc định gửi1000 ms/lần; sau5000 ms không có mẫu mới được chấp nhận thì dữ liệu cũ. Đây là nhịp gửi, không phải nhịp lấy mẫu.
- Thiết bị chỉ gửi snapshot mới sau đồng bộ, hàng đợi1, retain=false, không gửi dồn bản cũ. Khoá (device,session/boot,timestamp) cùng nội dung chuẩn hoá là gói trùng: không cập nhật lần thấy gần nhất, DB/sự kiện/WS lần2. Cùng khoá khác nội dung là xung đột; timestamp cũ bị bỏ và ghi log.
- Schema1.0 không có boot trong telemetry nên không tự phát hiện mọi bản phát lại độc hại. Thiết kế dựa vào phiên MQTT sạch, đồng bộ mới, bên gửi đã xác thực và TLS; giờ nhận gói không chứng minh tuổi của mẫu.
- HR chỉ gửi khi hợp lệ, hữu hạn20..240 và còn mới từ nhịp/cập nhật đã xác nhận. Sentinel0/lỗi/cũ dùng null. TTL phát triển HR3000 ms, GSR/IMU1000 ms. Driver thiếu mốc cập nhật thì 05 thêm thông tin nội bộ hoặc để null; read() trả cache không thành mẫu mới.
- GSR ADC lấy trước EMA, sau trung bình8 lần. Delta=percentChange/100 khi valid, còn mới và baselineConductance>0.05; chưa xác minh mạch phải ghi chưa hiệu chuẩn. Không đưa deltaConductance_uS vào tỷ lệ. Movement chưa thuật toán dùng null; SpO2 chỉ debug.
- Chưa có bộ ước lượng chất lượng: cả3 quality=0 theo cách biểu diễn bảo thủ, nghĩa chưa chứng minh chất lượng, không phải đã đo ra0. Không bịa0.9 hoặc loại raw hợp lệ chỉ vì chưa có bộ ước lượng.
- DEVICE chưa mô hình: model_version=none, probability=null. GSR/IMU đang CALIBRATING thì trạng thái CALIBRATING; còn lại UNCERTAIN, kể cả PPG đang tìm mạch/lỗi. Sensor VALID không tự thành NORMAL.
- Kịch bản SYNTHETIC cũ được giữ trong chế độ tương thích có ghi điểm/trạng thái gán sẵn; không dùng để nới quy tắc DEVICE.

## Giới hạn và thử lại

Đây là **mặc định thiết kế**, không bảo đảm RAM board. Nhánh05/07 phải đo, có thể giảm hàng đợi. Tăng trần hoặc đổi schema cần sửa đặc tả/kiểm thử trước.

| Mục | Mặc định/trần |
|---|---|
| JSON telemetry/control | <=4096 byte/gói; bộ đệm MQTT tính thêm topic/header |
| Raw HTTP | <=65536 byte; giới hạn ngay khi đọc, kể cả thiếu Content-Length; không gzip |
| Mảng raw | <=1000 mẫu/luồng, không rỗng, khớp cửa sổ/cấu hình; JSON sâu<=8 |
| Hàng đợi raw trên thiết bị | <=4 batch đã đóng và <=32768 byte đã đóng gói; chạm một trần là đầy. Bộ đệm đang thu và serializer tính riêng |
| Telemetry | Chỉ bản mới nhất |
| Control | <=8 gói đang gửi/chờ và <=32768 byte; một lệnh hiện hành/thiết bị |
| Hàng đợi MQTT backend | <=256 gói và <=1MiB tổng payload; đầy thì ghi lỗi/bộ đếm, không giả ACK |
| Mạng | Kết nối3000 ms, tổng HTTP5000 ms; chạy riêng, không chặn lấy mẫu |
| Thử lại | Chờ1,2,4,8,16,30 s, thêm ngẫu nhiên<=20%; đặt lại sau thành công |
| Keepalive / chờ ACK lệnh / chờ raw cuối | 15 s /30 s /30 s từ ACK đã dừng |

Khi raw đầy: bỏ batch mới vừa đóng, giữ bản cũ đang chờ ACK bất biến; ID/timeline vẫn tăng, báo số mất. Không tự thêm ghi flash. Tối đa64 khoảng batch mất; vượt thì giữ tổng, đánh loss_ranges_truncated=true và bản ghi không đầy đủ.

## Kiểm tra raw, ACK và chống trùng

Raw chỉ HTTP. Phải kiểm tra phiên/thiết bị/nguồn/cấu hình, mảng không rỗng, độ dài PPG/6 trục IMU, cặp null, thời gian/số mẫu/tốc độ, chồng lấp và giới hạn.

PPG nguyên0..262143; GSR nguyên0..4095; IMU hữu hạn, gia tốc g±2, vận tốc degrees/s±250 theo cấu hình hiện tại, hoặc null. Giá trị sát giới hạn nhưng trong dải vẫn lưu, bản mô tả báo bão hòa; không gọi ADC là độ dẫn đã hiệu chuẩn.

Khoá (session_id,device_id,batch_id), nguồn từ phiên. Chỉ ACK khi file đã lưu bền và chỉ mục nhất quán. Lỗi có dạng:

```json
{"accepted":false,"batch_id":null,"error":{"code":"SCHEMA_INVALID","retryable":false}}
```

Điền batch_id nếu đọc được. Không trả đường dẫn thật, secret hoặc stack trace.

| HTTP | Mã/kết quả | Thiết bị xử lý |
|---|---|---|
| 202 | accepted=true, batch_id=n, duplicate=false | Giải phóng đúng batch |
| 202 | Cùng khoá/hash, duplicate=true | Giải phóng, không đếm lần2 |
| 400 | MALFORMED_JSON, kể cả khoá lặp | Sửa bên gửi, không thử lại mù |
| 401/403 | UNAUTHORIZED/IDENTITY_MISMATCH | Sửa cấu hình/quyền |
| 404 | SESSION_NOT_FOUND | Đồng bộ phiên, không tạo phiên từ raw |
| 409 | BATCH_CONFLICT/SESSION_NOT_ACCEPTING/PROFILE_MISMATCH | Đối chiếu; không ghi đè hoặc thử lỗi cũ vô hạn |
| 413/415 | PAYLOAD_TOO_LARGE/UNSUPPORTED_MEDIA_TYPE/CONTENT_ENCODING | Sửa cho phiên mới; không cắt batch đang retry cùng ID |
| 422 | SCHEMA_INVALID/TIMELINE_INVALID | Sửa lỗi, không coi đã nhận |
| 429/503/507 | BUSY/STORAGE_UNAVAILABLE/STORAGE_FULL | Chờ và giữ batch trong hàng đợi có hạn |
| Hết thời gian/mất mạng/5xx | Có thể backend đã ghi | Gửi lại cùng ID và nội dung |

- Cùng khoá khác nội dung trả409, giữ bản cũ. Phiên đóng vẫn xác nhận202 cho bản trùng đúng quyền/hash; bản khác hoặc batch mới trả409.
- STOPPING nhận batch trước cutoff/trong hạn chờ, có thể sai thứ tự. Batch3 đến trước1 không làm1 bị loại.
- Batch cuối ngắn đến trước tổng kết: chỉ nhận khi backend đã STOPPING, số mẫu tự suy ra cutoff hợp lệ trên lưới chung. Lưu thông tin tạm và trả202 sau lưu bền, chưa complete. Tổng kết đến sau phải khớp; lệch thì giữ file, ghi xung đột/thiếu. RECORDING chưa có ý định Stop chỉ nhận cửa sổ đầy.
- Hash là SHA-256 của JSON chuẩn hoá theo [RFC8785/JCS](https://www.rfc-editor.org/rfc/rfc8785), sau kiểm tra nghiêm kiểu và đủ trường. Thứ tự khoá/khoảng trắng không ảnh hưởng; thứ tự mảng/null giữ nguyên. 1/1.0 và -0/0 chỉ tương đương nếu cả hai hợp lệ cho trường đó; trường nguyên vẫn từ chối1.0 trước hash. sort_keys=True không tự là JCS. Nhánh06 phải có mẫu kiểm thử chuẩn; firmware không cần tự hash để gửi.
- Đường lưu: {root}/{origin}/{session_id}/{device_id}/batches/{batch_id}.json. Kiểm tra ID và đường dẫn nằm trong root; client không chọn path.
- DB giữ khoá duy nhất ở PENDING/hash → ghi file tạm cùng ổ, flush/fsync → công bố nguyên tử không ghi đè và lưu metadata thư mục theo OS → chỉ mục COMPLETE/số mẫu →202. Khoá Python trong một process không thay ràng buộc DB.
- Lỗi trước công bố: chưa ACK, thử lại. Sau công bố/trước COMPLETE: đối chiếu file/hash, hoàn tất chỉ mục rồi ACK trùng. Sau COMPLETE/trước response: retry nhận202 trùng. PENDING đang xử lý trả503.
- COMPLETE thiếu/hỏng file:503, yêu cầu phục hồi và đánh không đầy đủ; không giả accepted. Xung đột hash giữ nguyên bản ghi để điều tra.
- Nhánh06 phải ghi rõ bảo đảm của OS/filesystem và thử lỗi; close() không tự bảo đảm chống mất điện. JSONL cũ giữ đọc được hoặc chuyển đổi sau sao lưu/đối chiếu số mẫu/hash; không xoá volume.

## Phiên HTTP và trạng thái thực tế

Start giữ request {session_id,device_id,participant_id?}; Stop giữ {session_id}. Nguồn/cấu hình từ bảng đăng ký. Response đích thêm vòng đời, callers phải cập nhật ở04. Hiện Start200/tạo row và Stop ghi giờ dừng chưa phải ACK thiết bị.

- Start202 sau lưu STARTING, desired=RECORDING và lệnh chờ. Lặp cùng ID/body trả cùng phiên/lệnh:202 nếu đang chờ,200 nếu đã giải quyết; không Start lại. Cùng ID khác body409. Request giống phiên đã đóng chỉ trả bản cuối, không mở lại. DB chặn2 phiên hoạt động/thiết bị kể cả đồng thời.
- Stop202 chuyển STOPPING, desired=STOPPED, tạo generation cao hơn. Lặp không tạo lại lệnh hoặc gia hạn. Phiên đã kết thúc trả200; không có404, sai quyền403.
- Stop đến trước Start ACK thì thay thế ý định cũ. ACK Start muộn không đưa về RECORDING. Chưa thu thì ACK zero-batch; đã thu thì cutoff/drain. Thiết bị vẫn nhận Stop khi đang chờ xác nhận Start.
- STARTING → RECORDING chỉ sau ACK STARTED hợp lệ. STOPPING → STOPPED khi có ACK đã dừng và đối chiếu raw; hết hạn chờ raw thì STOPPED nhưng complete=false. Reboot/không biết đã dừng/timeout lệnh thì ABORTED kèm lý do. PUBACK không đổi trạng thái thực.
- Mỗi thiết bị một phiên chưa kết thúc. Sau ABORTED, chưa Start mới cho tới khi đồng bộ xác nhận idle/stopped hoặc boot mới. Backend timeout không chứng minh thiết bị dừng. Mất broker không tự thành lệnh Stop; thu/đệm vẫn có hạn, UI báo thực tế chưa rõ khi dữ liệu cũ.
- Response gồm: session_id, device_id, participant_id nullable, data_origin, state, desired_state(RECORDING/STOPPED), actual_state(IDLE/RECORDING/STOPPED/UNKNOWN), command_id/generation, boot_id nullable, requested_at UTC, started_at/stopped_at UTC nullable, cutoff_timestamp_ms/final_batch_id nullable, recording_complete, incomplete_reasons và acquisition_profile.
- started_at là giờ backend quan sát ACK, không giả đồng bộ UTC mẫu. GETsessions ban đầu giữ mảng; phân trang/chi tiết/xuất chốt ở08 trước UI09.
- Telemetry có session chỉ nhận sau STARTED ACK trong RECORDING/STOPPING và trước cutoff. Thiết bị đợi state confirmation trước gửi telemetry/upload theo phiên. Raw đến trước trả409SESSION_NOT_ACCEPTING, giữ bộ đệm/đồng bộ, không tự tạo phiên. Trong lúc chờ vẫn phải xử lý Stop.

## Dừng, gửi nốt và đủ dữ liệu

Thiết bị chốt cutoff, final batch ID, tổng số batch/slot, số bị bỏ/thiếu và các khoảng ID mất. Tổng kết MQTT có thể trước/sau raw HTTP cuối. Backend lưu riêng và tính lại sau mỗi đầu vào, không giả hai giao thức có cùng thứ tự.

Complete chỉ khi có tổng kết đúng phiên/boot/generation; đủ ID0..final, hash/cấu hình/thời gian/số mẫu khớp cutoff; không mất batch/mẫu/null/file hỏng. Có bất kỳ thiếu hoặc không rõ chi tiết thì recording_complete=false, dù STOPPED.

Zero-batch với cutoff0/finalnull có thể là complete-empty, phải báo empty_recording=true; không coi là dữ liệu hữu ích. Nếu raw_recording_enabled=false ở nhánh05 thì không tuyên bố đã nghiệm thu ghi raw.

Broker mất nhưng HTTP còn: tiếp tục nhận raw cho phiên đã cấp quyền trong trạng thái/hạn chờ, không tự Start; thiếu tổng kết thì xử lý incomplete/ABORTED. HTTP raw lỗi nhưng MQTT còn: chart có thể chạy trong lúc bộ đệm đầy; phải báo mất thật. Đọc/xuất file đã lưu không cần broker. Chỉ HTTP202 đúng batch mới giải phóng raw, không PUBACK/ACK Stop.

## Tương thích và bàn giao

Nhánh04 làm xác thực, nhận chung, phiên và chuyển DB; simulator HTTP vẫn SYNTHETIC. Simulator cũ gửi raw không Start và tái dùng ID cố định phải được cập nhật ở04/06, không mở cửa bỏ qua quyền DEVICE để test xanh.

Nhánh05/07 kiểm tra JSON từ C++ bằng Pydantic, đo tốc độ/RAM trước nghiệm thu thật. File giả lập cũ không bị đổi thành dữ liệu thật. Mã kiểm tra chặt hơn và hành vi runtime thuộc nhánh tính năng, không nhánh tài liệu03.
