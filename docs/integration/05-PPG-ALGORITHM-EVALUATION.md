# Bước 2: đối chiếu thuật toán HR

Ngày 2026-11-06. **Đã chạy đối chiếu offline; ESP vẫn dùng 0.3.11.** Không đổi LED, lấy mẫu, bộ HR đang chạy hoặc schema. Chưa nghiệm thu HR cổ tay, chưa có nhịp tham chiếu cho các file đo trên Trung.

## Đối chiếu những gì?

- Bộ sản phẩm: `processing/ppg_rate.h`, chạy bằng C++ thực qua harness riêng trên laptop.
- Ứng viên: bản chuyển NumPy của lõi **MSPTDfast v2**, lấy từ mã Peter H. Charlton, [commit c397be7afc0d8a1601a85cd673718372e40f1f59](https://github.com/peterhcharlton/ppg-beats/blob/c397be7afc0d8a1601a85cd673718372e40f1f59/source/msptdfastv2_beat_detector.m). Giữ ghi công và giấy phép MIT trong bản chuyển. Hash file MATLAB gốc: `39f5010f1d485f2dc180bffbbe662dc9bd16e8116bd1ae630761f1e2b58bcabd`.
- Mỗi ứng viên dùng cùng sóng đã qua bộ lọc C++ sản phẩm: HP0,5Hz/LP4Hz, FIFO50Hz danh định, khởi tạo DC, cổng tiếp xúc và tách đoạn mất mẫu. Bộ hiện tại xét cả IR/RED; MSPTD được báo riêng từng kênh, không dùng đáp án để chọn kênh tốt hơn.
- Dùng cửa sổ dữ liệu quá khứ8s, chấm mỗi1s từ giây13. MSPTD chia nội bộ6s/overlap20%, giảm50→25Hz bằng hệ số2, scale tối thiểu30bpm và chỉnh đỉnh trong50ms theo mã nguồn. HR ứng viên tính từ số đỉnh và khoảng thời gian đỉnh đầu-cuối, giữ dải40..200bpm.
- **MSPTD ở đây chưa có cổng chất lượng tín hiệu.** Một HR ứng viên không tương đương `valid=true` của driver. Vì thế số ứng viên nhiều hơn chưa chứng minh đo tốt hơn.
- Không dùng mẫu tương lai; không lấp khoảng không có mẫu bằng dự đoán đã cũ. MSPTD cần đủ500 mẫu cùng đoạn:100 mẫu warmup bộ lọc và400 mẫu cửa sổ. Mẫu mới nhất quá40ms so với mốc chấm bị loại khỏi cả hai bộ.

Đây là phép thử với tiền xử lý chung để tách ảnh hưởng bộ phát hiện, **không tái lập toàn bộ pipeline bài báo**. [Nghiên cứu gốc](https://pmc.ncbi.nlm.nih.gov/articles/PMC11894679/) dùng quy trình tiền xử lý/hậu xử lý khác. Máy chưa có MATLAB/Octave nên chưa chạy binary MATLAB gốc; bản chuyển đã đối chiếu vòng lặp nguyên bản và kiểm tín hiệu chuẩn, không được mô tả là đã chứng minh tương đương toàn bộ toolbox.

## Dữ liệu có HR tham chiếu

Dùng [BIDMC1.0.0](https://physionet.org/content/bidmc/1.0.0/), giữ LICENSE và xác minh SHA256 CSV theo manifest chính thức. HR tham chiếu là trung vị HR từ ECG trong8s trước mốc chấm, không dùng cột PULSE từ PPG. Đây là HR monitor1Hz, không phải nhãn từng nhịp để tính F1. Loại tham chiếu thiếu/không hữu hạn/ngoài40..200bpm. Việc đổi125→50Hz giữ như công cụ đối chiếu trước: FIR161tap/Hann20Hz, clock index/125 sau kiểm sai số timestamp CSV, ánh xạ counts cố định; RED phẳng ở phần BIDMC, chỉ IR mang PLETH.

Bản ghi01–05 đã dùng tìm lỗi0.3.10. Bản ghi06–10 được bổ sung ở bước này, không dùng chỉnh ngưỡng. Các ca này chưa đủ đại diện mọi người/điều kiện, không gọi là nghiệm thu lâm sàng hoặc test niêm phong độc lập; trong quá trình hoàn thiện bản chuyển có chạy lại sau sửa phép đổi chỉ số và kiểm cách chấm.

### Kết quả trên phần mỗi bộ có kết quả

| Nhóm | Bộ hiện tại: tỷ lệ có HR | MAE trên phần có HR | MSPTD-IR: tỷ lệ có ứng viên | MAE trên phần có ứng viên |
|---|---:|---:|---:|---:|
| BIDMC01–05,2.335 cửa sổ | 90,28% | 0,84bpm | 99,61% | 1,59bpm |
| BIDMC06–10,2.335 cửa sổ | 95,03% | 0,46bpm | 100% | 0,75bpm |

Nhóm01–05: số cửa sổ sai trên10bpm là14 với bộ hiện tại,67 với MSPTD-IR. Nhóm06–10: lần lượt0 và13. Phải đọc cả tỷ lệ có kết quả và sai số; các bộ từ chối những cửa sổ khác nhau nên MAE trên phần riêng chưa phải so sánh ngang hoàn toàn.

### Chỉ so trên cửa sổ cả hai cùng có kết quả

| Nhóm | Số cửa sổ chung | MAE bộ hiện tại | MAE MSPTD-IR |
|---|---:|---:|---:|
| BIDMC01–05 | 2.108 | 0,84bpm | 0,82bpm |
| BIDMC06–10 | 2.219 | 0,46bpm | 0,50bpm |

Chênh lệch nhỏ trên phần chung; các đoạn khó được MSPTD tạo thêm ứng viên đóng góp nhiều sai số ở bảng trước. Không kết luận MSPTD nói chung kém hơn hoặc bộ hiện tại đã tối ưu từ phép thử này. Con số0,84 khác báo cáo0,87 trước do chấm ở lưới giây nguyên/cached estimate thay vì chỉ mốc cập nhật native; cả hai bộ ở báo cáo này dùng cùng mốc tham chiếu.

## Sóng đo của Trung

Tất cả là replay cùng file, khởi tạo lại bộ lọc ở đầu file và bỏ đầu13s. Mỗi file dưới có32 mốc chấm; kết quả không phải mẫu số41 frame live vì thời gian bắt đầu/trạng thái bộ lọc khác.

| File đo | Bộ hiện tại | MSPTD-IR | MSPTD-RED |
|---|---:|---:|---:|
| Ngón tay0.3.11,174444 | 27/32,68,4..74,9bpm | 32/32,67,3..90,6 | 32/32,67,3..80,5 |
| Cổ tay0.3.11,174808 | 6/32,71,1..74,3bpm | 32/32,55,8..84,8 | 32/32,50,5..116,9 |
| Cổ tay giữ cố định/không ấn,175215 | 0/32 | 29/32,40,4..112,1 | 31/32,40,7..97,6 |

**Chưa có HR tham chiếu cho các file này**, nên không chấm MAE hoặc chọn kết quả nhìn hợp lý làm đáp án. MSPTD làm xuất hiện nhiều số hơn nhưng vẫn biến thiên lớn trên file cổ tay; chưa có căn cứ nạp thay bộ hiện tại.

File ngón tay0.3.10 có khoảng mất6,221s cũng được kiểm:32 mốc chấm,6 mốc không có mẫu mới,11 mốc MSPTD chưa đủ lịch sử liên tục; bộ hiện tại0 HR, MSPTD mỗi kênh20 ứng viên. Không giả nối qua khoảng mất mẫu.

## Kiểm nhiễu và tín hiệu chuẩn

30 lượt nhiễu trắng/màu, seed17/37/73/101/211 và mức10/100/1000counts, mỗi lượt60s: tổng1.410 mốc chấm sau warmup. Đây là nhiễu sinh tổng hợp không có nhịp tim, hai kênh tương quan theo cách sinh; không coi là hai phép đo độc lập.

| Bộ | Số mốc tạo HR/ứng viên trong nhiễu |
|---|---:|
| Hiện tại | 0/1.410 |
| MSPTD-IR chưa cổng chất lượng | 1.197/1.410 |
| MSPTD-RED chưa cổng chất lượng | 1.208/1.410 |

Đây không phải lỗi bất ngờ của một bộ tìm đỉnh: nó chưa thực hiện nhiệm vụ quyết định có mạch đập đủ tin cậy hay không. Kết quả chứng minh **không dùng trực tiếp ứng viên MSPTD làm HR hợp lệ**. Bộ hiện tại từ chối được bộ nhiễu hữu hạn này, không phải bảo đảm không bao giờ nhận nhầm.

Các sóng sạch40/60/80/100/150/180/200bpm đều có47/47 cửa sổ sau warmup ở cả hai bộ; sai số trên sóng sạch dưới0,2bpm. Sóng phẳng không có kết quả ở cả hai. Tín hiệu tổng hợp không thay nghiệm thu board.

## File và cách chạy lại

- `scripts/ppg_msptd_reference.py`: bản chuyển offline; không import vào backend/firmware.
- `ai/edge_firmware/tests/native/ppg_benchmark_harness.cpp`: chạy bộ HR và chính bộ lọc C++ sản phẩm trên laptop; không nằm trong build firmware. Truy cập lớp lọc private chỉ trong translation unit benchmark.
- `scripts/benchmark_ppg_candidates.py`: kiểm hash dữ liệu, chấm chung, lưu kết quả từng mốc/source hash/định nghĩa pipeline.
- `scripts/test_ppg_msptd_reference.py`:47 ca hồi quy bản chuyển.
- `scripts/test_ppg_candidate_scoring.py`:6 ca chấm, gồm mất mẫu, không lấp dự đoán cũ, chờ lịch sử sau gap, thiếu HR tham chiếu và timestamp lùi.

Trên máy Trung, tại root:

```powershell
$env:CXX = 'C:\msys64\ucrt64\bin\g++.exe'
.\.venv\Scripts\python.exe scripts/test_ppg_msptd_reference.py
.\.venv\Scripts\python.exe scripts/test_ppg_candidate_scoring.py
.\.venv\Scripts\python.exe scripts/benchmark_ppg_candidates.py --records 1 2 3 4 5 6 7 8 9 10
```

Nếu chưa có CSV BIDMC local, thêm `--download`. Mặc định benchmark dùng4 file đo trên máy Trung; máy khác truyền `--trace <file.csv>` cho từng file của mình. Không yêu cầu Trung chia sẻ file đo người thật. Cần NumPy2.2.1 như ai/requirements.txt và g++/clang++; không thêm SciPy hoặc thư viện firmware.

CI thêm47+6 ca vào job **AI tests** hiện có; không tải dataset, không cần ESP/credential và giữ nguyên6 tên check. Đã chạy53 ca local và harness C++ với `-Wall -Wextra -Werror`; chưa có CI từ xa/commit/push mới.

Báo cáo đầy đủ: `backend/storage/local/ppg-candidates-step2.json`, log cùng thư mục; Git bỏ qua. Bản nguồn MATLAB cùng manifest nằm trong `ppg-beats-c397be7afc0d/` ở thư mục local. Thời gian chạy NumPy trên laptop không phải thời gian/stack/heap của ESP32; chưa đo tài nguyên bản port trên board.

## Quyết định sau bước 2

1. Giữ firmware0.3.11 làm đối chứng; **chưa thay trực tiếp bằng MSPTD**.
2. Bước3 cần đánh giá ứng viên có lớp chất lượng tín hiệu đi kèm trước khi chọn chạy thật; dùng đồng thời tỷ lệ có HR, sai số trên cùng cửa sổ và số nhận nhầm nhiễu. Không chọn theo độ mượt biểu đồ.
3. Những ngưỡng hoặc cách chọn kênh mới phải được chốt trước lượt đối chiếu mới; dữ liệu đã xem ở bước này là bộ phát triển. Không gọi các bản ghi đã xem là test chưa đụng tới.
4. Chỉ khi ứng viên đạt phần mềm và đo được tài nguyên ESP mới chuyển sang thử đầu ngón tay/cổ tay có tham chiếu ở bước4. Chưa có thiết bị tham chiếu thì ghi thiếu bằng chứng, không tuyên bố tối ưu nhất hoặc HR đúng.
