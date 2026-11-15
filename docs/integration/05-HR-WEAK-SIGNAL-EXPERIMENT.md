# Thử thuật toán HR trên dữ liệu cổ tay yếu

Ngày 2026-11-07. Tiếp nối [bộ bốn lượt thu đầy đủ](05-HR-DATA-HANDOFF.md). Chỉ chạy offline, chưa sửa/nạp firmware hoặc thay dữ liệu DEVICE trên Dashboard. GSR/IMU giữ nguyên.

## Giả thuyết và cấu hình khóa trước chạy

Nhánh quality hiện loại cả cửa sổ khi một khoảng giữa đỉnh ngoài dải, hoặc ước tính từ 4 giây không khớp 8 giây. Dữ liệu đã thu cho thấy hai điểm này xảy ra nhiều; chưa biết đỉnh nào là nhịp thật do chưa có tham chiếu đồng bộ.

**Ứng viên A, `robust_peaks`:** giữ bộ lọc nhân quả đang chạy; giữ MSPTD tìm đỉnh, nhưng tính HR từ nhóm khoảng nhịp nhất quán thay vì loại cả cửa sổ vì một ngoại lệ. Không chèn đỉnh hoặc sửa timestamp. Tối thiểu bốn khoảng và 60% khoảng phải cùng nhóm, trong ±25% trung vị và dải 40–200 bpm. Chấm tổng hợp độ đều RR, hình dạng nhịp, phổ, tự tương quan và tính mới; cửa sổ 4 giây đóng góp bằng chứng thay vì phủ quyết cứng. Không ưu tiên dải 70–90 bpm.

Cấu hình đầu: score ≥0,65, tương quan ≥0,30, tỷ phần phổ ≥0,40; trọng số lần lượt RR/template/phổ/tương quan/recent là 0,25/0,20/0,25/0,20/0,10. Đây là giả thuyết kỹ thuật, không phải ngưỡng y khoa hay xác suất đúng. Hai lần liên tiếp phải khớp trong 12%, cách tối đa 1,5 giây và cùng segment; mất dữ liệu thì xóa xác nhận. Hai kênh đủ bằng chứng nhưng bất đồng cũng bị loại. Không lấy baseline hoặc số trước đó làm đáp án.

Nếu A không đạt, mới thử **ứng viên B**, tìm chu kỳ bằng phổ và tự tương quan để giảm lệ thuộc từng đỉnh. Tối đa hai thuật toán trong vòng này, không quét ngưỡng tới khi biểu đồ có số. Cấu hình B phải ghi trước khi chạy, không gọi lại dữ liệu đã xem là test mới.

## Cách chấm đã định trước

- Replay bốn lượt A1/B1/A2/B2 đo lại, cùng các cửa sổ giây 13–44. Chỉ ghi số ứng viên; không chấm đúng/sai trên cổ tay.
- BIDMC 01–10 đã xem trước đây: chỉ dùng hồi quy với HR ECG-monitor trung vị 8 giây, không gọi là kiểm độc lập hoặc nhãn từng nhịp.
- Bộ sạch 40–200 bpm và nhiễu trắng/có màu cũ; thêm mô phỏng sóng yếu ở 48/72/105/165 bpm, biên độ 6/20/60 counts, trôi nền, xung, đổi biên độ và hài mạnh. Có nhiễu không mạch, và ca nhiễu quang tuần hoàn báo riêng. Những con số mô phỏng không phải mô hình da/ánh sáng đã hiệu chuẩn.
- Khóa source, tham số, seed trước chạy. Development dùng seed 3411 và seed noise cũ; nếu đạt mới kiểm mô phỏng mới bằng seed 9011/9029 và noise 941/953. Không dùng vòng sau để chọn lại cấu hình.
- Điều kiện để đi tiếp: nhiễu không tuần hoàn không có HR giả; bộ sạch coverage ≥90%, MAE ≤2 bpm; BIDMC MAE không tăng quá 0,2 bpm, p95 không tăng quá 0,5 bpm, không thêm lỗi >10 bpm, không mất quá 5% số cửa sổ baseline đã nhận và phải cứu thêm cửa sổ có tham chiếu. Phần sóng yếu nhận thêm cần MAE ≤5 bpm, không thêm lỗi >10 bpm. Báo cả cửa sổ thiếu.

Các cửa sổ chồng nhau, không phải các lần đo độc lập. Ca nhiễu quang tuần hoàn giống nhịp phải báo số nhận nhầm; không giấu hoặc khẳng định PPG đơn thuần luôn phân biệt được. Đạt mô phỏng/hồi quy chưa xác nhận HR cổ tay chính xác.

## File và cách chạy

- `scripts/ppg_weak_candidate.py`: thuật toán thử, không được import vào firmware/backend.
- `scripts/benchmark_ppg_weak.py`: chạy bộ lọc C++ thật, đối chiếu dữ liệu và lưu checkpoint, input/source hashes; không mở COM hay publish MQTT.
- `scripts/test_ppg_weak_candidate.py`: kiểm ngoại lệ RR, dữ liệu lỗi, mất/xung đột tín hiệu và trạng thái xác nhận.

```powershell
.\.venv\Scripts\python.exe scripts/test_ppg_weak_candidate.py
.\.venv\Scripts\python.exe scripts/benchmark_ppg_weak.py
# Chỉ chạy sau khi development chọn được ứng viên và source chưa đổi:
.\.venv\Scripts\python.exe scripts/benchmark_ppg_weak.py --phase validation
```

Báo cáo trong `backend/storage/local/ppg-weak-*.json`, được Git bỏ qua; có `.lock.json` ghi trước khi chạy. Công cụ từ chối ghi đè báo cáo và không tự tải dữ liệu. File BIDMC local được kiểm checksum theo manifest nguồn đã lưu.

## Trạng thái

### A đã chấm, chưa đạt để chọn

Trên 4.670 cửa sổ BIDMC đã xem: baseline nhận 4.327, MAE 0,646 bpm, 14 lỗi >10 bpm; A nhận 4.470, MAE 0,582 bpm, 5 lỗi >10 bpm. A cứu thêm 168 cửa sổ, MAE phần cứu 1,226 bpm và không có lỗi >10 bpm trong phần cứu. Bộ nhiễu không tuần hoàn: 0/1.598 cửa sổ có HR giả.

Tuy vậy A không qua mốc coverage bộ sạch: 83,9%, bỏ toàn bộ nhịp 40 bpm do số đỉnh đủ để ước tính chưa đạt tối thiểu bốn khoảng. Mô phỏng hài mạnh 48 bpm còn 19 cửa sổ sai >10 bpm. Không chọn A chỉ vì MAE trung bình thấp. Với cổ tay: A1/A2 không có ứng viên, B1 5/32 và B2 đo lại 3/32, chưa có đáp án đối chiếu. Nhiễu quang tuần hoàn không có mạch vẫn được nhận 46/47 cửa sổ, giới hạn chưa giải quyết.

Báo cáo A giữ nguyên: `backend/storage/local/ppg-weak-development.json`, cùng lock/hashes và log. Không sửa A hoặc ngưỡng để che kết quả này.

### Khóa B trước vòng so thứ hai

**B, `period_consensus`:** dùng cùng bộ lọc C++ thực tế, bỏ xu hướng tuyến tính trên cửa sổ quá khứ; giới hạn ảnh hưởng xung vượt 6 lần MAD quy đổi trước ước tính. Đây là thao tác trên cửa sổ đã có, không dùng mẫu sau thời điểm dự đoán, không sửa raw. Lấy các đỉnh phổ có công suất ít nhất 20% đỉnh chính trong 40–200 bpm; đối chiếu cực đại tự tương quan gần chu kỳ đó. Zero-pad FFT 2.048 điểm chỉ nội suy phổ, không tăng độ phân giải vật lý của cửa sổ 8 giây. Biên phổ có dung sai nửa bin; HR cuối vẫn nằm 40–200 bpm.

Kết hợp tương quan 8 giây (trọng số 0,35), tương quan ở 6 giây gần nhất tại cùng chu kỳ (0,25) và tỷ phần phổ cơ bản/các hài (0,40). Yêu cầu tối thiểu tương quan lần lượt 0,35/0,20, tỷ phần phổ 0,45, tổng 0,60. Năng lượng 1,5 giây cuối phải còn ít nhất 12% trung bình toàn cửa sổ; không hiện lại nhịp quá khứ khi tín hiệu đã mất. Nếu đỉnh chính là hài, chỉ chọn chu kỳ dài gấp đôi khi có năng lượng cơ bản ≥25% đỉnh chính và tổng bằng chứng kém tối đa 0,10 so với ứng viên tốt nhất; không tự chia mọi số HR cho hai.

B giữ cùng quy tắc xác nhận/mất dữ liệu/xung đột hai kênh của A. Một cấu hình duy nhất; giữ nguyên tiêu chí chọn đã ghi phía trên. Đã qua 10 test logic, gồm 40/200 bpm, pha khác nhau, hài mạnh và không điền HR cũ. Chưa có kết quả benchmark B tại thời điểm khóa này.

Vòng B chạy cả A để so trên cùng input; đây là dữ liệu phát triển/hồi quy đã xem, không phải validation. Báo cáo mới không ghi đè A:

```powershell
.\.venv\Scripts\python.exe scripts/benchmark_ppg_weak.py --report backend/storage/local/ppg-weak-round2-development.json
```

Nếu có ứng viên đạt, vòng mô phỏng mới phải truyền `--development-report backend/storage/local/ppg-weak-round2-development.json` và tên `--report` mới. Không dùng vòng đó để chọn lại tham số. Chưa đổi firmware, chưa yêu cầu đo thêm.

### Kết quả development B, khóa để kiểm seed mới

B qua các điều kiện development đã định trước. Trên BIDMC đã xem: nhận 4.474/4.670 cửa sổ, MAE 0,631 bpm, p95 1,642 bpm, 12 lỗi >10 bpm so với 14 của baseline. **Có một lỗi >10 bpm trong 173 cửa sổ B nhận thêm**; tổng lỗi ít hơn không có nghĩa mọi cửa sổ được cứu đều đúng. Không giấu lỗi này.

Bộ sạch: 322/329 cửa sổ, MAE 0,006 bpm. Mô phỏng sóng yếu: 1.497/2.256 cửa sổ, MAE 0,275 bpm, không lỗi >10 bpm; phần 204 cửa sổ nhận thêm MAE 0,679 bpm. Nhiễu không tuần hoàn: 0/1.598. Nhiễu quang tuần hoàn vẫn bị nhận 46/47; giới hạn chưa giải quyết. Những số này chỉ áp dụng bộ mô phỏng đã mô tả.

Trên bốn lượt cổ tay: A1 0/32, B1 3/32, A2 0/32, B2 đo lại 0/32. B mạnh hơn trên mô phỏng nhưng **chưa chứng minh khôi phục HR ổn định trên cụm cổ tay thật**. Không chọn chỉ theo điểm trung bình và không tuyên bố đã giải quyết phần quang học.

Chọn B để kiểm seed mô phỏng mới; giữ nguyên code/ngưỡng. Bản sao 10 source có hash trong `backend/storage/local/hr-weak-round2-sources-20261107/`, không chỉ lưu một hash rồi mất source. A vẫn là đối chứng bị loại, không phát triển thêm thuật toán thứ ba.

```powershell
.\.venv\Scripts\python.exe scripts/benchmark_ppg_weak.py --phase validation --development-report backend/storage/local/ppg-weak-round2-development.json --report backend/storage/local/ppg-weak-round2-validation.json
```

Chỉ xác nhận vòng seed mới đạt nếu vẫn không nhận nhiễu không tuần hoàn, bộ sạch coverage ≥90%/MAE ≤2 bpm, phần sóng yếu nhận thêm MAE ≤5 bpm/không lỗi >10 bpm; báo riêng lỗi hài, coverage và ca nhiễu tuần hoàn. Chưa có kết quả vòng seed mới tại thời điểm ghi mục này.

## Kết luận sau vòng seed mới

**Đã hoàn tất hai ứng viên, chưa có bản đạt để nạp.** Không đổi tiêu chí sau khi thấy kết quả, không chuyển lại A vì B thất bại, không thử thuật toán thứ ba trong vòng này.

| Phép kiểm B trên mô phỏng mới | Kết quả |
|---|---|
| Bộ sạch | 322/329 cửa sổ; MAE 0,006 bpm; đạt |
| Nhiễu không tuần hoàn | 0/893 có HR giả; đạt |
| Sóng yếu có nhịp gốc | 2.959/4.512 có kết quả; MAE 0,295 bpm, p95 1,003 bpm |
| Phần B nhận thêm khi đối chứng không có HR | 425 cửa sổ; MAE 0,903 bpm; **một lỗi >10 bpm, không đạt** |
| Nhiễu quang tuần hoàn không có mạch | B nhận 46/47 ở mỗi seed 9011 và 9029; đối chứng 47/47. Giới hạn chưa giải quyết |

Lỗi nằm ở `strong_harmonic_165_6_seed9029`, cửa sổ kết thúc giây 18: nhịp gốc **165 bpm**, B trả **81,656 bpm**, đối chứng không trả HR. Đây là nhận nhầm nửa nhịp trên tín hiệu rất yếu. Sai số trung bình thấp không bù được lỗi này theo tiêu chí đã khóa. Không xóa cửa sổ hoặc đổi nhãn mô phỏng để đạt.

Trên cổ tay thật, B chỉ có 3/32 cửa sổ B1; A1/A2/B2 đo lại không có. Chưa đạt mục tiêu HR cổ tay ổn định và đúng tương đương. Không có tham chiếu nên chưa biết các số được khôi phục có đúng hay không; không kết luận MAX30102 không thể đo cổ tay hoặc bắt buộc thay phần cứng.

### Bàn giao và kiểm thử

- Hai thuật toán offline; runner khóa source/checksum/seed, lưu checkpoint nguyên tử. Không mở COM, publish MQTT hoặc sửa firmware.
- 10 test mới và 31 ca hồi quy chấm điểm/quality/capture đạt. Thêm test mới vào job `AI tests` hiện có; chưa chạy CI GitHub từ xa.
- Dự đoán A ở hai báo cáo khớp từng cửa sổ, input hashes khớp. Source development B và vòng seed mới giữ nguyên, đã kiểm 10 hash.
- [Hình so sánh và lỗi nửa nhịp](../../backend/storage/local/ppg-weak-round2-results.png), [kết luận máy đọc được](../../backend/storage/local/ppg-weak-round2-assessment.json). Đã xem hình, không nối đường qua HR thiếu.
- Báo cáo đầy đủ: `ppg-weak-round2-development.json`, `ppg-weak-round2-validation.json`; script tái hiện hình/kết luận: `backend/storage/local/hr-weak-round2-sources-20261107/analyze_results.py`. Raw cá nhân và bản sao source khóa nằm trong thư mục ignored, không đưa lên Git.

### Điểm dừng và điều kiện mở vòng tiếp

Giữ bản đối chứng `0.3.13-led10`; **không port/nạp ứng viên chưa đạt**, không nới cổng hoặc giữ số HR cũ để tăng độ kín biểu đồ. Chưa cần cắm USB, đặt tay hoặc lặp lại cùng phép đo A/B.

Bằng chứng mới cần trước vòng tiếp: HR đồng thời ở đúng vị trí cổ tay để phân biệt chu kỳ đúng với nửa/gấp đôi nhịp. Đếm mạch đủ 60 giây cho mốc thô, không thay nhãn đồng bộ từng cửa sổ; nếu chưa có thì ghi chưa có, không bắt mua thiết bị. Giả thuyết phần mềm tiếp theo phải xử lý lỗi đã thấy: phân biệt cơ bản/hài khi thành phần cơ bản yếu mà vẫn giữ nhịp thật. Không chỉ tăng LED, làm phẳng biểu đồ hoặc quét ngưỡng tiếp trên bốn trace này.

**Mốc thu và vòng thuật toán offline đã xong; HR cổ tay và nghiệm thu nhánh 5 chưa xong.** Chưa commit/push/merge, chưa xác nhận xử lý nhiệt; không đổi GSR/IMU hoặc schema của người dùng trong vòng này.
