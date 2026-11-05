# Thiết kế logo ASD-EASE

Cập nhật 2026-11-05. Nhánh làm việc: `feature/asd-ease-logo`.

## Bản đã chọn: 02 / TT Signal

Trung chọn **02 / TT Signal**. Biểu tượng ghép hai chữ T của Trung và Tân, với khe cong hình S ở giữa. Màu chính cobalt `#0638D8`, điểm nhấn mint `#20E78D`. Chữ ASD-EASE được vẽ riêng, không cần cài font để mở logo.

Đã dựng thành SVG và gắn vào header Dashboard, favicon, biểu tượng Apple và tiêu đề tab. Bộ file chỉ giữ logo 02; có các bản màu, một màu và âm bản để dùng theo nền hoặc cách in.

- [Xem bộ nhận diện](tt-signal/preview.png).
- [File dùng và hướng dẫn](tt-signal/README.md).
- [Toàn bộ bộ logo ZIP](../../../output/brand/asd-ease-logo-02.zip).
- [Tem A4 màu](../../../output/pdf/asd-ease-logo-02-stickers-a4.pdf).
- [Tem A4 một màu](../../../output/pdf/asd-ease-logo-02-stickers-a4-mono.pdf).
- [Kiểm tra bàn giao](VERIFICATION.md).

`build_selected_logo.py` xuất lại bộ **02** đang dùng, với tiện ích trong `svg_helpers.py`. Cần Python với Pillow/fontTools, `rsvg-convert` và font Segoe UI trên Windows. Font chỉ phục vụ chữ chú thích trên bảng xem mẫu/tờ in; logo và wordmark là đường vector tự dựng.

Các phương án không được chọn, bảng so sánh cũ, tem V1 và mã tạo các mẫu cũ đã được xoá. Không tạo lại chúng khi chạy công cụ xuất logo.
