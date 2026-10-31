# Tiến độ dự án

## Giai đoạn hiện tại

Giai đoạn02 — kiểm thử toàn luồng giả lập. Tổng trạng thái IN_PROGRESS. Giai đoạn hoàn tất gần nhất:01 — khung dự án.

| Giai đoạn | Nội dung | Phụ trách | Trạng thái | Bắt đầu | Kết thúc | Ghi chú |
|---|---|---|---|---|---|---|---|
| 00 | Kiểm chứng phần cứng | Tân | NOT_STARTED | - | - | Cần kiểm chứng board thật. |
| 01 | Khung dự án | IT | DONE | - | - | Cấu trúc, tests, build/container đã kiểm tra; không thay nghiệm thu phần cứng. |
| 02 | Kiểm thử toàn luồng giả lập | IT | IN_PROGRESS | - | - | Frontend26 tests và18/18 gói đã đạt; thiếu quan sát trình duyệt. |
| 03 | MAX30102 | Tân | IN_PROGRESS | - | - | Có driver/FIFO/HR, thiếu nghiệm thu board. |
| 04 | MPU6050 | Tân | IN_PROGRESS | - | - | Có đọc thanh ghi/EMA, thiếu hiệu chuẩn/thời gian thật. |
| 05 | GSR | Tân | IN_PROGRESS | - | - | Có ADC/mức nền/EMA, thiếu xác nhận mạch/GPIO/hiệu chuẩn. |
| 06 | Tích hợp cảm biến | Tân | IN_PROGRESS | - | - | Có vòng Serial chung, thiếu đo tốc độ/đồng bộ/mất mẫu. |
| 07 | Wi-Fi và backend | IT | NOT_STARTED | - | - | Client ESP32 LAN/MQTT chưa triển khai. |
| 08 | Ghi dữ liệu | IT | NOT_STARTED | - | - | Khung raw receiver chưa đủ nghiệm thu. |
| 09 | Thu thập dữ liệu | Chung | NOT_STARTED | - | - | Giả lập không thay dữ liệu thu thật. |
| 10 | Xử lý tín hiệu | IT | NOT_STARTED | - | - | Mới có giao diện đầu vào chung. |
| 11 | Mức nền và đặc trưng | IT | NOT_STARTED | - | - | Chưa triển khai. |
| 12 | Đối chứng theo quy tắc | IT | NOT_STARTED | - | - | Chưa có mô hình đối chứng hoàn chỉnh. |
| 13 | Thử nghiệm học máy | IT | NOT_STARTED | - | - | Chưa huấn luyện mô hình. |
| 14 | Chọn mô hình | Chung | NOT_STARTED | - | - | Chưa có so sánh đo thực. |
| 15 | Xuất mô hình | IT | NOT_STARTED | - | - | Chưa có mô hình đã xuất. |
| 16 | Suy luận trên thiết bị | Chung | NOT_STARTED | - | - | Chưa suy luận thật trên thiết bị. |
| 17 | Đối chiếu Python/C++ | Chung | NOT_STARTED | - | - | Chưa có bằng chứng Python/C++ khớp. |
| 18 | Logic thời gian | Chung | NOT_STARTED | - | - | Chưa có máy trạng thái sản phẩm. |
| 19 | Chạy pin độc lập | Tân | NOT_STARTED | - | - | Cần phần cứng. |
| 20 | Thi đấu không dây | Chung | NOT_STARTED | - | - | Cần phần cứng. |
| 21 | Phục hồi kết nối | Chung | NOT_STARTED | - | - | Mới có thiết kế. |
| 22 | Kịch bản trình diễn | Chung | NOT_STARTED | - | - | Giả lập không thay trình diễn vật lý. |
| 23 | Đo hiệu năng | Chung | NOT_STARTED | - | - | Chưa công bố chỉ số khoa học/hệ thống. |
| 24 | Chốt bản thi đấu | Chung | NOT_STARTED | - | - | Giai đoạn sau. |

## Việc còn chặn và rủi ro

- Ngày2026-10-20 công cụ trình duyệt trả discovery=[] và No browser is available; chưa xác nhận trực quan giá trị/nhãn SYNTHETIC DATA. Xem [hướng dẫn nghiệm thu](integration/02-VERIFICATION.md).
- Chưa xác minh board/flash/PSRAM, dây nối, chất lượng cảm biến, nguồn và pin. GPIO7 hiện chỉ là cấu hình code.
- Build/HTTP/WebSocket đạt không chứng minh bố cục đúng hoặc phép đo đúng.
- Dữ liệu giả lập chỉ phục vụ kỹ thuật, không xác nhận sinh lý/lâm sàng.

## Đã kiểm chứng trong các lần trước

- Backend13 tests, health/OpenAPI/HTTP/WebSocket và khung lưu raw đã đạt.
- Frontend build/26 tests React DOM/jsdom đã đạt; socket/đồng hồ trong tests được giả lập, chưa kiểm tra trình duyệt thật.
- AI có bộ sinh giả lập và đầu vào xử lý chung; pipeline nghiên cứu phía sau còn khung.
- Firmware có3 driver, EMA và báo Serial; profile esp32s3_supermini build được. Cleanup PR #9 đã gom kiểu/header;4 tổ hợp header đạt ở lần kiểm tra2026-10-20.
- Compose,3 image và khởi động backend/frontend đã kiểm tra. Chưa có đường ESP32 LAN thật, pin độc lập hoặc chế độ thi đấu được nghiệm thu.

Các kết quả chỉ đúng phạm vi/commit đã ghi, không tự trở thành kết quả mới trong lượt dịch tài liệu.

## Nhánh công việc hiện tại

Nhánh docs/device-ingestion-contract, dựa dev d80cc0e, đã hoàn thiện phần đặc tả/ví dụ trên máy ngày2026-10-31: READY_FOR_REVIEW, chưa commit/push/PR/merge. Code nhánh01 và02 đã merge trước đó;02 vẫn thiếu nghiệm thu trực quan.

Xem [kế hoạch](integration/README.md), [tracker nhánh](integration/PROGRESS.md), [bàn giao03](integration/03-HANDOFF.md). Sau review/merge03 mới tạo nhánh04 làm backend MQTT/phiên. Hướng đã chốt: MQTT telemetry/điều khiển, raw HTTP, browser HTTP/WS; chưa runtime.

**Số nhánh khác số giai đoạn**: nhánh03 là đặc tả, giai đoạn03 là MAX30102. Đo thiết bị ở05/07 nhánh tích hợp vẫn là cổng trước nghiệm thu giai đoạn07/08.

## Chỉ số

Chưa có số liệu khoa học: không công bố accuracy/F1, độ trễ, RAM, cảnh báo sai hoặc thời lượng pin nếu chưa đo.
