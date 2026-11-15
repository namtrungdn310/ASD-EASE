# Đối chiếu thuật toán HR với dữ liệu có nhịp tham chiếu

Ngày 2026-11-06, bản 0.3.10 sửa lỗi chọn chu kỳ dài gấp đôi khi biên độ xung lớn nhỏ xen kẽ. Ca tổng hợp 80 bpm từng trả 40 bpm, nay đạt. Bỏ điều kiện đỉnh phải đạt 90% đỉnh mạnh nhất; vẫn cần đỉnh tự tương quan tối thiểu 0,60, kiểm tra cửa sổ 8s/4s và hai lượt nhất quán. Không giữ số cũ khi cửa sổ bị từ chối.

## Nguồn và cách kiểm tra

Dùng recording 01–05 của [BIDMC PPG and Respiration Dataset 1.0.0](https://physionet.org/content/bidmc/1.0.0/), Pimentel và cộng sự, DOI 10.13026/C2208R. Giữ LICENSE Open Data Commons Attribution 1.0 cùng bản tải. Script kiểm SHA256 CSV và LICENSE theo manifest của nguồn; dữ liệu và báo cáo nằm trong `backend/storage/local/`, được Git bỏ qua.

- Đưa sóng PLETH 125Hz qua FIR 161 tap/Hann, cutoff 20Hz rồi đổi về 50Hz. Khôi phục clock index/125 sau khi kiểm tra sai số làm tròn timestamp CSV không quá 5ms.
- Ánh xạ cố định `IR=100000+PLETH*10000`, RED phẳng 80000; không nhân đôi một sóng thành hai kênh độc lập. Đây là counts giả lập, không phải nhiễu ADC của MAX30102.
- Chạy đúng header C++ `processing/ppg_rate.h` qua harness replay. Không gửi các số này lên MQTT, DB hoặc Dashboard.
- Đối chiếu HR được chấp nhận với trung vị HR tham chiếu từ ECG trong 8s trước đó; không dùng cột PULSE từ PPG làm đáp án. Chỉ chấm cửa sổ có đủ ít nhất 8 giá trị tham chiếu hữu hạn trong 40–200 bpm; bỏ đoạn đầu dưới 12s và giây cuối.
- Cửa sổ cập nhật mỗi giây và chồng nhau. Báo đồng thời tỷ lệ có kết quả và sai số trên phần có kết quả; không tính trường hợp bị từ chối thành sai số bằng 0.

## Kết quả trên cùng 2.335 cửa sổ đủ điều kiện

| Chỉ số | 0.3.9 | 0.3.10 |
|---|---:|---:|
| Cửa sổ có HR được chấp nhận | 1.912 | 2.108 |
| Tỷ lệ có kết quả | 81,88% | 90,28% |
| MAE trên phần được chấp nhận | 3,27 bpm | 0,87 bpm |
| Phân vị 95 của sai số tuyệt đối | 44,56 bpm | 1,77 bpm |
| Cửa sổ sai trên 10 bpm | 116 | 14 |

Vẫn có lỗi: recording 03 còn 5 cửa sổ sai trên 10 bpm; recording 04 còn 9, sai số lớn nhất khoảng 48,11 bpm. Không tuyên bố đã loại hết lỗi nửa nhịp. Báo cáo local `ppg-reference-039.json` và `ppg-reference-0310.json` giữ từng ước tính, hash header và hash nguồn.

Đây là **bộ đối chiếu phát triển đã dùng tìm và sửa lỗi**, không phải tập đánh giá độc lập. Sóng lâm sàng đã qua thiết bị khác và tiền xử lý offline; không chứng minh MAX30102 đo chính xác tại cổ tay, không thay nghiệm thu board. Chưa có nhịp tham chiếu cho các lượt đo trên Trung.

## Chạy lại

Cần NumPy trong môi trường Python của dự án và g++/clang++. Trên máy Trung:

```powershell
$env:CXX = 'C:\msys64\ucrt64\bin\g++.exe'
.\.venv\Scripts\python.exe scripts/benchmark_ppg_reference.py --records 1 2 3 4 5 --report backend/storage/local/ppg-reference-0310.json
```

Nếu chưa có dữ liệu local, thêm `--download` để tải từ PhysioNet và kiểm hash; mặc định script không truy cập mạng. Bài này không yêu cầu CI tải dataset. Kiểm thử hồi quy không cần mạng nằm trong `scripts/check_sensor_drivers.py`: 76 ca HR, gồm 5 ca biên độ xen kẽ; 49 ca driver và 12 snapshot qua serializer/schema. Bộ thử nhiễu hữu hạn có 0/2.400 cửa sổ được chấp nhận, không phải bảo đảm không bao giờ nhận nhầm nhiễu.
