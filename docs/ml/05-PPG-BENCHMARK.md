# Bước 4B — Đối chiếu phương pháp PPG đã công bố (MSPTDfast v2)

Ngày: 2026-11-18. Đây là bước nghiên cứu đối chứng thuật toán PPG công bố trên WESAD trước khi chốt danh sách feature huấn luyện mô hình.
**Quy tắc bất biến: Firmware giữ nguyên**, không nạp lại ESP32, không thay đổi schema truyền tin thiết bị.

---

## 1. Mục tiêu và Phương pháp đối chứng

Ở Bước 4A ([04-HR-ECG-REVIEW.md](04-HR-ECG-REVIEW.md)), thuật toán tìm đỉnh nhân quả thử nghiệm `bvp-causal-peaks-v1-experimental` bộc lộ điểm yếu nghiêm trọng: **độ phủ trong pha Stress chỉ đạt 16,40%** (1.595 / 9.724 cửa sổ ECG dùng được), dẫn đến nguy cơ thiên lệch chọn mẫu nếu loại bỏ dữ liệu thiếu.

Để xác định nguyên nhân (do bộ lọc/thuật toán nội bộ quá cứng nhắc hay do bản chất tín hiệu BVP cổ tay khi stress bị suy giảm/nhiễu), chúng tôi tiến hành đối chiếu trực diện trên toàn bộ **15/15 đối tượng WESAD** với một phương pháp đã công bố tiêu chuẩn:

* **Phương pháp công bố:** **MSPTDfast v2** (Multi-Scale Peak and Trough Detection).
  - Tác giả: *Peter H. Charlton et al.* (toolbox `ppg-beats`, commit `c397be7afc0d8a1601a85cd673718372e40f1f59`).
  - Nguyên lý: Biến đổi scalogram đa thang đo để tìm cực trị cục bộ của sóng mạch mà không phụ thuộc vào ngưỡng biên độ cố định (amplitude threshold).
  - Triển khai: Module nhân quả [ppg_published.py](../../ai/src/preprocessing/ppg_published.py), chạy trên cửa sổ trượt 10 giây (bước trượt 1 giây), lọc thông dải Butterworth SOS nhân quả 0,5–5,0 Hz đồng nhất.
* **Tham chiếu đối chứng:** ECG ngực tự động (WFDB XQRS 4.2.0, lọc hai chiều offline, median RR trên cùng cửa sổ 10 giây).
* **Hai biến thể khảo sát của MSPTD:**
  1. `msptd_raw`: MSPTD nguyên bản, chỉ lọc theo dải nhịp tim sinh lý 40–200 bpm.
  2. `msptd_gated`: MSPTD kèm cổng chất lượng sinh lý cơ bản (tối thiểu 3 nhịp, $CV_{\text{RR}} \le 0,35$, loại trừ khoảng nhịp dị biệt).

---

## 2. Kết quả đối chiếu trên 15 đối tượng WESAD

Script thực thi: `scripts/compare_wesad_published_ppg.py`. Kết quả đầy đủ lưu tại `ai/data/interim/wesad/hr-published-review-v1/report.json`.

### 2.1. Bảng so sánh tổng hợp (Gộp 15 đối tượng)

| Điều kiện thí nghiệm | Cửa sổ ECG dùng được | Thuật toán | Cửa sổ có HR | Độ phủ / ECG (%) | MAE (bpm) | Median AE (bpm) | P90 AE (bpm) | % lỗi $\le$ 5 bpm |
|---|---:|---|---:|---:|---:|---:|---:|---:|
| **Baseline** (nhãn 1) | 17.452 | Causal-peaks cũ | 10.962 | 62,81% | **1,57** | 0,97 | **3,46** | **94,7%** |
| | | MSPTD raw | 17.417 | **99,80%** | 3,88 | 1,45 | 9,19 | 80,6% |
| | | MSPTD gated | 14.935 | **85,58%** | 2,68 | 1,24 | 5,88 | 87,4% |
| **Amusement** (nhãn 3) | 5.409 | Causal-peaks cũ | 3.738 | 69,11% | **1,64** | 0,94 | **3,77** | **94,6%** |
| | | MSPTD raw | 5.404 | **99,91%** | 3,45 | 1,32 | 8,75 | 83,4% |
| | | MSPTD gated | 4.799 | **88,72%** | 2,69 | 1,16 | 6,62 | 87,9% |
| **Stress** (nhãn 2) | 9.724 | Causal-peaks cũ | 1.595 | **16,40%** | 3,34 | 1,61 | 5,54 | 88,3% |
| | | MSPTD raw | 9.614 | **98,87%** | 15,95 | 7,47 | 45,00 | 44,1% |
| | | MSPTD gated | 6.003 | **61,73%** | 10,56 | 4,44 | 29,85 | 53,7% |
| **Binary Task** (1, 2, 3) | 32.585 | Causal-peaks cũ | 16.295 | 50,01% | **1,76** | 1,01 | **3,71** | **94,1%** |
| | | MSPTD raw | 32.435 | **99,54%** | 7,38 | 2,08 | 22,05 | 70,2% |
| | | MSPTD gated | 25.737 | **78,98%** | 4,52 | 1,55 | 10,75 | 79,7% |

---

## 3. Phân tích sâu: So sánh Head-to-Head & Cửa sổ bất đồng

Để nhìn thấu bản chất, dữ liệu được bóc tách thành hai tập riêng biệt:

### 3.1. Cửa sổ đồng thuận (Common Windows — Cả 2 thuật toán cùng đưa ra HR)

Trên các cửa sổ mà tín hiệu BVP cổ tay đủ rõ nét để cả 2 thuật toán cùng nhận dạng được nhịp ($N = 16.294$ cửa sổ):

* **Baseline ($N = 10.961$):** Causal-peaks cũ MAE = 1,57 bpm vs MSPTD MAE = **1,64 bpm**.
* **Amusement ($N = 3.738$):** Causal-peaks cũ MAE = 1,64 bpm vs MSPTD MAE = **1,61 bpm**.
* **Stress ($N = 1.595$):** Causal-peaks cũ MAE = 3,34 bpm vs MSPTD MAE = **3,28 bpm**.

> **Kết luận 1:** Khi hình thái sóng PPG ở cổ tay còn giữ được các đỉnh mạch rõ nét, thuật toán nội bộ và thuật toán quốc tế MSPTD đạt **độ chính xác tương đương tuyệt đối** (sai lệch < 0,1 bpm giữa hai phương pháp, MAE ~1,6 bpm so với ECG ngực).

### 3.2. Cửa sổ bất đồng (Disjoint Windows — Thuật toán cũ từ chối, MSPTD đưa ra HR)

Đây là những cửa sổ làm sáng tỏ bản chất của bài toán ($N = 16.141$ cửa sổ):

* **Trong Baseline ($N = 6.456$ cửa sổ):** MSPTD đạt **Median AE = 3,63 bpm**, P90 = 21,72 bpm. Thuật toán cũ quá bảo thủ (do cổng `RR_OUTSIDE_METHOD_RANGE` khắt khe chỉ cần 1 khoảng nhịp lệch nhỏ là hủy toàn bộ cửa sổ 10s). MSPTD gated đã cứu được phần lớn các cửa sổ này, nâng độ phủ Baseline từ 62,81% lên **85,58%** với MAE rất tốt (2,68 bpm).
* **Trong Stress ($N = 8.019$ cửa sổ):** MSPTD đạt **MAE = 18,47 bpm**, Median AE = 10,31 bpm, P90 = 49,60 bpm.

### 3.3. Truy tìm nguyên nhân gốc rễ (Root Cause) trong pha Stress

Phân tích định tính trên các đoạn sóng có sai số lớn trong pha Stress cho thấy 2 hiện tượng sinh lý - vật lý chi phối:
1. **Lỗi nửa nhịp (Half-rate / Missed alternate beats):** Khi đối tượng stress, co mạch ngoại vi làm biên độ sóng xung giảm mạnh và hình thành sóng phản xạ phức tạp (*pulsus alternans* hoặc *dicrotic notch* chiếm ưu thế). Biến đổi scalogram của MSPTD bị hút về hài bậc dưới (chọn thang đo ứng với chu kỳ gấp đôi), dẫn đến ước lượng nhịp tim bằng đúng một nửa nhịp tim thực (ví dụ ECG = 88 bpm nhưng MSPTD đếm ~42 bpm).
2. **Nhiễu chuyển động (Motion Artifacts):** Trong bài test TSST (Trier Social Stress Test) của WESAD, đối tượng phải thuyết trình trước ban giám khảo và làm tính nhẩm nhanh. Gia tốc cổ tay ($\sigma_{\text{ACC}}$) vọt lên 0,3–0,7 $\text{m/s}^2$ (so với 0,07 $\text{m/s}^2$ lúc tĩnh), làm dịch chuyển cảm biến quang E4 trên da, tạo ra các đỉnh quang giả làm méo mó chu kỳ nhịp tim thực.

---

## 4. Quyết định kỹ thuật cho việc chốt Feature (Feature Decision Gate)

Dựa trên bằng chứng thực nghiệm đối chứng 15 người:

1. **Không thể giả định HR từ BVP luôn luôn hoàn hảo và đầy đủ:** Cả thuật toán heuristic lẫn thuật toán công bố quốc tế MSPTD đều chịu giới hạn vật lý khi cổ tay chuyển động và co mạch trong stress.
2. **Chiến lược Feature đa tầng (Dual-representation HR Feature):**
   * Sử dụng **MSPTD Gated** làm bộ trích xuất nhịp tim mặc định cho BVP, giúp nâng độ phủ tổng thể lên **~79%** (và đạt **~62%** ở Stress thay vì 16,4%).
   * Tạo feature nhị phân đi kèm: `hr_is_valid` (1 nếu cửa sổ đạt chuẩn sinh lý, 0 nếu bị loại do nhiễu/mất nhịp).
   * Khi `hr_is_valid == 0`: áp dụng forward-fill có giới hạn (tối đa 5–10 giây) hoặc gán giá trị nền cá nhân, đồng thời cờ `hr_is_valid = 0` báo cho mô hình biết độ tin cậy của kênh HR.
3. **Phát huy ưu thế đa cảm biến (Multimodal Fusion):**
   * Hai kênh **EDA** (điện da) và **ACC** (gia tốc) trên WESAD có **độ phủ 100% không mất mẫu**.
   * Pha Stress kích hoạt hệ thần kinh giao cảm (Sympathetic Nervous System), làm tăng rõ rệt biên độ và tần suất của các đáp ứng dẫn truyền da (SCR peaks) và mức nền (SCL).
   * Do đó, mô hình phân loại stress sẽ lấy EDA + ACC làm khung xương sống vững chắc, và kết hợp HR như một kênh củng cố khi hợp lệ, đảm bảo hệ thống không bị "mù" khi trẻ hoặc người đeo cử động tay.
4. **Firmware giữ nguyên:** Không thay đổi mã nguồn firmware ESP32. Cơ chế lọc và trích xuất feature này nằm hoàn toàn ở backend / pipeline huấn luyện AI.

---

## 5. Danh mục file và Kiểm chứng

* [ppg_published.py](../../ai/src/preprocessing/ppg_published.py): Module MSPTDfast v2 nhân quả.
* [compare_wesad_published_ppg.py](../../scripts/compare_wesad_published_ppg.py): Script đối chiếu 15 người độc lập.
* [test_ppg_published.py](../../ai/tests/test_ppg_published.py): 6 ca kiểm thử đơn vị hồi quy.
* Tổng cộng: **50/50 AI tests đạt**, không có lỗi hồi quy.
