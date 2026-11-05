# ASD-EASE - Logo 02 / TT Signal

Trung chọn mẫu 02 ngày 2026-11-03. Hai chữ T gợi Trung + Tân; khe S tạo cảm giác chuyển động và kết nối. Logo được dựng bằng vector, dùng chung cho web, browser và tem thiết bị.

## Chọn đúng file

| Nhu cầu | File |
|---|---|
| Xem nhanh toàn bộ | `preview.png` |
| Logo ngang cho website | `logo-horizontal.svg` / `.png` |
| Logo xếp dọc | `logo-stacked.svg` / `.png` |
| Chỉ biểu tượng | `mark.svg` / `.png` |
| Chỉ tên dự án | `wordmark.svg` |
| In một màu | Các file có hậu tố `-black.svg` |
| Đặt trên nền tối | `-reverse.svg` (trắng + mint) hoặc `-white.svg` |
| Tab browser | `favicon.svg`, `favicon.ico` và PNG 16/32/48/64 px |
| Biểu tượng ứng dụng | `app-icon-512.png`, `apple-touch-icon.png` |
| Tem in thử | `stickers-a4.svg`, `stickers-a4-mono.svg`; PDF trong `print/` của ZIP |

SVG phóng lớn không vỡ. PNG logo/biểu tượng có nền trong suốt; favicon và app icon có nền trắng để giữ khe S rõ trên nền sáng/tối. Favicon dùng một màu cobalt vì phần mint quá nhỏ ở tab browser.

## Màu và cách đặt

- Cobalt: `#0638D8`, RGB 6/56/216.
- Mint: `#20E78D`, RGB 32/231/141.
- Nền tối gợi ý: `#101C40`.
- Giữ đúng tỷ lệ, không kéo giãn ngang/dọc, không thêm viền hoặc bóng vào biểu tượng.
- Chừa khoảng trống quanh logo ít nhất bằng 1/8 chiều cao biểu tượng. Favicon có bố cục riêng cho diện tích nhỏ.
- Với bản màu, nên dùng biểu tượng rộng từ 32 px. Nhỏ hơn dùng favicon một màu. Logo ngang trên web nên rộng từ 180 px để tên còn dễ đọc.

## In tem

PDF A4 có tem tròn **20 mm** và tem ngang **50 x 18 mm**, là kích thước in thử trước khi biết vỏ thiết bị thật. Chọn **Actual size / 100%**, tắt **Fit to page**, đo đoạn thước trên giấy phải đúng **50 mm**.

Đường xám mảnh hướng dẫn cắt thủ công; chưa phải đường bế chuyên dụng của nhà in. Logo có khoảng cách an toàn với mép tem. Với vỏ nhỏ hơn, gửi SVG cho nhà in và chốt lại kích thước, vật liệu, đường bế. Màu hiện là sRGB; nên in thử để chỉnh màu theo máy/vật liệu, nhất là xanh mint.

## Áp dụng trong dự án

Dashboard dùng `frontend/public/brand/asd-ease-logo.svg`; favicon, ICO và biểu tượng Apple ở `frontend/public/`. Tiêu đề tab: **ASD-EASE · Dashboard**. URL favicon có phiên bản `tt-signal-1` để cập nhật biểu tượng cũ trong cache.

Không có font bên ngoài, thư viện hay kết nối mạng mới cần tải khi hiển thị logo.
