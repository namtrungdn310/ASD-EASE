# Bước 3: chọn ứng viên HR kèm chất lượng tín hiệu

Ngày2026-11-06. **Đã chọn ứng viên offline `hybrid_strict` sau hai vòng kiểm. ESP vẫn chạy0.3.11.** Chưa chuyển bộ mới sang firmware C++, chưa đo tài nguyên ESP hoặc nghiệm thu sai số cổ tay.

## Ứng viên làm gì?

Giữ nguyên kết quả khi bộ HR C++ hiện tại công nhận hợp lệ. Khi bộ đó không có HR, thử ứng viên MSPTDfastv2 có thêm kiểm độ đều khoảng nhịp, hình dạng sóng theo template leave-one-out và năng lượng phổ. Cần hai cửa sổ liên tiếp đạt mới bổ sung kết quả; thiếu mẫu, đổi đoạn hoặc không đạt thì xoá xác nhận, không giữ HR cũ.

Các ý tưởng chất lượng tham khảo [PPG-quality](https://ppg-quality.readthedocs.io/en/latest/functions/assess_ppg_quality/); ngưỡng là lựa chọn kỹ thuật chưa kiểm định của dự án, không nhận là ngưỡng từ công bố đó. [Chính sách được ghi trước benchmark](05-PPG-QUALITY-POLICY.md) giữ hai cấu hình cân bằng/chặt. Chốt cấu hình theo dữ liệu tham chiếu và nhiễu, không lấy số cổ tay trông đẹp làm đáp án.

## Kết quả vòng phát triển

Dùng4 file đo trên Trung, BIDMC01–10 và38 tín hiệu tổng hợp. Các dữ liệu đã xem được coi là bộ phát triển. Hai bộ dùng chung bộ lọc C++/mốc chấm của bước2; đã kiểm kết quả đối chứng và HR tham chiếu giống hệt bước2 ở mọi bản ghi chung.

| Chỉ số trên4.670 cửa sổ tham chiếu | Đối chứng0.3.11 | Hybrid cân bằng | Hybrid chặt |
|---|---:|---:|---:|
| Có HR | 4.327 | 4.425 | 4.391 |
| Tỷ lệ có HR | 92,66% | 94,75% | 94,03% |
| MAE trên phần có HR | 0,646bpm | 0,658bpm | 0,653bpm |
| Sai số phân vị95 | 1,631bpm | 1,675bpm | 1,655bpm |
| Cửa sổ sai trên10bpm | 14 | 14 | 14 |
| Cửa sổ tham chiếu nhận thêm | 0 | 98 | 64 |

Chỉ xét phần64 cửa sổ nhận thêm của mức chặt: MAE1,117bpm, không có cửa sổ sai trên10bpm. Những cửa sổ đối chứng đã valid được giữ nguyên giá trị, không đổi số để cải thiện điểm. Các lỗi của đối chứng cũng được giữ nguyên, vì vậy vẫn còn14 lỗi lớn ở bảng trên.

### Chống nhận nhầm nhiễu

30 lượt nhiễu trắng/màu từ5 seed,3 mức counts, tổng1.410 cửa sổ; thêm47 cửa sổ sóng phẳng thành1.457. Mức cân bằng nhận nhầm **1 cửa sổ** ở `SYNTHETIC_colored_73_1000`, giây22, khoảng48,39bpm, nên bị loại đúng tiêu chí trước đó. Mức chặt và đối chứng đều0/1.457. Không xoá ca này để chọn mức cân bằng có coverage cao hơn.

## Vòng kiểm cấu hình đã chốt

Sau khi chọn mức chặt, khóa source hash/policy hash rồi mới tải BIDMC11–15 và dùng seed nhiễu mới907/911/919/929/937. Không chỉnh ngưỡng sau khi xem kết quả này, không đổi sang cân bằng dù cân bằng có thể đạt ở vòng mới. Đây là vòng kiểm bổ sung của ứng viên thử nghiệm, chưa phải bằng chứng lâm sàng hoặc đại diện mọi loại nhiễu/điều kiện cổ tay.

| Chỉ số trên2.335 cửa sổ tham chiếu mới | Đối chứng | Hybrid chặt |
|---|---:|---:|
| Có HR | 2.107 | 2.150 |
| Tỷ lệ có HR | 90,24% | 92,08% |
| MAE trên phần có HR | 0,6234bpm | 0,6238bpm |
| Sai số phân vị95 | 1,6925bpm | 1,6959bpm |
| Cửa sổ sai trên10bpm | 2 | 2 |
| Cửa sổ tham chiếu nhận thêm | 0 | 43 |
| MAE chỉ trên43 cửa sổ mới | — | 0,6434bpm |

Không có lỗi trên10bpm ở43 cửa sổ mới. Hai lỗi lớn vẫn là kết quả đã được đối chứng công nhận, ứng viên chưa sửa chúng. Bộ nhiễu seed mới có1.410 cửa sổ cộng47 phẳng: đối chứng và hybrid chặt đều0/1.457. Các cửa sổ chồng nhau, không phải1.457 phép thử độc lập hoặc bảo đảm mọi nhiễu đều bị loại.

Mức chặt qua toàn bộ điều kiện chốt trước: không thêm nhận nhầm nhiễu, không tăng lỗi trên10bpm, MAE không tăng quá0,2bpm, p95 không tăng quá0,5bpm và có thêm cửa sổ tham chiếu. Tỷ lệ/sai số phải đọc cùng nhau; MAE trên phần được mỗi bộ chấp nhận không phải cùng mẫu số. Trên các cửa sổ chung, hybrid giữ nguyên kết quả đối chứng theo thiết kế.

## Kết quả trên file cổ tay

Replay từ đầu file, bỏ đầu13s nên mỗi file có32 mốc, khác mẫu số41 frame live. Chưa có HR tham chiếu cho các file này.

| File | Đối chứng | Hybrid chặt | Giới hạn |
|---|---:|---:|---|
| Đầu ngón tay174444 | 27/32 | 27/32 | Không tăng ở lượt này |
| Cổ tay174808 | 6/32 | 13/32 | Ứng viên bổ sung khoảng70,2..78,4bpm; chưa chứng minh sai số |
| Cổ tay cố định/không ấn175215 | 0/32 | 0/32 | Vẫn chưa có cửa sổ đủ bằng chứng |
| Ngón tay022934 có gap6,221s | 0/32 | 0/32 | Không nối mẫu hoặc lấp số qua khoảng mất |

Kết quả cho phép thử một hướng bổ sung HR có kiểm chất lượng; **không chứng minh đã giải quyết HR cổ tay ổn định**. Mức chặt chưa giúp file cổ tay cuối, không hạ ngưỡng để ép file đó có số.

## Cấu hình được bàn giao

[PPG_QUALITY_CANDIDATE_V1.json](../contracts/PPG_QUALITY_CANDIDATE_V1.json) ghi cấu hình `hybrid_strict`, toàn bộ điều kiện chung, source/policy hash và kết quả hai vòng. Đây là đặc tả ứng viên offline, **không phải payload MQTT hoặc file cấu hình thiết bị đang chạy**.

- CV khoảng nhịp≤0,12; cần ít nhất5 đỉnh/4 khoảng.
- Trung vị tương quan template≥0,90, phân vị20≥0,75.
- Tỷ lệ năng lượng quanh tần số ứng viên/hài trong băng0,5..4Hz≥0,65.
- So8s/4s và xác nhận hai cửa sổ, giới hạn mới/cũ/đổi đoạn như policy đã ghi.
- Hai kênh rõ nhưng bất đồng thì từ chối; còn lại ưu tiên IR rồi RED. Chất lượng không được xuất thành xác suất hoặc phần trăm MQTT.

Có pha của sóng40bpm không đủ5 đỉnh trong8s sau xử lý biên; nhánh quality từ chối, hybrid vẫn giữ40 nếu đối chứng valid. Kiểm độ đều có thể từ chối nhịp không đều. Nhiễu tuần hoàn có hình dạng giống mạch vẫn có thể lọt; bộ thử hiện tại không chứng minh phân biệt được mọi loại nhiễu đó.

## File và kiểm thử

- `scripts/ppg_quality_candidate.py`: đặc trưng, hai policy, chọn kênh/xác nhận và hybrid; không nhận HR tham chiếu làm đầu vào.
- `scripts/benchmark_ppg_quality.py`: vòng phát triển/validation, kiểm hash trước validation và quyết định chọn theo tiêu chí đã chốt.
- `scripts/benchmark_ppg_candidates.py`: hook cho ứng viên, cập nhật state ở cả mốc thiếu nhãn tham chiếu; nhãn thiếu không được ảnh hưởng hoạt động của ứng viên.
- `scripts/test_ppg_quality_candidate.py`:15 ca, gồm xóa xác nhận, đổi đoạn, stale, bất đồng hai kênh, giữ baseline và độc lập với nhãn tham chiếu.
- `scripts/test_ppg_quality_pipeline.py`:4 ca chạy bộ lọc/HR C++ thật cùng ứng viên, gồm sóng sạch, nhiễu trắng/màu và gap.
- `scripts/test_ppg_quality_selection.py`:4 ca, gồm loại cấu hình nhận nhầm và không chọn ứng viên sai số lớn.

Tổng kiểm công cụ offline:47 ca port MSPTD+6 ca chấm+15 quality+4 pipeline+4 chọn=**76 ca đạt local**. Ba bài mới được thêm vào job AI tests hiện có; giữ6 tên check, không tải dataset hoặc cần ESP trong CI. Chưa chạy CI từ xa, chưa commit/push/merge ở lượt này.

Chạy lại tại root, với NumPy và g++/clang++:

```powershell
$env:CXX = 'C:\msys64\ucrt64\bin\g++.exe'
.\.venv\Scripts\python.exe scripts/test_ppg_quality_candidate.py
.\.venv\Scripts\python.exe scripts/test_ppg_quality_pipeline.py
.\.venv\Scripts\python.exe scripts/test_ppg_quality_selection.py
.\.venv\Scripts\python.exe scripts/benchmark_ppg_quality.py --phase development
.\.venv\Scripts\python.exe scripts/benchmark_ppg_quality.py --phase validation
```

Thêm `--download` nếu chưa có dữ liệu PhysioNet. Validation bắt buộc giữ đúng source/policy đã chốt ở development; source thay thì báo lỗi thay vì giả vẫn là vòng kiểm cấu hình cũ. Lệnh development dùng4 trace local trên máy Trung; chưa phải tool thu/gửi dữ liệu người thật từ máy khác. Raw/log/JSON đầy đủ lưu `backend/storage/local/ppg-quality-development.*` và `ppg-quality-validation.*`, Git bỏ qua.

## Điểm nối sang bước 4

Đã đủ bằng chứng để chọn **ứng viên thử nghiệm hybrid chặt**, chưa đủ để nạp mã Python hoặc tuyên bố firmware đã đổi. Việc tiếp theo là chuyển ứng viên sang C++, đối chiếu kết quả với bản offline và đo RAM/stack/thời gian xử lý để không làm gián đoạn lấy mẫu. Chỉ sau đó mới nạp bản thử và đo đầu ngón tay/cổ tay; vẫn cần nhịp tham chiếu để xác nhận sai số trên người.
