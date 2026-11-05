# Kiểm tra logo 02 - cập nhật 2026-11-05

Nhánh: `feature/asd-ease-logo`. Hướng được chọn: **02 / TT Signal**.

| Hạng mục | Kết quả |
|---|---|
| Đối chiếu mẫu 02 | Giữ hai khối T, khe S, hai điểm mint và chữ cách điệu; dựng lại thành SVG |
| Xem bản màu, âm và một màu | Đã render `tt-signal/preview.png`, kiểm tra trực quan |
| Favicon | SVG và ICO gồm 16/32/48/64 px; nền trắng, biểu tượng cobalt |
| Logo web | SVG 760 x 160, img có alt và kích thước; không sửa logic Dashboard |
| Tem màu và đen | PDF 1 trang A4 mỗi bản, 595.28 x 841.89 pt; không chứa ảnh raster |
| Render PDF | Đã xem cả hai trang, chữ không cắt, tem không chồng, có thước 50 mm |
| Frontend tests | `npm --prefix frontend test`: PASS 26/26 |
| Frontend build | `npm --prefix frontend run build`: PASS; vẫn có cảnh báo bundle >500 kB |
| Kiểm tra HTTP local | Đúng tiêu đề ASD-EASE; cả 5 asset trả 200 và byte khớp file nguồn tại cổng 5173 |
| Kiểm tra file bàn giao | SVG đọc hợp lệ; PNG RGBA nền trong; ICO đủ 4 kích thước; ZIP không trùng tên, CRC đạt |
| Dashboard trong trình duyệt thật | NOT_RUN: trình duyệt tích hợp báo không có browser khả dụng |
| In giấy/dán lên vỏ thật | NOT_RUN: kích thước vỏ thực chưa được cung cấp |

Đã xoá bộ mẫu V1, bảng so sánh V2, tem V1 và mã tạo mẫu cũ. Công cụ xuất chỉ còn tạo logo 02. Hai file schema backend đang có thay đổi từ trước được giữ nguyên và không nằm trong PR logo. Kết quả CI của commit được công bố trên PR vào `dev`.

Tạo lại bộ asset bằng `.venv/Scripts/python.exe docs/brand/asd-ease/build_selected_logo.py`. Bộ ZIP ở `output/brand/`, PDF ở `output/pdf/`. Khi mở Dashboard, kiểm tra logo header và tab; nếu trình duyệt giữ icon cũ, đóng tab rồi mở lại hoặc tải lại mạnh.
