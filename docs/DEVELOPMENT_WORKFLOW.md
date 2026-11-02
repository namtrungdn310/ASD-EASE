# Quy trình phát triển

- main là bản ổn định; dev là nơi tích hợp hằng ngày. Không push trực tiếp vào hai nhánh này.
- Mỗi nhánh ngắn tập trung một mục tiêu: feature/*, fix/*, docs/* hoặc chore/*. Mở PR vào dev; chỉ dev mở PR lên main.
- Trước merge: build và kiểm thử liên quan đạt, không xung đột, tài liệu/tiến độ khớp phần đã làm. Thiết kế thay đổi ghi DECISIONS.md; sản phẩm thay đổi ghi CHANGELOG.md.
- Đổi quy ước dữ liệu phải cập nhật đặc tả cùng backend Pydantic, TypeScript, C++ và simulator liên quan; không âm thầm đổi payload.
- Kết thúc giai đoạn: đối chiếu nghiệm thu, lưu bằng chứng, ghi việc còn chặn và cập nhật tiến độ. Phần cứng cần phép đo thật; AI cần thí nghiệm thật.
- “Dự kiến” không có nghĩa tính năng đã chạy. Không ghi PASS cho kiểm thử chưa thực hiện.

Xem [Git/GitHub](GIT_WORKFLOW.md) và [tiến độ tích hợp](integration/PROGRESS.md).
