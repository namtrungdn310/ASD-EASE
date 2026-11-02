# Quy trình quản lý bộ dữ liệu

Cập nhật 2026-10-31. Các yêu cầu lưu/trao đổi dưới đây dành cho nhánh 04–08, không có nghĩa đã thu dữ liệu thật. Xem [API](API_CONTRACT.md), [nhận dữ liệu](contracts/INGESTION_V1.md), [ánh xạ driver](contracts/DRIVER_MAPPING.md).

## Tách nguồn và định danh

Dữ liệu thật nằm trong ai/data/raw, interim, processed tương ứng; dữ liệu sinh chỉ nằm trong ai/data/synthetic/{raw,processed,manifests}. Không trộn thành tập mất nhãn nguồn.

Dùng ID giả danh như P001/SESSION-001, dữ liệu giả lập dùng SYN-P001/SYN-SESSION001. Không lưu tên thật hoặc định danh trực tiếp. Tiền tố ID chỉ giúp đọc; tài khoản thiết bị và quyền sở hữu phiên mới ràng buộc nguồn. Sóng giả chạy trên ESP32 vẫn là SYNTHETIC.

Giữ nguồn, phiên bản schema/firmware/bộ sinh, cấu hình, seed nếu có, ID người/phiên/lần đo và bối cảnh thu. Mô hình chỉ học giả lập ghi SYNTHETIC_ONLY; mô hình trộn phải khai cả hai nguồn. Không đoán nguồn bản cũ từ tên file.

## Thông tin phép đo

- Tách tốc độ danh định và đã đo, kèm khoảng đo, số mẫu, jitter/mất mẫu và nguồn log. Chưa đo thì unknown/null, không sao chép cấu hình thành kết quả.
- PPG hiện chip100/averaging2 → FIFO50 danh định; simulator100/50/20 là cấu hình khác. Ghi GPIO, commit, board/flash/PSRAM khi có căn cứ.
- ADC GSR hiện lấy trung bình8 lần trước EMA; công thức độ dẫn chưa hiệu chuẩn mạch. gsr.delta là tỷ lệ, không µS.
- Raw IMU dùng g và degrees/s. Driver hiện đảo dấu Y/Z trước EMA; ghi phép biến đổi, không áp dụng lại.
- Raw 1.0 dùng mốc chung và khoảng mẫu đều; giữ null khi thiếu. Nếu board không căn được thời gian, dừng nghiệm thu và thống nhất phiên bản có timestamp phù hợp.
- Bản mô tả cần: phiên bản định dạng, phiên/thiết bị/nguồn/boot, cấu hình lấy mẫu, mốc thời gian, thời điểm yêu cầu/nhận/dừng, cutoff/final batch, số mẫu/batch, mất dữ liệu, hash và lý do chưa đầy đủ.
- Tách số đã thu, đưa vào hàng đợi, bị bỏ và đã lưu. Retry trùng không tăng số đã nhận.
- Ghi giao thức/phiên bản thực tế khi biết; không xuất token, mật khẩu, khoá riêng hoặc định danh người. Giờ backend nhận không phải giờ sinh lý chính xác của mẫu.
- DEVICE chưa mô hình có probability=null/model_version=none; quality0 có thể nghĩa chưa có bộ ước lượng. Không dùng giá trị mặc định hay nhãn giả lập như sự thật sinh lý.

## Đủ dữ liệu, lưu và xuất

Thiết bị dừng, backend nhận raw và bản ghi đầy đủ là ba việc khác nhau. Đối chiếu tổng kết MQTT với chỉ mục HTTP, không phụ thuộc thứ tự đến.

STOPPED vẫn có thể thiếu mẫu/batch/file. Phiên không có batch là phiên rỗng, không phải bộ dữ liệu hữu ích. Giữ vị trí null/gap khi xuất; nội suy hoặc lấy mẫu lại là sản phẩm dẫn xuất riêng, phải có cấu hình/phiên bản.

File raw bất biến, DB lưu chỉ mục; sao lưu cả hai. Xuất cần kiểm tra số mẫu, thứ tự, hash, đơn vị và cutoff. Giữ JSONL cũ đến khi có chuyển đổi đã sao lưu/đối chiếu. Hash xác nhận nhất quán file, không chứng minh cảm biến đo đúng. Đọc/xuất file đã lưu không cần broker online.

Thu người thật, sự đồng thuận, quy trình/nhãn và đánh giá khoa học thuộc các cổng sau.

## Chia tập và tránh lộ đáp án

Giữ thứ tự thời gian. Ưu tiên chia theo người hoặc nguyên phiên/lần đo; không rải ngẫu nhiên cửa sổ kề nhau vào train/test. Khi có dữ liệu thật, giữ tập đánh giá riêng, không dùng để học/chỉnh tham số.

Không dùng kịch bản, ID người/phiên/lần đo, seed, trạng thái/điểm simulator hoặc thông tin lộ kết quả làm đặc trưng. Chỉ học chuẩn hoá/mức nền từ phía train, kiểm tra chất lượng đoạn tín hiệu. Hai nguồn dùng chung giao diện xử lý/đặc trưng.

## Báo cáo

Giả lập chỉ kiểm tra phần mềm và giả thiết kỹ thuật, không xác nhận nhận diện ASD/lo âu hoặc hiệu quả lâm sàng. Kết luận thực tế cần tín hiệu thật độc lập, nhãn/quy trình phù hợp, tập đánh giá giữ riêng và số liệu đã đo. Không bịa accuracy, F1, độ trễ, RAM, cảnh báo sai hoặc thời lượng pin.

