# Tiến độ nhánh tích hợp thiết bị

Cập nhật2026-11-05, Asia/Saigon. [Kế hoạch](README.md), [kiến trúc](MQTT_ARCHITECTURE.md). Mốc lập kế hoạch332f249; bắt đầu03 trên d80cc0e.

## Hiện tại

- **0.3.25 đo thật chưa đạt; đang dùng bản thử0.3.26:** lượt thật chỉ3/45gói HR53,6–107,9, dù thu/truyền đầy đủ. Không đánh dấu tối ưu xong. Đã tìm ca tái hiện một cửa sổ yếu làm mất cổng chống nhảy nửa nhịp;0.3.26 giữ lịch sử có giới hạn và không phát số cũ.46ca core+20toàn dải+46hình dạng,8tích hợp,89driver/12snapshot và header/build đạt. Vòng mô phỏng mới không tăng lỗi, nhưng chưa kiểm độ đúng0.3.26 trên cổ tay và chưa có reference từng cửa sổ. Không mở thêm lượt người trong vòng này; chưa push/merge. [Bàn giao](05-HR-TRACK-SWITCH.md).

- **0.3.25 đang kiểm cổ tay:** thêm phép chấm độ lặp hình dạng vào bằng chứng chọn chu kỳ từng kênh, không ép theo nhịp người dùng. Seed mô phỏng mới giảm lỗi lớn5→0, nhiễu không tuần hoàn nhận nhầm197→49; dữ liệu BIDMC đã xem giảm lỗi lớn76→34, có giảm coverage. Nhiễu quang tuần hoàn vẫn là giới hạn.111ca core/range/shape,8ca tích hợp và kiểm driver/capture/header/build/nạp đạt; nhận5frame DEVICE sau nạp. Chưa nghiệm thu độ đúng cổ tay; bản thử có thể để trống nhiều hơn. [Chi tiết](05-HR-TRACK-SWITCH.md). Chưa push/merge.

- **Lượt kiểm cổ tay0.3.24 KHÔNG ĐẠT:** chỉ7/45gói HR41,3–43,8; Trung không chấp nhận số đo. Raw đủ2.252 mẫu, không lỗi thu/truyền mới; so cùng raw bằng0.3.23 và0.3.24 cho đầu ra giống nhau. Smoother chỉ cải thiện độ trễ mô phỏng, không xử lý chọn nhầm chu kỳ trên cổ tay.0.3.24 vẫn là bản thử trên ESP, chưa chốt/rollback, chưa push/merge. Không yêu cầu đo lặp hoặc tự tiếp tục nạp thêm trong vòng này. [Bằng chứng](05-HR-TRACK-SWITCH.md).

- **2026-11-08 buổi tối, HR0.3.24:** thêm làm mượt thích nghi khi5 ứng viên mới tạo xu hướng đều; không đổi chọn chu kỳ hoặc lấy105–115 làm số đích.45 ca core+20 ca toàn dải đạt; nhịp ramp mô phỏng giảm độ trễ, nhưng MAE BIDMC đã xem tăng nhẹ0,858→0,874bpm, lỗi lớn giữ76 và mask nhận giữ nguyên. Đã build/nạp và nhận5gói DEVICE đúng phiên bản. Chưa nghiệm thu toàn dải/cổ tay; lỗi nhận nhầm dao động chậm còn tồn tại. Không đổi GSR/IMU/schema/FEforecast; chưa commit/push/merge. [Kết quả và đánh đổi](05-HR-TRACK-SWITCH.md). Các mốc0.3.23 bên dưới là lịch sử.

- **2026-11-08, Trung chốt HR0.3.23-tracker:** giữ nguyên thuật toán và kết quả lượt cuối bên dưới. Đã bỏ5 env thử,7 file dư cùng nhánh cấu hình/worker cũ; env mặc định và alias tracker cùng dùng bản đã chốt. 4env build,4tổ hợp header,45ca core,64FE,111backend,15AI và các bài driver/protocol đạt. Không nạp lại ESP, không đổi GSR/IMU/cấu hình Wi-Fi, chưa commit/push/merge. [Phạm vi và kiểm chứng dọn mã](05-CLEANUP-AUDIT.md).

- **2026-11-08, đã kiểm 0.3.23 trên cổ tay:** đủ 45 frame; sau 4 frame đầu chưa có HR, 41 frame còn lại liên tiếp 68,8–76,6 bpm. FE parser nhận đủ, không dùng dự báo, không trống sau HR đầu tiên; không có lỗi mạng mới. Sửa trộn smoother khi đổi chu kỳ đã được kiểm bằng hai test trước/sau và replay khóa input; raw mới không có chuyển lớn nên không quy toàn bộ coverage tăng cho sửa này. 45 core, 8 tích hợp, 6 capture, 4 tổ hợp header/build/upload đạt. Giữ 0.3.23, không mở thêm lượt đo; độ đúng cổ tay/độ tin cậy lâu dài và nhánh 5 chưa nghiệm thu. Chưa push/merge. [Bàn giao](05-HR-TRACK-SWITCH.md).

## Lịch sử trước khi chốt HR

- **2026-11-08, chẩn đoán mất dữ liệu HR:** nạp 0.3.22, giữ core HR 0.3.20; thêm RSSI/lỗi socket vào Serial. Dây USB mới thu đủ raw nhưng lượt cổ tay chỉ 13/60 frame WS; chưa có số đếm tham chiếu. Kiểm không yêu cầu tiếp xúc da, bật raw 60 giây nhận 59 frame/3.001 mẫu. Chờ lượt cổ tay để so log mới, không cần đếm mạch. 43 core, 6 capture, 4 tổ hợp header/build/upload đạt. HR và kết nối chưa nghiệm thu; chưa push/merge. [Chi tiết](05-HR-LINK-DIAGNOSIS.md).

- **2026-11-07, vòng xử lý nhận nhầm HR:** bản thử 0.3.21 không đạt ở lượt cổ tay mới (5/45 frame có HR, 42,9–43,3 bpm). Đã loại thay đổi không đạt, khôi phục core 0.3.20; nạp cấu hình Wi-Fi nhà, broker/backend healthy và nhận 5 frame DEVICE qua WebSocket. 43 ca core, 8 ca tích hợp, 4 tổ hợp header và build/upload đạt. HR ổn định, gần đúng vẫn chưa đạt; chưa push/merge. [Bằng chứng và các cách lọc đã loại](05-HR-HARMONIC-REJECTION.md). Các mục dưới là lịch sử.

- **Bản mới nhất0.3.20-tracker:** đã nạp và thử cổ tay45giây, đủ45gói,28gói có HR thiết bị và8gói được FE ghi“Tạm tính”. Sau HR đầu tiên lớp hiển thị không bị trống trong lượt thu; dữ liệu gốc giữ null. Thêm xác nhận cú nhảy/startup80↔40, nhưng HR còn đoạn thấp43,7–52 nên chưa kết luận hết nhận nhầm nửa nhịp/đúng sai.39coretest,64FE,build và tích hợp đạt; chưa CI/push/merge. [Bàn giao liền mạch có hạn](05-HR-CONTINUITY.md). Các mục dưới giữ lịch sử.

- **Theo dõi chu kỳ HR, bản mới nhất0.3.18-tracker:** đã hoàn tất code, kiểm thử, build/nạp và hai lượt cổ tay. Lượt cuối nhận45gói/45giây,17gói có HR;13gói cuối liên tiếp70,3–72,2bpm. GSR/IMU45/45, mạng không lỗi. Thẻ hiển thị ở36/45gói khi tính thêm19gói giữ có tuổi, không gọi là HR mới. Còn khoảng thiếu, chưa có HR tham chiếu và còn nhận nhầm nhiễu trong benchmark; không đánhDONE HR/nhánh5. [Bàn giao tracker và cách chạy](05-HR-CYCLE-TRACKER.md). Các mục demo trước dưới đây giữ lịch sử.

- **Kết quả vòng demo HR mới nhất:** hai lượt cổ tay đã xong. Lượt cuối nhận **45 gói WS/45 giây**, GSR/IMU đủ, wifi/mqtt/sync ổn định nhưng HR 0/45. Lượt trước driver có HR ở 9/45 bản chụp nhưng đường truyền ngắt trước lúc có HR; chưa quy được nguyên nhân. Đã kiểm riêng mạch trên bàn 70 giây. Hoàn tất code/test/nạp demo, **chưa đạt HR luôn có số**, không gán số giả hoặc tự mở thêm lượt đo. [Bàn giao demo](05-HR-DEMO.md).

- **Theo mục tiêu demo mới, 2026-11-07:** đã triển khai/nạp `0.3.16-demo` ưu tiên cập nhật HR tương đối, median3/EMA trên ứng viên mới; FE ghi nhãn và tuổi số giữ tối đa 10 giây, không lấp dữ liệu gốc. Đã kiểm phần mềm, hai build và nhận lại 5 gói WS DEVICE thật có GSR/IMU/phiên. Chờ một lượt cổ tay sẵn sàng, chưa tuyên bố HR đúng/ổn định. [Bàn giao demo](05-HR-DEMO.md). Không đổi schema của Trung hoặc phép đo GSR/IMU.

- **Vòng thuật toán HR yếu, 2026-11-07:** triển khai/chấm hai ứng viên offline trên bốn trace cổ tay, BIDMC đã xem và mô phỏng khóa seed. B qua development nhưng vòng seed mới nhận nhầm 165 thành 81,656 bpm ở một cửa sổ; không đạt điều kiện để nạp. Đã chạy 41 ca công cụ, lưu source/input hashes, báo cáo và hình. Không đổi firmware/GSR/IMU/schema, không mở vòng đo mới. [Kết quả và giới hạn](05-HR-WEAK-SIGNAL-EXPERIMENT.md). HR cổ tay và nhánh 5 chưa DONE.

- **Hoàn tất số lượt thu HR, 2026-11-07, 15:22:** Trung yêu cầu B2 đo lại và đã thu đủ 45 giây. Bộ chính A1/B1/A2/B2 đo lại có 9.008 mẫu raw, 160 frame WS, GSR/IMU đầy đủ; B2 gián đoạn 1.673 mẫu giữ riêng. Có manifest/hash, hình và replay trên bốn trace đầy đủ. Thuật toán đối chứng vẫn chưa chấp nhận HR; chưa có HR tham chiếu hoặc số đo nhiệt. Kết thúc bước thu, chuyển tối ưu thuật toán offline. [Bàn giao cuối bước thu](05-HR-DATA-HANDOFF.md). Chưa DONE HR hoặc nhánh 5.

- **Chốt đợt thu HR cổ tay, 2026-11-07:** A1/B1/A2 đủ 45 giây và 40 frame WS mỗi lượt, GSR/IMU đủ, HR chưa được bản đối chứng chấp nhận; B2 chỉ giữ phần 33,413 giây và không tính là lượt đầy đủ. Đã Clean/build/nạp lại trước A2, không đổi thuật toán hay điện năng. Có manifest/hash và so cùng cửa sổ; chưa chứng minh tác dụng che sáng lặp lại hoặc sai số HR thật. Kết thúc thu trong vòng này, chuyển sang thuật toán offline. [Bàn giao dữ liệu](05-HR-DATA-HANDOFF.md). Sự kiện chip nóng chưa được xác nhận đã xử lý; chưa DONE nhánh 5.

- **Dừng đo trên thiết bị, 2026-11-07:** Trung rút USB vì chip ESP32-S3 nóng, không thấy khét/khói/biến dạng. B2 gián đoạn, A2 tạm dừng; không quy đổi phiên thành lỗi tự crash. Code có tắt modem sleep là yếu tố cần đánh giá, chưa xác định nguyên nhân nhiệt. Đã sửa công cụ giữ partial capture, 6 test đạt; chưa nạp firmware mới sau báo nóng. [Checkpoint nhiệt](05-THERMAL-CHECK.md). Có thể tiếp tục phân tích HR offline, chưa yêu cầu cấp nguồn/đeo đo.

- **Vòng HR theo dữ liệu yếu, 2026-11-07:** đã dọn phần thừa có bằng chứng và replay bốn trace; baseline/strict/balanced đều chưa cứu được hai trace cổ tay khó. Kế hoạch mới tập trung xử lý nền/xung và cổng chọn chu kỳ bớt loại cứng, giữ cách đặt nhẹ, không đè. GSR/IMU giữ nguyên. [Kế hoạch và tiêu chí](05-HR-ROOT-CAUSE-PLAN.md), [báo cáo dọn mã](05-CLEANUP-AUDIT.md). Chưa nạp thuật toán mới, chưa xác nhận sai số HR thật hoặc CI từ xa.

- **HR cổ tay chưa đạt, 2026-11-07:** thử400Hz/avg8/0.3.15 cũng0/39 HR dù sensing/mạng ổn định; chưa có cấu hình đủ lặp lại. Đã quay về0.3.13-led10/200Hz/avg4 làm đối chiếu, kiểm20s/1.000 mẫu và14 frame WS GSR/IMU đạt. Code7 env/kiểm hồi quy đạt; cần nhịp tham chiếu để đánh giá tiếp có cơ sở. [Checkpoint](05-WRIST-SAMPLING-TRIAL.md). Nhánh05 chưa DONE, chưaCI/push.

- **Bước 4 đã thử board:** 0.3.12, hybrid C++ khớp policy Python, 5 build và kiểm hồi quy đạt. Đầu ngón tay có 38/39 HR qua WS; cổ tay vẫn 0/39, GSR/IMU đủ. Có lỗi I2C/init chặn khoảng 1 giây giữa hai lượt cần xử lý. [Bằng chứng hiện tại](05-PPG-FIRMWARE-TRIAL.md). Nhánh 05 chưa DONE, chưa CI/push mới; các cập nhật dưới là lịch sử.

- Cập nhật mới: bước3 đã chọn ứng viên HR offline `hybrid_strict` qua2 vòng kiểm, chưa tích hợp/nạp. [Bằng chứng và việc cần làm trước thử board](05-PPG-QUALITY-EVALUATION.md). ESP vẫn0.3.11, HR cổ tay và nhánh05 chưa nghiệm thu/DONE.

- Cập nhật2026-11-06: HR cổ tay vẫn đang tối ưu, chưa nghiệm thu. Board0.3.11 đã có log I2C; bước2 đối chiếu offline đã chạy, chưa nạp bộ HR mới. [Bằng chứng và hướng bước3](05-PPG-ALGORITHM-EVALUATION.md). Nhánh05 chưa DONE, chưa có CI/commit mới cho lượt này.

- Yêu cầu mới Trung/Tân: [npm run dev](05-ONE-COMMAND-DEV.md) tự bật dịch vụ và mở phiên local, không DevTools/token. Đã thử root/frontend và stop/start trên máy Trung, cookie tự động→WS nhận DEVICE thật. Chờ xác nhận UI và thử trên máy Tân; nhánh05 chưa DONE.

- Kế hoạch [PR #8](https://github.com/namtrungdn310/ASD-EASE/pull/8) merge0bcd833.
- Cleanup [PR #9](https://github.com/namtrungdn310/ASD-EASE/pull/9) merge86cd09f, CI cuối c764210 đạt6/6; chưa thay nghiệm thu phần cứng.
- Code02 merge [PR #10](https://github.com/namtrungdn310/ASD-EASE/pull/10) tại ea959ef ngày2026-10-22 theo quyết định chủ repo. Head trước merge6/6, frontend26/transport18 đã đạt; còn thiếu ảnh/log browser độc lập.
- Nhánh03 đã merge [PR #12](https://github.com/namtrungdn310/ASD-EASE/pull/12) tại752bd5d ngày2026-10-31, CI head af61856 đạt6/6 trước merge.
- Nhánh04 đã merge [PR #13](https://github.com/namtrungdn310/ASD-EASE/pull/13) vào dev tại7ff5a2c, CI PR/dev đạt6/6 ở mốc đó. Xem [bàn giao](04-HANDOFF.md)/[cách chạy](04-SETUP.md); chưa thay nghiệm thu ESP32.
- Nhánh05: code PR #15 đã merge; sau PR #17, tiếp tục sửa trên `fix/esp32-local-mqtt-integration` từ dev46d4e2d. Trung đã nạp COM7 thành công, backend sync1 và WS nhận3 frame DEVICE/ESP32-001 thật qua hotspot iPhone. Đang kiểm tra Serial, còn Dashboard/StartStop/lỗi/tài nguyên; xem [rà soát](05-REVIEW-PR17.md), [bước đang làm](05-LOCAL-BRINGUP.md), [ma trận](05-VERIFICATION.md).
- Trung đã giao Codex làm nốt03 thay từng-file walkthrough. Các nhánh code sau vẫn có thể học từng file theo yêu cầu.
- Hướng: MQTT telemetry/lệnh/ACK/đồng bộ, rawHTTP, browserHTTP/WS. Đo wiring/rate/đồng bộ/RAM ở05/07 vẫn còn; không dùng mẫu để nghiệm thu thật.
- Cần phối hợp Tân về board/GPIO và lịch sửa main.cpp/board_config.h.

## Mã trạng thái

| Mã | Ý nghĩa |
|---|---|
| TODO |Chưa bắt đầu, xem phụ thuộc trước |
| IN_PROGRESS |Đang làm |
| READY_FOR_REVIEW |Local đã kiểm tra, chờ review/commit/push/PR |
| IN_REVIEW |Có PR, chờ CI/review |
| WAITING_HARDWARE |Phần mềm có thể thử, thiếu bằng chứng board |
| BLOCKED |Có việc cụ thể đang chặn |
| DONE |Đã merge và đủ nghiệm thu của nhánh |

Merge code không tự là hoàn tất giai đoạn. Chờ board thì ghi rõ, không mặc định DONE.

## Bảng nhánh

| ID | Kế hoạch/nhánh | Phụ thuộc | Trạng thái | Bắt đầu | Kết thúc | PR | Kết quả/việc chờ |
|---|---|---|---|---|---|---|---|
| 01 | [chore/repository-integration-cleanup](01-repository-integration-cleanup.md) | PR #8 | DONE | 2026-10-18 | 2026-10-18 | [#9](https://github.com/namtrungdn310/ASD-EASE/pull/9) | Đã merge86cd09f, CI6/6; dây nối chưa xác nhận. |
| 02 | [fix/frontend-live-connection-status](02-frontend-live-connection-status.md) | 01 | BLOCKED | 2026-10-18 | — | [#10](https://github.com/namtrungdn310/ASD-EASE/pull/10) | Code mergeea959ef, CI6/6; chỉ còn chặn nghiệm thu trực quan, không chặn03. |
| 03 | [docs/device-ingestion-contract](03-device-ingestion-contract.md) | 01 | DONE | 2026-10-22 | 2026-10-31 | [#12](https://github.com/namtrungdn310/ASD-EASE/pull/12) | Merge752bd5d, CI head af61856 đạt6/6. Phần cứng05/07 vẫn chờ. |
| 04 | [feature/backend-session-lifecycle](04-backend-session-lifecycle.md) | 03 | DONE | 2026-10-31 | 2026-11-01 | [#13](https://github.com/namtrungdn310/ASD-EASE/pull/13) | Merge7ff5a2c sau6/6 CI; broker/phiên/ACK bền và simulator đã kiểm thử. |
| 05 | [feature/firmware-telemetry-client](05-firmware-telemetry-client.md) | 03/04;02 cho UI | IN_PROGRESS | PR #17 / dev46d4e2d | — | #15 và #17 đã merge; lượt sửa mới chưa PR | Đã nạp board thật, MQTT/backend sync1, WS nhận3 frame DEVICE. Đang kiểm tra Serial rồi Dashboard/StartStop/lỗi/tài nguyên và F01–F19. |
| 06 | [feature/backend-raw-ingestion](06-backend-raw-ingestion.md) | 03/04 | TODO | — | — | — | Raw HTTP lưu bền/chống trùng, đối chiếu tổng kết. |
| 07 | [feature/firmware-raw-batching](07-firmware-raw-batching.md) | 05/06 và số đo mẫu | TODO | — | — | — | Raw HTTP song song MQTT, đo rate/RAM/gap. |
| 08 | [feature/backend-recording-export](08-backend-recording-export.md) | 06;07 trước nghiệm thu thật | TODO | — | — | — | Đọc/xuất/bản mô tả, không cần broker online. |
| 09 | [feature/frontend-recording-control](09-frontend-recording-control.md) | 02/04/08 | TODO | — | — | — | UI HTTP/WS, không browser MQTT. |
| 10 | [chore/e2e-device-ingestion](10-e2e-device-ingestion.md) | 01–09 và board | TODO | — | — | — | E01–E21, có broker/ACL/lỗi từng kênh, không chỉ giả lập. |

## Việc cần phối hợp

| ID | Việc | Người | Ảnh hưởng/hành động |
|---|---|---|---|
| B01 |GSR code hiện GPIO7 sau PR #11; chưa wiring/board/flash |Tân |05 thật; đã sửa ghi chú4 cũ, cần ảnh/log |
| B02 |PPG FIFO thực, mất mẫu/timestamp/đồng bộ |Tân+IT |05/07 thật; nominal50/50/20 chưa là số đo,04 dùng mẫu trước |
| B03 |Lệnh/ACK/đồng bộ, Stop/gửi nốt, thứ tự raw |IT |Đặc tả03 đã có;04–07 triển khai/tests |
| B04 |JSONSerial khác API |IT |05 cần bộ đóng gói riêng |
| B05 |Browser/board cho nghiệm thu |Trung+Tân |02 trực quan,05/07/10 thật;2026-10-20 discovery=[]/No browser is available, cần kiểm tra tay hoặc công cụ |
| B06 |Tương thích broker/Python/Arduino, quyền/TLS/bộ nhớ |IT+Tân |04 đã thử Mosquitto2.0.22/Paho2.1.0/QoS1/ACL thật trên máy; Arduino, TLS triển khai và RAM board còn05/10 |

## Nhật ký chính

| Ngày | Việc | Bằng chứng và giới hạn |
|---|---|---|
|2026-10-18|Lập10 nhánh|10 tên hợp CI,230 mục mở,62 link;25 tài liệu giai đoạn, chỉ kế hoạch |
|2026-10-18|Cleanup hỗ trợ|Quét conflict đúng mã0/1/128, env/Compose/ignore đạt;4 file local giữ hash |
|2026-10-18|5 header Trung viết|Firmware/4 tổ hợp header/frontend/Compose đạt; chuẩn bị PR #9 |
|2026-10-18|Rebase sau PR #8|3 commit lên0bcd833, tree giống nhau;4 file giữ hash, CI7ff18516/6 trước rebase |
|2026-10-18|Tạo02 từ86cd09f|Code cleanup đã review,4 file IDE local giữ; bắt đầu connection.ts |
|2026-10-18|connection.ts/validation.ts|TypeScript đạt, validation29 phép kiểm tra |
|2026-10-18|parseTelemetry.ts|TypeScript/137 phép kiểm tra đạt |
|2026-10-18|telemetryStream.ts|TypeScript/563 phép kiểm tra, có vòng lặp bộ đệm |
|2026-10-18|useLiveTelemetry.ts|Build/89 phép kiểm tra mô phỏng Node; chưa browser, bundle>500kB chỉ cảnh báo |
|2026-10-20|DeviceStatus.tsx|Build/74 phép kiểm tra render server; chưa bố cục/trình đọc màn hình |
|2026-10-20|Dashboard.tsx|16 tests Node/Vite đạt, hook mạng thay bằng mẫu; chưa browser |
|2026-10-20|Vòng đời và đường truyền|Frontend26, backend13, AI15, audit0, header4/4, transport18/18 đạt; React/jsdom dùng socket/timer giả, mạng riêng thật; browser discovery=[] |
|2026-10-22|Bắt đầu03|PR10/11 đã merge, devd80cc0e, chỉ chuẩn bị đặc tả |
|2026-10-22|Kế hoạch MQTT|Đồng bộ03–10,52 link/tên nhánh/21 ca E2E kiểm tra; chưa runtime |
|2026-10-31|Bàn giao03|17 ca schema+11 control+9 biến thể sai/thời gian/16 tham chiếu đạt; backend13/AI15 đạt; chưa broker/board/JCS thật |
|2026-10-31|Việt hoá|Backend13/AI15/frontend26 và build đạt; ví dụ17+11/9 ca sai đạt. Logic54 file Python/13 file C++ và JS giữ nguyên;67 Markdown/164 link hợp lệ. Không đổi trạng thái hoặc lịch sử Git |
|2026-10-31|Đưa03 lên GitHub|Commit5dd0d0e và PR #12 vào dev theo yêu cầu Trung; kiểm tra local đạt lại. Hai schema định dạng riêng giữ trên máy, không trong PR. CI/merge tra trực tiếp PR; không suy từ kết quả local. |
|2026-10-31|Merge03|PR #12 squash752bd5d sau6/6 CI trên af61856, dev local đồng bộ; giữ hai schema định dạng riêng |
|2026-11-01|Bàn giao04|Backend55/AI15/frontend26+build; HTTP19 frame; MQTT7 nhóm qua Mosquitto thật; migration/restore/rollback và Compose đạt. Chưa push/CI từ xa/merge hoặc phần cứng |
|2026-11-01|Rà soát trước PR04|Backend56, sửa kiểm tra nonce ACK và credential Unicode; HTTP19 frame/MQTT7 nhóm, firmware build/header4, AI15/frontend26+build/audit0 đạt. Trung yêu cầu push và merge vào dev sau CI, giữ main nguyên trạng |
|2026-11-01|Push04|Commit076aa83, PR #13 vào dev. Backend56 đạt thêm trên Linux container và Docker backend build đạt; CI/merge tra trực tiếp PR, không suy từ local |

Các số trong nhật ký là kết quả lịch sử theo phạm vi, không chép sang SHA mới như đã chạy.

Ngày2026-11-03: rà soát dev1e73aea sau PR #14 và hoàn thiện code05 trên feature/firmware-telemetry-client-completion theo yêu cầu Trung. Build2 env/header4, native30, MQTT C++7 nhóm/Python7 nhóm, backend61/AI15/frontend26+build+audit0 và HTTP19 frame đạt local. Đã push d1101c5, mở PR #15 theo yêu cầu đưa vào dev; CI/merge tra PR. Board ở chỗ Tân. Chi tiết và các ca NOT_RUN_HW ở [05-VERIFICATION](05-VERIFICATION.md).

## Sau mỗi buổi

- [ ] Tick việc đã làm trong đúng kế hoạch.
- [ ] Ghi lệnh/kết quả/ảnh/log và commit tương ứng.
- [ ] Cập nhật trạng thái/PR/việc chặn.
- [ ] Quyết định đổi quy ước ghi tài liệu nguồn.
- [ ] Chỉ cập nhật giai đoạn khi có bằng chứng thật.
- [ ] Nhánh đã merge thì cập nhật dev rồi tạo nhánh mới.

## Trước PRdev→main

- [ ] MốcM1–M4 có bằng chứng, xử lý việc chặn.
- [ ] Telemetry/raw thật qua LAN, nguồn/thời gian đúng.
- [ ] Retry/nối lại/Stop/restart không nhân đôi hoặc báo đủ sai.
- [ ] Có thử broker/client/quyền/lệnh cũ và lỗi từng giao thức; PUBACK khác ACK thực thi/lưu.
- [ ] Xuất/đọc lại được, khai mất mẫu, không thay raw bằng EMA.
- [ ] CI đạt, không xung đột, docs khớp code.
- [ ] Chủ repo review cuối và mở PR.

Hoàn tất nhận/ghi dữ liệu không tự nghĩa có mô hình đã kiểm chứng hoặc sẵn sàng thi đấu.
