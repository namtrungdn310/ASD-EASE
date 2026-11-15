# Kiểm thử hồi quy frontend

Trục OY ổn định: `chart-axis.test.mjs` kiểm dải nền/mở rộng/thu hẹp15giây,
giữ đỉnh trong history, gyro đối xứng tối thiểu0,4°/s, HR tối thiểu30bpm,
GSR tối thiểu100ADC, gia tốc ba miền riêng/chung thời gian, null/clock/đổi luồng,
StrictMode và hook/component thật. Recharts được thay bằng probe chỉ trong file này
để đối chiếu domain/ticks/series; không kiểm CSS hoặc hình ảnh. [Quy tắc](../../docs/design/CHART_AXES.md).

Chạy từ frontend, với Node22 và dependencies đã cài:

```powershell
npm test
npm run build
```

live-telemetry.test.mjs dùng bộ chạy tests của Node và Vite SSR để chạy helper TypeScript/component React thật. Chỉ hook mạng của Dashboard được thay bằng mẫu có kiểm soát; các tests trong file chạy tuần tự vì dùng chung mẫu.

Phạm vi: bốn trạng thái kết nối, dữ liệu rỗng/cũ, nguồn giả lập, null/0, chọn thiết bị, chuyển dữ liệu biểu đồ, escape ID, kiểm tra payload, bộ đệm60 giây, đổi luồng và ranh giới còn mới. CI chạy trước build.

Cửa sổ60giây được thử cả nhịp1Hz/2Hz và mất gói dài. Mốc OX chia đều15giây
hoặc30giây theo chiều rộng, không theo số điểm. Điểm ngắt null chỉ thuộc lớp vẽ.
`acceleration-render.test.mjs` dùng Recharts thật, ResizeObserver/DOM có kiểm soát,
đối chiếu3nhãn OY toàn thẻ gia tốc,3nhãn mỗi biểu đồ khác, OX đồng bộ và khoảng cách nhãn.

use-live-telemetry.test.mjs dùng hook thật với React DOM/jsdom: StrictMode, cập nhật, timeout/trùng, thử lại, tách callback socket, chọn thiết bị/phiên và dọn khi unmount. Socket/đồng hồ giả lập có kiểm soát; hook/vòng đời React không bị thay. Test Dashboard gửi sự kiện DOM, đối chiếu live → stale → disconnected → waiting → live.

local-connection.test.mjs kiểm tra tự mở/gia hạn phiên, retry, giữ Dashboard và cleanup StrictMode. local-session.test.mjs kiểm tra bridge localhost, cookie HttpOnly, chặn Origin/Host/client ngoài và không trả secret.

Chỉ đếm cảnh báo Recharts kích thước0 đã biết vì jsdom không tính bố cục. Không kết luận đúng pixel hoặc trình đọc màn hình. Tổng hiện tại60 tests; jsdom chỉ là dependency phát triển. Có kiểm tra parser1.0/1.1, sáu trục âm/0/null, đơn vị/độ lớn, history/đổi phiên bản, biểu đồ, quality chưa đánh giá và mở/đóng thông tin. Dashboard ghép bốn số đo với biểu đồ; khung AI luôn có vị trí chờ nhưng chỉ vẽ lịch sử khi có dữ liệu phù hợp.

Phiên tự động: DOM dùng hook thật và API giả có kiểm soát, kiểm tra STARTING chưa thành hoạt động, backend ACK nhưng chưa telemetry cùng session vẫn chờ, live mới xác nhận, stale không giả đang chạy; đổi thiết bị không giữ phiên cũ. Browser chỉ GET /api/v1/sessions, không có nút Start/Stop hoặc POST tạo phiên.

Hồi quy khung AI: DEVICE/modelnone không tạo dự đoán, trạng thái có mô hình và xác suất0/1/null được giữ đúng, dữ liệu cũ không hiện kết quả hiện tại, nguồn giả lập được gắn nhãn. Test DOM dùng hook thật kiểm tra chuyển modelnone→model test→stale. Badge Đã kết nối chỉ bật sau mẫu hợp lệ; socket vừa mở/reconnect hoặc stale vẫn Chưa kết nối.

Bộ hồi quy realtime kiểm tra phiên mở đầu timeout/retry, deadline CONNECTING, OPEN im lặng không close event, ping/pong không làm live giả, renew cookie trước reconnect, online/pageshow và LocalConnection→Dashboard nhận lại mẫu mà không remount. Giữ tests cleanup StrictMode/request đang chạy, duplicate không làm mới và history không bị xoá do reconnect.

Kiểm tra HTTP/WebSocket thật độc lập: cài cả requirements backend/ai rồi chạy từ root:

```powershell
.\.venv\Scripts\python.exe .github/scripts/check-mock-transport.py
```

Công cụ tạo backend/SQLite tạm ở cổng loopback trống, phát lại3 kịch bản, so18 gói với nguồn, thử từ chối gói sai/nối lại subscriber rồi dừng dịch vụ của nó. Không sửa DB ứng dụng.

Các lớp kiểm tra này không thay trình duyệt thật, CSS, nét vẽ biểu đồ, trình đọc màn hình hoặc đường liên tục từ simulator tới browser. Vẫn cần nghiệm thu trực quan nhánh02.
