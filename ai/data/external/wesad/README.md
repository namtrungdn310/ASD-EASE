# WESAD — nguồn và cách dùng trong ASD-EASE

Cập nhật: 2026-11-17. Dataset ưu tiên hiện tại; EmpathicSchool tạm chờ quyền truy cập.

## Nguồn và điều kiện sử dụng

- [Trang tác giả](https://ubi29.informatik.uni-siegen.de/usi/data_wesad.html).
- [Tải WESAD.zip từ liên kết của tác giả](https://uni-siegen.sciebo.de/s/HGdUkoNlW1Ub0Gx/download).
- [Thông tin UCI](https://archive.ics.uci.edu/dataset/465/wesad+wearable+stress+and+affect+detection), DOI `10.24432/C57K5T`.
- Bài báo gốc: *Introducing WESAD, a multimodal dataset for Wearable Stress and Affect Detection*, ICMI 2018, DOI `10.1145/3242969.3242985`.
- Nguồn tác giả cho phép dùng cho khoa học, phi thương mại và yêu cầu ghi công khi công bố. Không mặc định là CC0/CC-BY hoặc dùng thương mại. Dữ liệu và kết quả dẫn xuất lưu local, không đưa lên Git.

## Trạng thái kiểm tra

- Đã kiểm tra endpoint chính thức trả file ZIP, kích thước `2.249.444.501` byte.
- Đã đọc thư mục trung tâm ZIP qua HTTP Range: 92 mục, tổng giải nén `17.578.304.666` byte; không phải chỉ 2,25 GB khi giải nén.
- Đã tải đầy đủ `archives/WESAD.zip`; kích thước, SHA-1/MD5 khớp checksum máy chủ nguồn. CRC của toàn bộ 92 mục ZIP đạt; bản README lấy trước qua HTTP Range cũng khớp nội dung trong ZIP đầy đủ.
- SHA-256: `5e15d2606adf16d819ba535c1786d92e94bae5ff5392f7ae01fb63f9938fd71c`.
- Đã lấy và đọc `WESAD/wesad_readme.pdf` nguyên gốc. Manifest và danh mục file được lưu local, không commit. Chưa giải nén toàn bộ tín hiệu.
- Đã kiểm kê cấu trúc/nhãn và các kênh cổ tay của đủ 15 người: [báo cáo bước 2](../../../../docs/ml/02-DATA-AUDIT.md).
- Đã chuẩn hóa, xuất dữ liệu và tính HR thử nghiệm đủ 15 người: [bước 3](../../../../docs/ml/03-WESAD-PREPARATION.md). HR chưa kiểm chứng sai số, chưa tạo feature cuối hoặc train model stress.

Không nhầm README của từng người (`S*_readme.txt`, thông tin nền cá nhân) với README kỹ thuật chung. Không đưa thông tin nền cá nhân vào feature mặc định.

## Phạm vi bài toán đầu tiên

Chỉ dùng kênh **cổ tay**. Dữ liệu ngực được giữ nguyên trong bản nén, không dùng làm đầu vào cho model triển khai trên thiết bị hiện tại.

| Mã gốc | Ý nghĩa theo README | `wesad-binary-v1` |
|---|---|---|
| 1 | Baseline | `NON_STRESS` (0) |
| 2 | Stress | `STRESS` (1) |
| 3 | Amusement | `NON_STRESS` (0) |
| 0 | Chưa xác định/chuyển tiếp | Loại |
| 4 | Meditation | Chưa dùng trong bài đầu |
| 5, 6, 7 | Tài liệu yêu cầu bỏ qua | Loại |

Đây là ánh xạ do dự án chọn cho bài nhị phân, không thay mã gốc. WESAD không cung cấp sẵn mức nhẹ/vừa/nặng. Nhãn điều kiện thí nghiệm không bảo đảm mọi người đều cảm thấy stress giống nhau.

Có 15 người có dữ liệu: `S2`–`S11`, `S13`–`S17`. Nghiên cứu tuyển 17 người nhưng loại S1/S12 vì cảm biến lỗi. Chia theo người; chưa chốt tập test hoặc cắt cửa sổ ở bước này.

## Đối chiếu đầu vào

| ASD-EASE | WESAD cổ tay | Đưa về chung |
|---|---|---|
| HR do MAX30102/firmware tính | BVP 64 Hz | Tính HR từ BVP bằng phương pháp có phiên bản; đánh giá thời gian và độ trễ. Không dùng HR giữ/nội suy trên UI |
| GSR ADC 12 bit, 20 Hz danh định | EDA 4 Hz, µS | Giữ khác đơn vị. Cần hiệu chuẩn hoặc đặc trưng tương đối đã kiểm chứng trước khi áp dụng model lên thiết bị |
| Ax/Ay/Az, 50 Hz danh định | ACC 32 Hz | Đã xác minh cả `ACC.csv` và `.pkl` ở 1/64 g; chuyển bằng `/64 * 9.80665`. Không chia 64 lần nữa khi dữ liệu đã được chuẩn hóa |
| Độ lớn gia tốc | Tính từ ba trục | `sqrt(Ax² + Ay² + Az²)`, sau khi thống nhất đơn vị; vẫn gồm trọng lực |
| RED/IR, gyro | Không có hai kênh RED/IR riêng hoặc gyro trong dữ liệu đồng bộ | Giữ dữ liệu thiết bị để hiển thị/chẩn đoán, chưa đưa vào model đầu |
| Không có nhiệt độ da | TEMP 4 Hz | Không dùng TEMP trong model đầu |

**Lưu ý HR:** README gốc yêu cầu bỏ qua `HR.csv`, `IBI.csv`, `tags.csv` trong gói E4 vì là thông tin dẫn xuất. Vì vậy không lấy `HR.csv` làm kênh chính rồi coi tương đương HR firmware. Bước xử lý tiếp theo dùng BVP đã đồng bộ để tính HR; không lấy ECG ngực làm feature thay HR cổ tay. ECG nếu dùng đánh giá riêng chỉ làm tham chiếu và phải ghi rõ.

Mỗi `.pkl` chứa `subject`, `signal.chest`, `signal.wrist` và `label`. Kênh cổ tay có ACC/BVP/EDA/TEMP, không có HR độc lập. Nhãn được lấy mẫu **700 Hz**, BVP/EDA/ACC giữ tần số riêng: ghép theo thời gian, không ghép theo chỉ số hàng.

Ưu tiên bản `.pkl` đã được tác giả đồng bộ. Dùng E4 ZIP thô trực tiếp cần xử lý chênh mốc thời gian với nhãn/ngực; không mặc định chúng cùng bắt đầu. Thời gian trong `S*_quest.csv` có dạng phút.giây, không phải phút thập phân.

## Lưu local và bước tiếp theo

```text
archives/WESAD.zip              Bản tải hoàn chỉnh; giữ file gốc
archives/WESAD.zip.part         Bản đang tải; không dùng train
raw/WESAD/wesad_readme.pdf      README gốc để đối chiếu
download-manifest.json          Nguồn, hash, kích thước và kiểm tra ZIP
archive-inventory.json          Danh mục file gốc, không commit
../../interim/wesad/audit-v1.json Kết quả kiểm kê đủ 15 người, không commit
```

Chưa giải nén toàn bộ bản dữ liệu để tránh tạo thêm khoảng 17,58 GB không cần ở bước chuẩn bị. Chỉ đọc/giải nén những file cần cho bước thẩm định tiếp theo; không sửa file gốc. Dùng Python 3 đọc pickle lịch sử có thể cần `encoding='latin1'`; chỉ đọc bản tải từ nguồn chính thức đã kiểm tra.

Bước tiếp: notebook kiểm chứng HR từ BVP trước khi chốt feature như [kế hoạch ML](../../../../docs/ml/README.md). Bài train đầu tiên chưa giải quyết xong chênh lệch GSR và chất lượng HR giữa E4/MAX30102 thì chưa được coi là model sẵn sàng chạy thật.
