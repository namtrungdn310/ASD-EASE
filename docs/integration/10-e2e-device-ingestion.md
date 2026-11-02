# 10 — Nghiệm thu toàn luồng thiết bị và bản ghi

| Mục | Nội dung |
|---|---|
| Nhánh | `chore/e2e-device-ingestion` |
| Phụ trách | Trung — IT; Tân phối hợp phần cứng |
| Phụ thuộc |01–09, board/dây nối/lấy mẫu đã kiểm chứng |
| Ước lượng |1–2 ngày, chưa tính sửa lỗi |
| Tiến độ |[Dòng10](PROGRESS.md) |

## Kết quả và đầu ra

Có hướng dẫn tái hiện, tests và bằng chứng thật theo [kiến trúc](MQTT_ARCHITECTURE.md): MQTT telemetry/lệnh, HTTPraw và browser HTTP/WS. Thiết bị giả chỉ chứng minh phần mềm; cần broker/board thật để nghiệm thu tương ứng.

Không sửa tính năng lớn trong PR nghiệm thu. Phát hiện lỗi thì dùng fix/<scope>-<description> riêng rồi kiểm tra lại.

Viết docs/integration/DEVICE_INGESTION_RUNBOOK.md khi nghiệm thu; giữ commit, firmware/config, board, môi trường server/browser và log không nhạy cảm. Cập nhật giai đoạn02/07/08, PROGRESS, FINAL_VERIFICATION, CHANGELOG. Raw thật có thể lưu ngoài Git, chỉ commit mẫu/log được phép cùng hash và hướng dẫn truy cập.

## Chuẩn bị

- [ ] Cây làm việc sạch, ghi SHAdev và build firmware đúng SHA/cấu hình.
- [ ] Có GPIO/flash/PSRAM/rate đo từ Tân; thiếu ghi rõ.
- [ ] LAN, broker1883dev hoặc8883TLS, backend8000, dashboard5173 đúng địa chỉ host/container/ESP32.
- [ ] DB/vùng lưu/tài khoản kiểm thử riêng, không gây lỗi lên dữ liệu nhóm.
- [ ] Ghi kỳ gửi, ngưỡng dữ liệu cũ, cửa sổ raw, hàng đợi, retry và hạn gửi nốt.
- [ ] Ghi phiên bản broker/client, topic/QoS/retain, ACL/TLS, keepalive và tiến trình nhận MQTT.
- [ ] Không Internet vẫn chạy; không public broker/tắt tường lửa để né lỗi.
- [ ] Simulator là SYNTHETIC; DEVICE chỉ khi thật sự dùng cảm biến.

## Ma trận nghiệm thu

| ID | Kịch bản | Bằng chứng cần |
|---|---|---|
| E01 | Khởi động backend/browser, chưa bật ESP32 | Backend có kết nối nhưng thiết bị chưa có dữ liệu mới, không báo đang ghi. |
| E02 | Simulator đi hết vòng đời phiên | Nhãn nguồn và telemetry/WS/raw/xuất khớp; chỉ chứng minh phần mềm. |
| E03 | HTTPStart → lệnhMQTT → ACK → telemetry | Đúng DEVICE/phiên/timestamp, có mẫu mới trên dashboard; PUBACK chưa là đã thực thi. |
| E04 | Thu raw, Stop/gửi nốt rồi xuất | Đối chiếu batch cuối, số mẫu, hash, đơn vị, thứ tự/null với log board. |
| E05 | Wi-Fi mất ngắn, hàng đợi còn chứa | Vẫn lấy mẫu, gửi bù không trùng, telemetry trở lại trực tiếp. |
| E06 | Wi-Fi mất lâu, hàng đợi đầy | RAM hữu hạn, khai mất/gap, không báo đủ sai. |
| E07 | Backend ghi nhưng client mất ACK | Retry cùng ID/nội dung, file/số mẫu chỉ một lần. |
| E08 | Rút rồi nối lại cảm biến | Null/trạng thái/tuổi đúng, không số cũ hợp lệ hoặc sập hệ thống. |
| E09 | Stop khi còn dữ liệu chờ hoặc thiết bị mất mạng | STOPPING có hạn, đủ/thiếu đúng bằng chứng, UI không treo. |
| E10 | ESP32 reboot trong phiên | Không trộn epoch/phiên, ghi rõ gián đoạn. |
| E11 | Backend khởi động lại | Phục hồi phiên/chỉ mục/file, đọc lại được bản cũ. |
| E12 | Sai schema/phiên/nguồn hoặc quá giới hạn | HTTP/MQTT báo đúng, không ghi dở hoặc sang nguồn khác. |
| E13 | Hai thiết bị/nguồn gửi xen kẽ | Dashboard/bản ghi không trộn thiết bị, phiên hoặc nguồn. |
| E14 | So rate/jitter khi bật/tắt mạng và Serial | Có số đo thật; gap do truyền phải được ghi. |
| E15 | Broker mất/restart, HTTP backend còn | Không live/ghi giả; raw/query/xuất theo quy tắc, nối lại không chạy Start cũ. |
| E16 | Backend restart khi broker/thiết bị còn | Phục hồi lệnh chờ, không dùng PUBACK thay xử lý; không nhận/DB/WS đôi. |
| E17 | Chặn riêng HTTPraw, MQTT còn | Telemetry/lệnh có thể chạy, raw đầy/mất phải báo, RAM hữu hạn. |
| E18 | Tổng kếtMQTT trước/sau raw cuối, lệnh/ACK lặp | Cùng số mẫu/mức đủ, một epoch/batch cuối, không release raw nhầm. |
| E19 | Sai tài khoản/ACL, giả DEVICE từ SYNTHETIC | Không gửi/nhận trái quyền, topic/body lệch bị chặn, không lẫn bản ghi. |
| E20 | Lệnh/presence cũ sau reconnect/reboot | Không tự Start/live; bỏ boot/generation/nonce cũ. |
| E21 | Lỗi sau lưu lệnh trước phát hoặc trước lưu ACK | Retry cùng ID/thời hạn, phục hồi trạng thái không nhân đôi phiên. |

Mỗi lần thử phải dài hơn cửa sổ hiệu chuẩn/dữ liệu cũ/retry đang kiểm tra. Có ít nhất một lần ổn định nhiều phút, đối chiếu tổng số mẫu và ghi thời lượng thật; không điền PASS hoặc con số đẹp.

## Ghi kết quả

- [ ] E01–E21 có PASS/FAIL/NOT_RUN, lệnh/thao tác, log/ảnh và điều kiện; thử quyền/lệnh cũ/lỗi chỉ trên môi trường tạm.
- [ ] Đếm từ raw thật, tách đã thu/đưa queue/bỏ/nhận; không chỉ tin số UI.
- [ ] Kiểm tra gap/NaN/null/thứ tự/đơn vị/đồng bộ; đủ số file chưa có nghĩa đúng dữ liệu.
- [ ] Backend/AI/frontend tests+build, firmware build và Compose đạt trên SHA cuối.
- [ ] Tích hợp broker thật có quyền/nối lại/timeout/ca lỗi; mockclient/build không thay kiểm thử MQTT.
- [ ] CI đạt, sửa mới phải chạy lại phần ảnh hưởng, không chép kết quả SHA cũ.
- [ ] Hướng dẫn cho laptop và browser máy LAN khác, secret local, đường lưu/xuất và lỗi từng kênh; không secret trong bằng chứng.
- [ ] Reviewer tái hiện từ README/hướng dẫn, không cần lịch sử chat.

## Cổng hoàn thành và main

- [ ] Giai đoạn02 có bằng chứng trực quan thật.
- [ ] Giai đoạn07 có MQTT/ACK/đồng bộ thật và ngắt/nối.
- [ ] Giai đoạn08 có raw thật, Start/Stop và xuất đối chiếu.
- [ ] Giai đoạn00/03–06 chỉ DONE khi có bằng chứng tương ứng, không suy từ07.
- [ ] Giai đoạn09 chưa DONE chỉ vì ghi dữ liệu xong; cần đợt thu riêng.
- [ ] Tracker/giai đoạn khớp, ghi giới hạn; không tự gọi sẵn sàng thi đấu.
- [ ] Commit gợi ý: `chore: kiểm tra toàn luồng nhận và ghi dữ liệu thiết bị`.
- [ ] Sau merge vào dev, chủ repo xét PRdev→main; không push trực tiếp hoặc tự merge ngoài quyết định.

## Khôi phục và nhật ký

Giữ raw/log khi lỗi, sửa/hoàn tác bằng PR có phạm vi. Không xoá volume hoặc reset lịch sử nhánh bảo vệ.

| Ngày/SHA | Kịch bản | Lệnh/thao tác/bằng chứng | Kết quả |
|---|---|---|---|
|—|E01–E21|Chưa thực hiện|NOT_RUN|

Phạm vi kết thúc ở nhận/ghi dữ liệu. Thu dataset, xử lý và ML lập kế hoạch riêng từ giới hạn đã kiểm chứng.
