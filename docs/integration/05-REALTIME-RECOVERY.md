# Tự khôi phục dữ liệu trực tiếp sau khi người dùng kết nối

Các cơ chế bên dưới chỉ hoạt động sau khi người dùng chọn thiết bị và bấm **Kết nối** trên Dashboard. Tải web không tự mở WebSocket; **Ngắt kết nối** dừng cơ chế thử lại cho trang đó, nhưng không điều khiển ESP/MQTT hoặc phiên backend.

Ngày2026-11-05. Trung báo lần mở trang đầu đôi khi đã có Dashboard nhưng đứng ở **Chờ dữ liệu**, cần hard refresh. Đây là mô tả hiện tượng; chưa tái hiện đúng lỗi trên trình duyệt của Trung vì công cụ browser không có kết nối.

## Lỗi đã tái hiện bằng kiểm thử

- WebSocket CONNECTING trước đây không có deadline; có thể chờ vô hạn nếu không nhận open/close.
- Socket báo OPEN nhưng không có message và cũng không có close event không được phát hiện. Backend bỏ subscriber lỗi khỏi danh sách mà không đóng kết nối có thể khiến browser vẫn chờ.
- Reconnect chỉ mở lại socket, không gia hạn cookie local; lỗi xác thực có thể tiếp tục lặp.
- Fetch mở phiên local không có timeout phía client. Tab/ngủ máy/khôi phục mạng không có đường phục hồi chủ động cho socket.

Ba tests frontend và hai tests backend đã FAIL trước sửa; sau sửa đều PASS. Không kết luận mọi nguyên nhân trên đều đã xảy ra với phiên browser người dùng.

## Cách xử lý hiện tại

- Tạo phiên local giới hạn8 giây, thất bại thử lại sau3 giây; token chỉ ở Node, browser nhận cookie HttpOnly như trước.
- Socket mở tối đa10 giây. Lỗi/timeout chủ động dọn callback và đóng socket cũ; không phụ thuộc close event.
- Khi thử lại trong dev, gia hạn phiên qua bridge trước rồi mở WS; mỗi hook có tối đa một socket/request/retry hiện hành.
- Nếu không có dữ liệu truyền tải10 giây, gửi text `ping`; backend trả text `pong`. Quá5 giây chưa có phản hồi thì thay kết nối sau1,5 giây. Payload telemetry1.0/1.1 không đổi.
- `pong` chỉ kiểm tra transport; không thêm vào biểu đồ hoặc làm mẫu cảm biến cũ thành live. Vẫn stale sau5 giây không có telemetry mới hợp lệ; backend sống nhưng ESP chưa gửi thì giao diện chờ/cũ là đúng.
- Trở lại tab, mạng online hoặc pageshow từ bfcache sẽ kiểm tra và khôi phục kết nối khi cần. Không tự reload trang.
- Khi reconnect giữ history/chọn thiết bị. Chỉ đánh live sau telemetry mới được chấp nhận cho thiết bị đó trên kết nối mới; gói trùng không làm mới, kể cả đồng hồ receive trùng thời điểm.
- Backend giới hạn mỗi lần gửi2 giây; subscriber lỗi được loại và đóng1011 để client nhận biết. Gửi pong dùng cùng đường xử lý lỗi. Không nới kiểm tra login/Origin.
- StrictMode/unmount dọn timeout, interval, callback, listeners và abort request đang chạy. Không tạo nhiều socket vì render.

## Kiểm chứng

- Frontend54 tests/React DOM/StrictMode và build đạt: mở trang qua LocalConnection→Dashboard, socket im lặng/không close, CONNECTING quá hạn, gia hạn cookie, timeout phiên đầu, unmount khi đang fetch, pong không làm dữ liệu live giả, khôi phục online/pageshow và gói trùng.
- Backend101 tests đạt; bao gồm trả pong khi không có telemetry và loại/đóng subscriber lỗi trong khi client khác vẫn nhận.
- Đã rebuild backend trên máy Trung, broker/backend healthy. Login→WS cookie mới6 lần đều nhận frame DEVICE đầu trong0,375..0,985 giây tính từ khi WS đã mở. Mỗi lượt ping đều có pong.
- Một kết nối tiếp nhận12 frame ESP32-001 thật có timestamp tăng đều, khoảng1002 ms. Không lưu/commit số sinh học thật.
- Kiểm thử native C++→broker/backend/API/DB/WS thật trong môi trường cô lập đạt9 nhóm, bao gồm heartbeat trước Start, sáu trục1.1, ACK/lặp/ACL và restart backend/broker. Dữ liệu bài này là SYNTHETIC, không thay nghiệm thu board.
- Giới hạn: đây là kiểm tra HTTP/WS thật cùng DOM kiểm soát, chưa là thao tác tự động trong trình duyệt thật. Người dùng cần mở lại tab bằng bản mới để xác nhận không còn hiện tượng cũ.

Không cần nạp ESP cho thay đổi này. Giữ Docker Desktop và npm run dev; nếu terminal đang chạy bản cũ thì dừng/chạy lại npm run dev để launcher build backend theo source. Máy Trung đã rebuild trong lượt kiểm tra này.
