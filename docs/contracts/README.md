# Đặc tả kết nối thiết bị — bàn giao nhánh 03

Nhánh03 đã merge PR #12 tại752bd5d. Nhánh04 có bộ kiểm tra runtime/control và backend MQTT, xem [bàn giao04](../integration/04-HANDOFF.md). check_examples.py vẫn kiểm tra schema tương thích ban đầu; tests runtime ở backend/tests kiểm tra chặt hơn, không sửa payload mẫu chỉ để đạt.

Ngày2026-10-31. JSON ở đây là mẫu SYNTHETIC để thử phần mềm, không dữ liệu người thật hoặc bằng chứng MQTT/board đã hoạt động.

## Thứ tự đọc

1. [API_CONTRACT](../API_CONTRACT.md): trường dữ liệu và phần hiện có/dự kiến.
2. [INGESTION_V1](INGESTION_V1.md): thời gian, quyền, giới hạn, phiên và xác nhận lưu raw.
3. [MQTT_CONTROL](MQTT_CONTROL.md): topic, lệnh, ACK và kết nối lại.
4. [DRIVER_MAPPING](DRIVER_MAPPING.md): lấy trường nào, đổi đơn vị và việc cần đo.
5. [examples.json](examples.json): mẫu đúng/sai và kịch bản cho04–07 viết tests.
6. [Bàn giao03](../integration/03-HANDOFF.md): kết quả kiểm tra, giới hạn và bước tiếp.

## Dùng ví dụ và công cụ kiểm tra

examples.json là danh mục, không gửi nguyên file vào API/MQTT. payload là nội dung gói; derive_from/changes tạo biến thể theo đường dẫn chấm. current_schema_valid là kết quả mong đợi của Pydantic hiện tại; expected_target là yêu cầu chưa triển khai. Mục kịch bản không phải kết quả E2E đã đạt.

Từ thư mục gốc chạy:

```powershell
.\.venv\Scripts\python.exe docs/contracts/check_examples.py
```

Công cụ chỉ đọc, không khởi động app/DB/broker, dùng Pydantic đã có. Nó kiểm tra schema hiện tại, một phần cấu trúc control và thời gian/số mẫu của ví dụ; không thay kiểm thử xác thực, vòng đời, JCS hoặc broker thật ở04–07. Không thêm thư viện runtime.

Nhánh03 không sửa mã chạy hoặc driver. Nhánh04 phải viết tests/migration/adapter; nhánh05/07 kiểm tra JSON từ C++ và đo board. [Quy trình bộ dữ liệu](../DATASET_PROTOCOL.md) áp dụng mọi bước, không trộn dữ liệu mất nhãn nguồn.
