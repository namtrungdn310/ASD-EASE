# Giai đoạn 01 — Khung dự án

## Trạng thái

DONE

## Người phụ trách

Trung — IT

## Mục tiêu

Tạo ba thư mục mã nguồn, tài liệu, container, đặc tả, kiểm thử và khung firmware.

## Lý do

Các bước sau cần một dự án dễ hiểu và chạy lại được.

## Phụ thuộc

Không.

## Đầu vào

Docker, Python và Node; chưa cần phần cứng.

## Công việc

- [x] Tạo đủ cấu trúc mã nguồn và tài liệu.
- [x] Tạo khung backend/frontend/AI/firmware build được.
- [x] Kiểm tra Docker, đặc tả và tests.

## File dự kiến thay đổi

backend/...; frontend/...; ai/...; docs/...; cấu hình tại thư mục gốc

## Lưu ý triển khai

Dùng một bộ mã nguồn và đặc tả có phiên bản; phần chưa làm phải ghi rõ là khung dự kiến.

## Kiểm thử

Chạy `docker compose config`, pytest backend/AI, build frontend/container và kiểm tra cấu trúc.

## Điều kiện nghiệm thu

- [x] Đủ ba thư mục mã nguồn và tài liệu yêu cầu.
- [x] Backend/AI tests và frontend/container build đạt.
- [x] Khung firmware không có thông tin truy cập thật, không giả định PSRAM.

## Đầu ra

Phần triển khai có thể review, kết quả kiểm thử và tiến độ đã cập nhật. Không tự chuyển sang giai đoạn sau khi chưa có yêu cầu.

## Rủi ro

Khác biệt phiên bản thư viện hoặc đường dẫn giữa các hệ điều hành.

## Xử lý lỗi và khôi phục

Đọc nhật ký build và kiểm thử đặc tả; chỉ hoàn tác thay đổi gây lỗi.

## Kết quả

Đã hoàn tất phần khung dự án. Firmware build được bằng cấu hình tạm; chưa kiểm chứng hoạt động trên phần cứng.

## Bằng chứng hoàn thành

- `docker compose config`: PASS.
- Backend: 13 tests PASS; AI: 15 tests PASS.
- TypeScript/Vite build PASS; kiểm tra thư viện production ghi nhận 0 lỗ hổng ở lần kiểm tra đó.
- Ba image Docker build được; backend khỏe, frontend chạy sau `docker compose up -d --build --wait`.
- Đủ 25 tài liệu giai đoạn và ba thư mục mã nguồn.
- PlatformIO 6.2.0 build PASS với cấu hình ESP32-S3 tạm, không phải bằng chứng phần cứng.

## Giai đoạn tiếp theo

Giai đoạn 02 — Kiểm thử toàn luồng bằng dữ liệu giả lập
