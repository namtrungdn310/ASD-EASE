# Trục và bố cục biểu đồ Dashboard

Cập nhật 2026-11-10. Chỉ thay cách vẽ, không thay số đo, HR, quality, raw hoặc dữ liệu lưu.

## Thời gian và khoảng mất dữ liệu

Bốn biểu đồ dùng cửa sổ **60 giây theo timestamp thiết bị**, thay bộ đệm 60 điểm.
Giữ các điểm từ T−60 đến T, gồm cả hai đầu nếu có: ở nhịp đúng 1 Hz có thể có 61 điểm.
Không ép số điểm thành số giây. Trong 60 giây đầu của mốc thiết bị, OX là 00:00–01:00;
sau đó cửa sổ trượt theo gói cuối. Khi mở trang giữa phiên, phần chưa nhận để trống.
Không nhận gói thì miền thời gian dừng, không tự tạo dữ liệu mới.

OX có 5 mốc cách 15 giây; vùng biểu đồ hẹp hơn 420px dùng 3 mốc cách 30 giây.
Tất cả dùng cùng cách chia và miền thời gian, không chọn mốc theo mật độ gói.
Nhãn 12px, vùng OX cao36px, cách trục16px; OY rộng56px, nhãn cách8px.
Không hiện tiêu đề và tổng điểm phía trên các thẻ. Mỗi thẻ có ô chung dạng
`42 điểm · 85%`: số điểm màu xám, chỉ phần trăm đổi màu chất lượng; nền xám nhạt,
chữ12px. HR đếm giá trị hữu hạn trong trường hr gốc, không đếm phần tạm tính;
GSR đếm ADC hữu hạn; gia tốc/xoay chỉ đếm thời điểm đủ ba trục hữu hạn, mỗi bộ
là một điểm. Null/NaN/Infinity không tính, số0 vẫn là số đo. Chỉ đếm cửa sổ60giây.
Mất kết nối giữ số điểm lịch sử nhưng phần trăm hiện—. Danh sách điểm vẫn do hook
tách theo thiết bị/phiên/nguồn. Không suy chất lượng từ số điểm hoặc ngược lại.

Trong mục “Thông tin thiết bị” có giải thích luôn đọc được khi mở bằng chuột/bàn phím:
số điểm thuộc60giây, chất lượng engineering-v1 thuộc8giây; không phải số mẫu thô,
tỷ lệ nhận đủ gói hoặc độ chính xác. Badge có nhãn hỗ trợ đọc màn hình cùng ý nghĩa,
không chỉ giải thích bằng hover. H1 giữ ẩn trực quan để cấu trúc tài liệu đầy đủ.

Khoảng giữa hai gói quá1,8giây được chèn một điểm null **chỉ trong dữ liệu vẽ**.
Áp dụng cả nét HR tạm tính; lịch sử nhận, số điểm, telemetry và DB không bị sửa.
Null vốn có vẫn ngắt đường, không trở thành0. Mốc1,8giây là quy tắc biểu diễn cho
telemetry danh định1Hz, không phải kết luận cảm biến lỗi hay ngưỡng sinh lý.

## Miền giá trị

| Biểu đồ | Dải hiển thị |
|---|---|
| HR | Bám cửa sổ dữ liệu, rộng ít nhất30bpm; căn mốc5bpm, chừa15% biên độ khi dao động lớn |
| GSR | Bám cửa sổ dữ liệu, rộng ít nhất100ADC; căn mốc20, chừa15% biên độ; giữ trong0–4095 với dữ liệu hợp lệ |
| Gia tốc | Ba dải Ax/Ay/Az xếp dọc; mỗi dải có OY riêng, rộng ít nhất0,2m/s²; căn mốc0,05m/s², chừa15% biên độ |
| Tốc độ xoay | Ba đường chung OY đối xứng quanh0, rộng ít nhất0,4°/s |
| Xác suất | Cố định0–1 |

Gyro mở rộng theo đỉnh lớn nhất của cả ba trục khi vượt±0,2°/s, chừa10% rồi làm tròn
theo bậc1/2/5. Các độ rộng tối thiểu là lựa chọn hiển thị, không phải ngưỡng sinh lý hay ngưỡng chất lượng.
Giá trị hợp lệ luôn được bao hết, không clip/kẹp hoặc bỏ đỉnh.
HR tính cả đường tạm tính vào miền cần vẽ, vẫn giữ nét đứt và nhãn riêng.

Gia tốc giữ nguyên giá trị tuyệt đối và đơn vị, không trừ trọng lực hoặc trừ nền.
Ba dải dùng cùng miền thời gian, chỉ hiện nhãn thời gian ở dải cuối; tooltip đồng bộ
trong cùng thẻ. Mỗi dải có tên trục và mốc OY của riêng nó; không so biên độ bằng
chiều cao đường giữa hai dải nếu chưa đọc các mốc. Trục thiếu mẫu không được điền0.
Biểu đồ cao216px; bố cục2tầng/2thẻ và số chính giữ nguyên.

Mở rộng ngay trong render nhận dữ liệu mới. Chỉ thu hẹp khi miền cần vẽ nhỏ hơn
ít nhất10%, duy trì15giây theo timestamp thiết bị của các mẫu mới; giữ miền bao
toàn bộ các dải ứng viên trong khoảng chờ. Một đỉnh còn trong history vẫn phải nằm trên biểu đồ.
Một đỉnh mới vượt thang hiện tại hủy lần chờ. Khoảng mẫu quá5giây hoặc gói cuối
không có giá trị vẽ sẽ bắt đầu lại thời gian chờ. Render lại/cùng timestamp không cộng thời gian.
Không có timer tiếp tục thu hẹp khi dữ liệu ngừng tới.

Mỗi biểu đồ giữ state riêng; đổi thiết bị, phiên, nguồn hoặc schema khởi tạo lại.
Clock lùi hoặc history rỗng cũng khởi tạo lại. `null` không trở thành0;
NaN/Infinity không tham gia tính miền. Chỉ gyro dùng miền chung đối xứng;
gia tốc ba miền riêng. GSR chưa có mẫu dùng miền dự phòng0–4095, HR40–160,
mỗi trục gia tốc±0,1, nhưng giao diện vẫn hiện trạng thái trống.
Mẫu đầu tiên phóng ngay vào dữ liệu, không chờ15giây để rời miền dự phòng.

Mã chính: `frontend/src/utils/chartAxis.ts`, `frontend/src/hooks/useChartAxis.ts`.
Kiểm bằng `npm --prefix frontend test` và `npm --prefix frontend run build`.
`chart-axis.test.mjs` kiểm bộ tính miền, StrictMode, cập nhật hook thật và props
gửi vào biểu đồ; chỉ thay Recharts bằng probe để đọc props trong jsdom.
Đây không phải nghiệm thu pixel hoặc nét vẽ trên trình duyệt.

Mỗi vùng gia tốc dùng chiều cao số56/56/92px truyền thẳng
cho Recharts, không dùng `height="100%"` và không dùng lớp `.plot-area` chung.
Grid có ba hàng56/56/92px và hai khe6px, tổng216px; hàng cuối gồm36px nhãn thời gian.
Ba vùng vẽ có cùng chiều cao; chỉ dải cuối có OX. Ax/Ay/Az chỉ hiện ở chú giải
bên trái, không lặp trên vùng vẽ. Màu và kiểu nét nhất quán; tooltip và nhãn hỗ trợ
trình đọc màn hình vẫn giữ tên trục. Tooltip hiển thị khoảng thang riêng của dải.
`acceleration-render.test.mjs` chạy Recharts thật với kích thước DOM giả,
kiểm SVG và tọa độ đường nằm trong từng dải ngay cả khi parent được đo thành200px.

HR/GSR/gyro hiện3mốc OY: dưới/giữa/trên. Riêng cả khung gia tốc chỉ hiện tổng3giá trị:
một mốc giữa ở mỗi dải Ax/Ay/Az, không phải9giá trị. Các dải vẫn giữ miền riêng
và tooltip giữ nguyên số đo thật.
Nhãn OX cách trục16px và có vùng cao36px; chừa12px bên trái vùng dữ liệu,
nhãn OY cách trục8px. Kiểm SVG thật đối chiếu số mốc và khoảng cách nhãn
OX với nhãn cuối OY trên cả gia tốc, HR, GSR, gyro.

## Bố cục

Tiêu đề và phần trăm tín hiệu nằm trong cùng hàng đầu thẻ. Bên dưới chia
thông số/biểu đồ theo tỷ lệ30/70, phần thông số tối thiểu164px.
Padding18px theo chiều dọc,20px theo chiều ngang; khoảng cách nội bộ18px,
khoảng cách thẻ16px. Số chính32px, tiêu đề14px/600, đơn vị12px.
Ax/Ay/Az và Gx/Gy/Gz xếp ba dòng với cột nhãn34px, cách số12px,
không đẩy số sang mép xa. Vạch dọc nhạt phân vùng đọc số và biểu đồ.
Ghi chú HR nằm dưới cùng bên trái trong vùng đọc số, không tạo hàng cao thêm cho cả thẻ.
Ba dải gia tốc chỉ có một đường lưới giữa mỗi dải, tránh tạo ba khung lưới dày.
Dưới1151px chuyển về một thẻ mỗi hàng; dưới481px chuyển thông số lên trên
biểu đồ và hiện ba số đo phụ cùng hàng. Không bẻ đôi số đo để nhét.

`acceleration-render.test.mjs` kiểm SVG thật:3nhãn OY toàn thẻ gia tốc,
3nhãn OY mỗi biểu đồ còn lại, cùng mốc thời gian15giây/30giây khi resize,
chiều cao SVG và khoảng cách góc OX/OY. Đây là kiểm DOM/SVG có kích thước giả,
không thay nghiệm thu CSS/pixel trên trình duyệt thật.
