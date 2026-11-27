# Dataset bên ngoài

Lưu dữ liệu tải từ các nhóm nghiên cứu tại đây, tách khỏi dữ liệu thiết bị tự thu và dữ liệu giả lập.

```text
ai/data/external/wesad/           WESAD gốc, đang ưu tiên làm việc
ai/data/interim/wesad/            Kết quả xử lý trung gian WESAD
ai/data/processed/wesad/          Feature và kết quả WESAD
ai/data/external/empathicschool/   Dữ liệu gốc và bản nén tải về
ai/data/interim/empathicschool/    Kết quả xử lý trung gian
ai/data/processed/empathicschool/  Dữ liệu đã xử lý để huấn luyện
```

- Giữ nguyên file gốc. Giải nén sang thư mục con, không sửa trực tiếp bản gốc.
- Khi tải được, ghi phiên bản, tên file, ngày tải và SHA-256; sau đó kiểm tra nhãn, thời gian, đơn vị và dữ liệu thiếu.
- Chỉ commit tài liệu nguồn, code và báo cáo tổng hợp phù hợp điều kiện sử dụng. Không commit dataset, dữ liệu dẫn xuất hoặc thông tin đăng nhập.
- Đường dẫn dữ liệu trong code/notebook phải cấu hình được; không dùng đường dẫn riêng của một máy.

Ưu tiên [WESAD](wesad/README.md) từ ngày 2026-11-16. EmpathicSchool vẫn [chờ quyền tải](empathicschool/README.md).

Trước khi xử lý, theo [cấu trúc dữ liệu ML đã chốt](../../../docs/ml/01-ML-DATA-CONTRACT.md).
