# EmpathicSchool — nguồn và trạng thái

Cập nhật: 2026-11-16.

**Chưa tải dataset. Chưa kiểm tra các file tín hiệu hoặc nhãn thực tế.**

Tạm chờ quyền truy cập. Từ 2026-11-16, dự án chuyển sang [WESAD](../wesad/README.md) để làm việc trước; không cần chờ bộ này mới tiếp tục ML.

## Nguồn

- Bản ghi đã kiểm tra: [Zenodo v3, ngày 2025-07-16](https://zenodo.org/records/15556502).
- DOI phiên bản: `10.5281/zenodo.15556502`.
- Bài báo: [A multimodal stress detection dataset with facial expressions and physiological signals](https://doi.org/10.1038/s41597-025-05812-0).
- Quy mô theo metadata v3: 30 người, khoảng 42 giờ; chưa xác nhận thời lượng có nhãn và đủ các kênh cần dùng.

## Quyền truy cập

File bị giới hạn quyền truy cập. Người sử dụng cần đăng nhập Zenodo, đọc và chấp nhận Data Usage Agreement, rồi gửi yêu cầu trên trang bản ghi. Không dùng đường tải vòng qua quyền truy cập hoặc đưa tài khoản/token vào repo.

Trang nguồn yêu cầu sử dụng cho nghiên cứu, bảo vệ dữ liệu và không phân phối lại. Thỏa thuận tại nguồn là căn cứ sử dụng; tài liệu này chỉ ghi tình trạng truy cập, không thay cho thỏa thuận.

Khi được cấp quyền, ưu tiên tải tín hiệu sinh lý, nhãn và tài liệu. Kiểm tra danh sách file trước khi tải để tránh lấy video không cần thiết; chưa biết các file có tách riêng khỏi bản nén lớn hay không.

## Vị trí lưu

- Bản nén và dữ liệu gốc: thư mục này, trong các thư mục con `archives/` và `raw/` khi cần.
- Kết quả trung gian: `ai/data/interim/empathicschool/`.
- Kết quả đã xử lý: `ai/data/processed/empathicschool/`.

Các dữ liệu trên được bỏ qua bởi `.gitignore`. Chỉ README của thư mục nguồn được đưa vào Git.

## Việc cần kiểm tra sau khi tải

- [ ] Ghi danh sách file, kích thước, phiên bản, ngày tải và SHA-256.
- [ ] Đối chiếu mã nhãn, tên mức và cách lấy nhãn; tài liệu có cách gọi lớp chưa thống nhất.
- [ ] Đếm số người, phiên và thời lượng hợp lệ của từng lớp; không coi `unknown` hoặc thiếu nhãn là không stress.
- [ ] Kiểm tra HR/BVP, EDA và ACC ba trục: tần số, đơn vị, đồng bộ thời gian, file rỗng, mất mẫu và đoạn lỗi.
- [ ] Đánh giá riêng mô hình chỉ dùng các tín hiệu thiết bị có; không lấy kết quả dùng video/nhiệt độ làm kết quả cho thiết bị.
- [ ] Chia theo người trước khi tạo cửa sổ; chỉ học tiền xử lý trên tập train.

Tác giả nêu giới hạn về kích hoạt sinh lý (arousal), nhãn tự đánh giá khoảng 2 phút và một số đoạn không có nhãn. Đây là ứng viên để kiểm định, chưa phải bộ dữ liệu đã được chấp nhận cho phân mức stress của ASD-EASE hoặc dự đoán hành vi ở trẻ tự kỷ.
