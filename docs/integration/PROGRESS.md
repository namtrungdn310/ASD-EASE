# Tiến độ nhánh tích hợp thiết bị

Cập nhật2026-11-01, Asia/Saigon. Trung phụ trách phần triển khai. [Kế hoạch](README.md), [kiến trúc](MQTT_ARCHITECTURE.md). Mốc lập kế hoạch332f249; bắt đầu03 trên d80cc0e.

## Hiện tại

- Kế hoạch [PR #8](https://github.com/namtrungdn310/ASD-EASE/pull/8) merge0bcd833.
- Cleanup [PR #9](https://github.com/namtrungdn310/ASD-EASE/pull/9) merge86cd09f, CI cuối c764210 đạt6/6; chưa thay nghiệm thu phần cứng.
- Code02 merge [PR #10](https://github.com/namtrungdn310/ASD-EASE/pull/10) tại ea959ef ngày2026-10-22 theo quyết định chủ repo. Head trước merge6/6, frontend26/transport18 đã đạt; còn thiếu ảnh/log browser độc lập.
- Nhánh03 đã merge [PR #12](https://github.com/namtrungdn310/ASD-EASE/pull/12) tại752bd5d ngày2026-10-31, CI head af61856 đạt6/6 trước merge.
- Nhánh04 feature/backend-session-lifecycle đã triển khai và kiểm thử local, [bàn giao](04-HANDOFF.md)/[cách chạy](04-SETUP.md); READY_FOR_REVIEW, chưa commit/push/PR/merge. Broker thật chạy trong kiểm thử tạm, không phải firmware ESP32 đã kết nối.
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
| 04 | [feature/backend-session-lifecycle](04-backend-session-lifecycle.md) | 03 | READY_FOR_REVIEW | 2026-10-31 | — | — | Broker/nhận chung/phiên/lệnh bền/migration/xác thực/simulator đã kiểm thử local; chưa commit/PR/CI từ xa/merge. |
| 05 | [feature/firmware-telemetry-client](05-firmware-telemetry-client.md) | 03/04;02 cho UI | TODO | — | — | — | Client Arduino MQTT/ACK; cần thử QoS1 và board/LAN. |
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

Các số trong nhật ký là kết quả lịch sử theo phạm vi, không chép sang SHA mới như đã chạy.

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
