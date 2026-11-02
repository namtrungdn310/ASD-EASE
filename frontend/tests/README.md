# Kiểm thử hồi quy frontend

Chạy từ frontend, với Node22 và dependencies đã cài:

```powershell
npm test
npm run build
```

live-telemetry.test.mjs dùng bộ chạy tests của Node và Vite SSR để chạy helper TypeScript/component React thật. Chỉ hook mạng của Dashboard được thay bằng mẫu có kiểm soát; các tests trong file chạy tuần tự vì dùng chung mẫu.

Phạm vi: bốn trạng thái kết nối, dữ liệu rỗng/cũ, nguồn giả lập, null/0, chọn thiết bị, chuyển dữ liệu biểu đồ, escape ID, kiểm tra payload, bộ đệm60 điểm, đổi luồng và ranh giới còn mới. CI chạy trước build.

use-live-telemetry.test.mjs dùng hook thật với React DOM/jsdom: StrictMode, cập nhật, timeout/trùng, thử lại, tách callback socket, chọn thiết bị/phiên và dọn khi unmount. Socket/đồng hồ giả lập có kiểm soát; hook/vòng đời React không bị thay. Test Dashboard gửi sự kiện DOM, đối chiếu live → stale → disconnected → waiting → live.

Chỉ đếm cảnh báo Recharts kích thước0 đã biết vì jsdom không tính bố cục. Không kết luận đúng pixel hoặc trình đọc màn hình. Tổng hiện tại26 tests; jsdom chỉ là dependency phát triển.

Kiểm tra HTTP/WebSocket thật độc lập: cài cả requirements backend/ai rồi chạy từ root:

```powershell
.\.venv\Scripts\python.exe .github/scripts/check-mock-transport.py
```

Công cụ tạo backend/SQLite tạm ở cổng loopback trống, phát lại3 kịch bản, so18 gói với nguồn, thử từ chối gói sai/nối lại subscriber rồi dừng dịch vụ của nó. Không sửa DB ứng dụng.

Các lớp kiểm tra này không thay trình duyệt thật, CSS, nét vẽ biểu đồ, trình đọc màn hình hoặc đường liên tục từ simulator tới browser. Vẫn cần nghiệm thu trực quan nhánh02.
