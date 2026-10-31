# Kiến trúc hệ thống

## Phạm vi

Đây là nguyên mẫu nghiên cứu kỹ thuật, không phải thiết bị y tế hay công cụ chẩn đoán/điều trị. NORMAL, ATTENTION, UNCERTAIN và CALIBRATING là trạng thái kỹ thuật. DISCONNECTED/ERROR mô tả tình trạng vận hành, không tự là giá trị enum dự đoán. ATTENTION không phải chẩn đoán lo âu.

## Ba chế độ

1. Phát triển: USB để nạp firmware và xem nhật ký.
2. Nghiên cứu/thu dữ liệu: ESP32 gửi mẫu thô qua Wi-Fi để lưu, xử lý trên máy.
3. Thi đấu: ESP32 dùng pin, tự xử lý tín hiệu và quyết định trạng thái. Laptop chỉ nhận/lưu/hiển thị trên cùng LAN, không cần Internet.

## Luồng mục tiêu

```text
MAX30102 + MPU6050 + GSR
  -> thu mẫu -> xử lý tín hiệu -> kiểm tra chất lượng
  -> mức nền cá nhân -> đặc trưng -> mô hình trên ESP32
  -> logic trạng thái theo thời gian -> telemetry mới nhất
  -> Wi-Fi/LAN -> broker MQTT -> backend -> WebSocket -> dashboard React
```

Start/Stop và xác nhận thực thi đi MQTT; batch thô đi HTTP. Trình duyệt dùng HTTP/WebSocket, không giữ thông tin truy cập broker. Laptop không làm thay quyết định cuối trên ESP32 khi thi đấu.

Đây là thiết kế cho nhánh 04–07, chưa phải đường truyền đang chạy. Xem [đặc tả API](API_CONTRACT.md), [điều khiển MQTT](contracts/MQTT_CONTROL.md), [bàn giao 03](integration/03-HANDOFF.md). Broker nhận gói chưa chứng minh thiết bị đã thực thi hoặc backend đã lưu.

## Khi mất mạng

Thu mẫu/suy luận không chờ mạng. Hàng đợi và thời gian thử lại có giới hạn; telemetry chỉ giữ bản mới nhất, không phát dữ liệu cũ như trực tiếp. Kiểm thử chi tiết trên hệ thống thi đấu thuộc giai đoạn 21.

## Lưu trữ

SQLite lưu thiết bị, phiên, chú thích, sự kiện và chỉ mục. Hiện raw được thêm vào JSONL. Mục tiêu nhánh 06 là mỗi batch một file bất biến, có chỉ mục và xác nhận sau khi lưu nhất quán; vẫn đọc được dữ liệu cũ. Không tạo một hàng SQLite cho từng mẫu tốc độ cao.

STOPPED chưa có nghĩa đủ dữ liệu: còn phải đối chiếu tổng kết, số mẫu, thứ tự và hash. Đổi cách lưu không tự đổi JSON raw 1.0.

## Dữ liệu giả lập và AI

Bộ sinh dùng chung đặc tả/giao diện xử lý với dữ liệu thật, giữ nhãn SYNTHETIC. Nó giúp thử phần mềm, không chứng minh cảm biến hoặc kết quả sinh lý.

Luồng AI dự kiến: raw → xử lý → chất lượng → mức nền → cửa sổ trượt → đặc trưng → quy tắc/mô hình nhỏ → điểm dự đoán → logic trạng thái.

Python/C++ sẽ dùng chung định nghĩa và mẫu kiểm tra. Chưa có mô hình sản phẩm hoặc bằng chứng hai bản cho kết quả khớp nhau.

