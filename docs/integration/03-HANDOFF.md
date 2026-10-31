# Bàn giao nhánh03 — đặc tả kết nối thiết bị

Ngày2026-10-31, múi giờ Asia/Saigon. Nhánh docs/device-ingestion-contract từ dev d80cc0e, HEAD trước bàn giao9a8401e.

**Phần đặc tả/ví dụ hoàn tất trên máy, READY_FOR_REVIEW; chưa commit/push/PR/merge.** Chưa DONE theo tracker vì còn review và merge.

## Nhánh này làm gì?

Viết quy tắc để ESP32 và backend hiểu nhau: đúng trường, đơn vị, phiên, lệnh và xác nhận lưu. Nhánh04/05 dựa vào đó để viết code. Chưa dựng đường truyền thực tế.

| File | Vai trò |
|---|---|
| [API](../API_CONTRACT.md) | Tra cấu trúc và phân biệt hiện có/dự kiến |
| [Nhận dữ liệu](../contracts/INGESTION_V1.md) | Thời gian, phiên, raw HTTP, thử lại, đủ dữ liệu |
| [MQTT](../contracts/MQTT_CONTROL.md) | Topic, Start/Stop, ACK và kết nối lại |
| [Ánh xạ driver](../contracts/DRIVER_MAPPING.md) | Chọn dữ liệu cảm biến, đổi đơn vị, việc cần đo |
| [Ví dụ](../contracts/examples.json) | Mẫu đúng/sai SYNTHETIC cho tests phía sau |
| [Công cụ kiểm tra](../contracts/check_examples.py) | Chỉ kiểm tra mẫu, không mạng/DB |
| [Hướng dẫn đọc](../contracts/README.md) | Thứ tự đọc và lệnh kiểm tra |
| [Kiến trúc](../ARCHITECTURE.md), [quyết định](../DECISIONS.md), [bộ dữ liệu](../DATASET_PROTOCOL.md) | Sơ đồ, lý do chọn và giữ nguồn/đơn vị/mẫu thiếu |
| [Kế hoạch03](03-device-ingestion-contract.md), [tiến độ](PROGRESS.md) | Phần đã làm, cần review và bước tiếp |
| [Giai đoạn07](../phases/PHASE_07_WIFI_BACKEND.md), [08](../phases/PHASE_08_DATA_LOGGER.md), [thay đổi](../CHANGELOG.md) | Đồng bộ điều kiện nghiệm thu, không tự đánh DONE |

## Kết quả kiểm tra của lần bàn giao

Chạy từ root bằng .venv. Tests dùng DB/vùng lưu riêng theo conftest, không production. Không bật broker/board.

```powershell
.\.venv\Scripts\python.exe docs/contracts/check_examples.py
Push-Location backend
..\.venv\Scripts\python.exe -m pytest -q
Pop-Location
Push-Location ai
..\.venv\Scripts\python.exe -m pytest -q
Pop-Location
git diff --check -- docs
```

| Mục | Kết quả ngày2026-10-31 | Chưa chứng minh |
|---|---|---|
| Ví dụ |17 ca schema hiện tại,11 mẫu control,9 biến thể sai bị từ chối; thời gian/số mẫu và16 tham chiếu kịch bản đạt | Broker, quyền, vòng đời thực tế hoặc JCS |
| Backend |13 tests PASS,1 cảnh báo Starlette/anyio về API cũ | MQTT dự kiến |
| AI |15 tests PASS,14 cảnh báo matplotlib/pyparsing | Phần cứng |
| Tài liệu |59 Markdown, không link local hỏng;25 giai đoạn/10 kế hoạch nhánh giữ nguyên | Runtime |
| Schema | AST telemetry.py/raw_batch.py khớp HEAD, chỉ có định dạng của Trung | Không sửa logic/schema để mẫu đạt |
| Diff | git diff --check -- docs đạt ở lần bàn giao | Không bao gồm khoảng trắng có trước trong code của Trung |

telemetry_nested_extra_gap và raw_adc_range_gap cố ý là ca hiện chấp nhận nhưng đích phải từ chối. Công cụ đạt không có nghĩa đã sửa hai thiếu sót kiểm tra đó. C01–C16 là yêu cầu kiểm thử tương lai, không E2E đã PASS.

## Chưa có bằng chứng

- Broker/client MQTT, quyền/ACL/TLS, DB chuyển đổi/lệnh chờ, lưu raw đồng thời/chống lỗi và mẫu JCS chưa triển khai.
- Tân chưa đo wiring/board/flash/PSRAM, rate/jitter/đồng bộ FIFO, hiệu chuẩn GSR và RAM đỉnh. GPIO7 là code hiện có, chưa xác nhận dây thật. Cổng này ở05/07;04 dùng giả lập trước.
- Giai đoạn02 còn quan sát trình duyệt. Không tự đánh giai đoạn00–24 DONE.
- Không review/merge thay chủ repo; hai schema Trung gõ vẫn là thay đổi local của Trung, không tự revert/stage vào PR tài liệu.

## Bước tiếp

1. Trung review quy tắc, giới hạn phát triển và phần quyền; không cần gõ lại docs.
2. Khi Trung yêu cầu: commit đúng tài liệu/mẫu/công cụ, kiểm tra không lẫn định dạng schema, push và mở PRbase dev.
3. Đủ6 CI trên head mới nhất, cập nhật/không xung đột, giải quyết trao đổi rồi merge theo quyền. READY_FOR_REVIEW chưa phải CI PASS/đã merge.
4. Sau merge, cập nhật dev và tạo feature/backend-session-lifecycle: broker/cấu hình → nhận chung/MQTT → phiên/lệnh chờ/chuyển DB → simulator/tests/hướng dẫn.
5. Chỉ nghiệm thu05/07 khi có số đo; nếu clock/profile không khớp, đổi đặc tả/phiên bản trước nhận raw thật.

Lần Việt hoá sau bàn giao giữ ý nghĩa và trạng thái trên; không làm phát sinh bằng chứng runtime/phần cứng.

## Kiểm tra sau Việt hoá — 2026-10-31

- Backend13/AI15/frontend26 tests PASS; frontend build PASS. Cảnh báo dependency cũ và bundle>500 kB không làm thất bại.
- Công cụ ví dụ PASS17 ca schema,11 mẫu control và9 biến thể sai; payload, ID, khoá và kịch bản giữ nguyên.
- AST thực thi54 file Python theo dõi trong Git không đổi khi bỏ docstring/comment;13 file C++/header/JS thay comment có token thực thi không đổi.
- Quét67 Markdown:164 liên kết local đều tồn tại, không lỗi đóng khối code/UTF-8. Đủ25 giai đoạn và10 kế hoạch nhánh.
- Không viết lại lịch sử Git, không commit/push/merge. Mã trạng thái, tên trường/API, cấu hình và thay đổi schema của Trung được giữ.
- Đã sửa ghi chú GPIO cũ và các mục kiểm thử/rủi ro/tiếp theo đặt nhầm ở giai đoạn00. Không thay trạng thái nghiệm thu.
