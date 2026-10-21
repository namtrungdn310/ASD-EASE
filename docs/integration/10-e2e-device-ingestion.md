# 10 — Nghiệm thu toàn luồng thiết bị, backend và recording

| Thuộc tính | Giá trị |
|---|---|
| Nhánh | `chore/e2e-device-ingestion` |
| Chủ trì | Trung — IT; Tân phối hợp phần cứng |
| Phụ thuộc | 01–09; có board/wiring/sampling đã kiểm chứng phù hợp |
| Ước lượng | 1–2 ngày, cộng thời gian xử lý lỗi nếu có |
| Theo dõi | [PROGRESS.md](PROGRESS.md), dòng 10 |

## Kết quả cần đạt

Một runbook tái hiện được, test tự động và bằng chứng thiết bị thật chứng minh tính đúng của ingestion/recording. Không chuyển việc sửa tính năng lớn vào PR nghiệm thu; lỗi phát hiện cần nhánh `fix/<scope>-<description>` riêng rồi quay lại kiểm tra.

## Đầu ra dự kiến

- `docs/integration/DEVICE_INGESTION_RUNBOOK.md` được viết khi nghiệm thu, mô tả command, setup và expected results thực tế.
- Test E2E qua API/WebSocket/storage/export, test failure/reconnect có thể chạy bằng fake-device.
- Bảng kết quả có commit SHA, firmware version, board/config, server/browser environment và các log không nhạy cảm.
- Cập nhật `docs/phases/PHASE_02_MOCK_END_TO_END.md`, phase 07/08, `PROGRESS.md`, `FINAL_VERIFICATION.md`, changelog.
- Evidence phần cứng raw có thể nằm ở storage ngoài Git; chỉ commit sample/log đã kiểm tra phù hợp và manifest/hash/path hướng dẫn truy cập.

## Chuẩn bị

- [ ] Working tree sạch, ghi SHA dev đang nghiệm thu, firmware build đúng SHA/config.
- [ ] Ghi GPIO/flash/PSRAM thực tế và measured sampling evidence từ Tân; thiếu thì ghi blocker.
- [ ] Dùng mạng LAN đã kiểm tra, backend port 8000, dashboard port 5173 và storage volume test riêng.
- [ ] DB/recording đang dùng của nhóm được giữ nguyên; fault injection dùng thư mục/DB tạm.
- [ ] Ghi kỳ telemetry, stale timeout, raw window, queue depth, retry/backoff và drain timeout để kết quả tái hiện được.
- [ ] Fake-device/simulator ghi nhãn SYNTHETIC; board gắn DEVICE chỉ khi dùng sample cảm biến thật.

## Ma trận nghiệm thu

| ID | Kịch bản | Bằng chứng và tiêu chí |
|---|---|---|
| E01 | Khởi động backend/browser, chưa bật ESP32 | Backend online nhưng device chưa live, không recording giả |
| E02 | Chạy simulator qua session lifecycle | Badge đúng, telemetry/WS/raw/export khớp; phần này chỉ chứng minh software path |
| E03 | ESP32 start -> ACK -> telemetry | DEVICE, timestamp session đúng, HTTP 202, dashboard nhận giá trị còn mới |
| E04 | Thu raw rồi stop/drain -> export | Final batch/count/hash/units/order/null đối chiếu log board, manifest complete đúng |
| E05 | Mất Wi-Fi ngắn hơn queue capacity | Sampling vẫn chạy; raw gửi bù không duplicate, telemetry trở lại live |
| E06 | Mất Wi-Fi dài quá queue capacity | RAM hữu hạn, loss/gap khai báo, recording không bị báo đầy đủ sai |
| E07 | Backend lưu batch nhưng client không nhận ACK | Retry cùng ID/payload, file/count chỉ một lần |
| E08 | Rút một cảm biến, cắm lại | null/status/age đúng; không số cũ valid, không crash cả hệ thống |
| E09 | Stop khi còn backlog hoặc device offline | STOPPING hữu hạn -> complete/incomplete theo bằng chứng, không treo UI |
| E10 | Reboot ESP32 trong phiên | Epoch/session không trộn, phiên gián đoạn được ghi rõ |
| E11 | Restart backend | Session/index/file phục hồi theo policy, recording cũ đọc được |
| E12 | Sai schema/session/origin, quá giới hạn | HTTP lỗi đúng, không ghi partial hoặc vào sai nguồn |
| E13 | Hai nguồn/thiết bị xen kẽ | Dashboard/recording không trộn device/session/provenance |
| E14 | So rate/jitter khi tắt/bật network và Serial | Có số đo thực tế; transport không gây gap không được ghi nhận |

Thời lượng mỗi run cần dài hơn cửa sổ calibration/stale/retry đang kiểm tra. Ít nhất có một run ổn định nhiều phút với tổng counts đối chiếu; ghi thời lượng thực, không tự điền PASS hoặc con số đẹp.

## Ghi kết quả và kiểm tra dữ liệu

- [ ] Từng E01–E14 có PASS/FAIL/NOT_RUN, command hoặc thao tác, log/ảnh và điều kiện đo.
- [ ] Counts tính từ raw thực, không chỉ số counter UI. Tách samples acquired/queued/dropped/accepted khi có log để đối chiếu.
- [ ] Gaps, NaN/null, order, units và alignment đều được kiểm tra; tổng số file đúng chưa đủ chứng minh đúng dữ liệu.
- [ ] Backend tests, AI tests, frontend tests/build, firmware build và Compose config đều pass trên SHA cuối.
- [ ] Required CI pass. Nếu có fix mới, chỉ chạy lại phạm vi bị ảnh hưởng và các tiêu chí còn chưa chắc chắn, không chép kết quả SHA cũ thành mới.
- [ ] Cập nhật guide LAN cho cả laptop host và máy browser khác, credential local, đường lưu/export và cách xử lý session incomplete.
- [ ] Reviewer có thể tái hiện từ README/runbook, không cần lịch sử chat.

## Cổng hoàn thành phase và main

- [ ] Phase 02 có visual evidence thật; không bỏ qua blocker cũ bằng việc sửa status.
- [ ] Phase 07 có real ESP32 telemetry qua LAN và disconnect/reconnect.
- [ ] Phase 08 có raw thật, session start/stop và export đối chiếu mẫu.
- [ ] Phase 00/03–06 chỉ cập nhật DONE khi bằng chứng phần cứng tương ứng có đủ; không suy từ Phase 07.
- [ ] Phase 09 chưa DONE chỉ vì logger đã xong; dataset collection cần đợt thu/protocol riêng.
- [ ] Tracker và phase docs nhất quán; các vấn đề còn lại ghi rõ, không gọi bản này là competition-ready.
- [ ] Commit gợi ý: `chore: verify end-to-end device ingestion and recording`.
- [ ] Sau merge PR nghiệm thu vào dev, chủ repo xem xét PR `dev -> main` theo mốc ổn định; không push trực tiếp hay tự merge ngoài quyết định chủ repo.

## Rollback

Nếu fail do firmware/backend feature, giữ evidence và trở về phiên bản ổn định bằng PR sửa/revert có phạm vi. Giữ raw/log đã thu để phân tích; không xoá volume hay reset lịch sử protected branches.

## Nhật ký / bảng kết quả thực tế

| Ngày / SHA | Kịch bản | Command / thao tác / evidence | PASS / FAIL / NOT_RUN |
|---|---|---|---|
| — | E01–E14 | Chưa thực hiện | NOT_RUN |

Kết thúc scope này tại ingestion/recording. Kế hoạch dataset thực, preprocessing và ML được lập riêng từ dữ liệu/giới hạn đã kiểm chứng.
