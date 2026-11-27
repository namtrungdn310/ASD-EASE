# Bước 5 — Huấn luyện và Đánh giá Mô hình Baseline nhận diện Stress

Ngày: 2026-11-18. Đây là kết quả huấn luyện mô hình học máy đầu tiên trên tập dữ liệu chuẩn hóa WESAD (15 đối tượng).
**Quy tắc bất biến: Firmware giữ nguyên**, không nạp lại ESP32, toàn bộ xử lý diễn ra trên pipeline AI.

---

## 1. Phương pháp luận và Thiết kế Thử nghiệm

Để tránh rò rỉ dữ liệu (data leakage) và đảm bảo tính tổng quát hóa trên người dùng thực tế:

1. **Giao thức kiểm định:** **Leave-One-Subject-Out (LOSO) Cross-Validation** trên toàn bộ **15 đối tượng** (`S2`–`S17`, trừ `S12` hỏng cảm biến từ nguồn).
   - Mỗi lượt lặp (fold), 1 đối tượng được giữ lại làm tập kiểm thử độc lập (unseen test subject); 14 đối tượng còn lại dùng làm tập huấn luyện.
   - Phép chuẩn hóa `StandardScaler` được tính toán và fit **chỉ trên tập huấn luyện của fold đó**, sau đó biến đổi sang tập kiểm thử. Không fit trên toàn bộ dữ liệu.
2. **Cửa sổ phân loại:** Cửa sổ trượt **60 giây** (bước trượt **10 giây**), hoàn toàn nhân quả, lùi về quá khứ.
3. **Quy tắc nhãn tinh khiết:** Chỉ giữ các cửa sổ nằm trọn vẹn trong một điều kiện thí nghiệm:
   - Baseline (nhãn 1) và Amusement (nhãn 3) $\rightarrow$ `0` (Non-stress).
   - Stress (nhãn 2) $\rightarrow$ `1` (Stress).
   - Tổng cộng sinh ra **3.040 cửa sổ** (904 Stress ~29,74%, 2.136 Non-stress ~70,26%).
4. **Tập 36 đặc trưng đa cảm biến:**
   - **EDA (14 đặc trưng):** `eda_mean`, `eda_std`, `eda_min`, `eda_max`, `eda_ptp`, `eda_slope`, `eda_tonic_mean`, `eda_tonic_std`, `eda_phasic_mean`, `eda_phasic_max`, `eda_phasic_std`, `eda_phasic_auc`, `eda_scr_count`, `eda_scr_amp_mean`.
   - **ACC (13 đặc trưng):** `acc_norm_mean`, `acc_norm_std`, `acc_norm_min`, `acc_norm_max`, `acc_norm_ptp`, `acc_norm_energy`, `acc_motion_intensity`, `acc_x/y/z_mean`, `acc_x/y/z_std`.
   - **HR & Validity (9 đặc trưng):** `hr_valid_count`, `hr_valid_ratio`, `hr_is_valid`, `hr_mean`, `hr_std`, `hr_min`, `hr_max`, `hr_ptp`, `hr_slope` (từ thuật toán MSPTD Gated kết hợp nội suy ngắn hạn và cờ độ tin cậy).

---

## 2. Kết quả Thử nghiệm Cắt bỏ (Ablation Study)

Đánh giá tác động độc lập và cộng hưởng của từng kênh cảm biến bằng Random Forest (100 cây, cân bằng trọng số lớp):

| Cấu hình cảm biến | Số đặc trưng | Accuracy (%) | F1-Score Macro (%) | Stress F1 (%) | Stress Recall (%) | Stress Precision (%) |
|---|---:|---:|---:|---:|---:|---:|
| **1. Chỉ EDA** (EDA only) | 14 | 73,62% | 69,25% | 57,66% | 60,40% | 55,15% |
| **2. Chỉ ACC** (ACC only) | 13 | 81,38% | 77,18% | 67,40% | 64,71% | 70,31% |
| **3. EDA + ACC** (không dùng HR) | 27 | 76,94% | 73,11% | 62,97% | 65,93% | 60,26% |
| **4. Full Multimodal** (EDA + ACC + HR) | **36** | **84,08%** | **81,22%** | **73,89%** | **75,77%** | **72,11%** |

> **Bằng chứng thực nghiệm cốt lõi:**
> Khi bổ sung kênh nhịp tim HR (dùng MSPTD Gated kèm cờ `hr_is_valid`) vào bộ đôi EDA + ACC:
> - Accuracy tăng từ 76,94% lên **84,08%** (+7,14% tuyệt đối).
> - F1 Macro tăng từ 73,11% lên **81,22%** (+8,11% tuyệt đối).
> - **F1-Score phân loại Stress nhảy vọt từ 62,97% lên 73,89%** (+10,92% tuyệt đối), độ nhạy (Recall) đạt **75,77%**.
> Điều này khẳng định kênh HR mang giá trị thông tin sinh lý thực sự và việc cứu được các cửa sổ HR bằng MSPTD Gated ở Bước 4B đóng vai trò quyết định.

---

## 3. So sánh 10 Biến thể Mô hình và Thông lượng Suy luận (Model Benchmark & PPS)

Trên cùng tập đặc trưng đầy đủ 36 chiều và quy trình kiểm định LOSO 15 fold:

| Hạng | Biến thể Mô hình | Thuộc Họ Thuật toán | Accuracy (%) | Macro F1 (%) | Stress F1 (%) | Độ trễ CPU (ms/mẫu) | Thông lượng (PPS) |
|:---:|---|---|---:|---:|---:|---:|---:|
| **1** | **Logistic Regression (C=10.0, Tuned)** | **Linear** | **90,69%** | **88,99%** | **84,66%** | **0,070 ms** | **14.285 PPS** ⚡ |
| **2** | **Logistic Regression (C=1.0)** | Linear | 89,74% | 87,95% | 83,30% | 0,076 ms | 13.108 PPS |
| **3** | **SVM (Linear, C=1.0)** | Kernel / Linear | 89,80% | 87,91% | 83,12% | 0,207 ms | 4.824 PPS |
| **4** | **k-NN (k=7, distance weights)** | Distance-based | 89,21% | 86,54% | 80,55% | 1,023 ms | 977 PPS |
| **5** | **MLP Neural Net (64x32)** | Neural Network | 88,45% | 86,15% | 80,49% | 0,080 ms | 12.484 PPS |
| **6** | **SVM (RBF, C=10.0, gamma='scale')** | Kernel / Non-linear | 88,19% | 85,72% | 79,77% | 0,235 ms | 4.253 PPS |
| **7** | **Random Forest (Tuned: 200 trees, depth=15)** | Ensemble | 84,01% | 81,21% | 73,95% | 33,563 ms | 30 PPS |
| **8** | **Random Forest (Default: 100 trees, depth=10)**| Ensemble | 84,08% | 81,22% | 73,89% | 3,348 ms | 299 PPS |
| **9** | **HistGradientBoosting (Tuned)** | Boosting | 80,92% | 78,21% | 70,53% | 3,034 ms | 330 PPS |
| **10**| **HistGradientBoosting (Default)** | Boosting | 80,72% | 78,00% | 70,25% | 1,506 ms | 664 PPS |

### Nhận định về hiệu năng vượt trội của Tuned Logistic Regression:
Mô hình tuyến tính điều chuẩn (**Logistic Regression $C=10.0$**) đạt kết quả toàn diện ấn tượng: **Accuracy 90,69%**, **Macro F1 88,99%** và **Stress F1 84,66%**.
Lý do vật lý và sinh lý:
1. Các đặc trưng kích thích giao cảm (độ dẫn da SCL/SCR, nhịp tim trung bình, năng lượng cử động) có quan hệ đơn điệu tăng dần khá rõ với trạng thái Stress.
2. Mô hình tuyến tính không bị overfit cục bộ vào các ngưỡng phi tuyến tính của từng cá nhân như cây quyết định, nên có khả năng tổng quát hóa tốt hơn khi test trên người hoàn toàn mới (LOSO 15-fold).
3. **Ý nghĩa triển khai thực tế:** Logistic Regression chỉ gồm 36 hệ số nhân trọng số (weights) và 1 bias, tính toán bằng một phép nhân vô hướng $\vec{w} \cdot \vec{x} + b$. Tốc độ đạt tới **~14.285 PPS** (nhanh gấp gần 500 lần so với Random Forest), chiếm chưa đầy **432 bytes RAM/Flash**, là ứng viên hoàn hảo cho vi điều khiển ESP32-S3 theo kiến trúc ADR-004.

---

## 4. Kiểm chứng Độc lập Cảm biến và Xếp hạng Đa biến Thực tế

### 4.1. Kiểm chứng loại bỏ cờ mất tín hiệu (`hr_valid_*` Ablation)
Để chứng minh mô hình không "học vẹt" theo hiện tượng rơi cảm biến PPG, ta tiến hành loại bỏ toàn bộ 3 đặc trưng cờ mất kết nối (`hr_valid_count`, `hr_valid_ratio`, `hr_is_valid`):
- Điểm Stress F1 trên mô hình Logistic Regression chỉ giảm nhẹ **-2.37%** (từ 84.66% xuống 82.29%).
- Trên Linear SVM chỉ giảm nhẹ **-0.95%** (từ 83.12% xuống 82.16%).
- Chứng minh mô hình học trực tiếp từ động học biến thiên sinh lý thật của nhịp tim, độ dẫn da và gia tốc.

### 4.2. Tầm quan trọng mô hình đa biến thực tế (Permutation Feature Importance)
Khác với tương quan đơn biến Pearson $|r|$, kỹ thuật xáo trộn ngẫu nhiên từng đặc trưng trên tập kiểm thử LOSO 15 người ghi nhận mức độ sụt giảm Macro F1 ($\Delta F_1$):

| Hạng | Đặc trưng | Cảm biến | Mức sụt giảm Macro F1 ($\Delta F_1$) | Pearson \|r\| đơn biến | Ý nghĩa thực tế trong mô hình |
|:---:|---|:---:|---:|---:|---|
| **1** | `eda_phasic_auc` | EDA | **+12,93%** | 0,401 | Năng lượng xung toát mồ hôi dâng cao khi stress |
| **2** | `eda_phasic_mean` | EDA | **+12,55%** | 0,401 | Cường độ trung bình pha phản xạ da |
| **3** | `acc_norm_std` | ACC | **+12,28%** | 0,444 | Biên độ biến thiên gia tốc rung lắc cổ tay |
| **4** | `acc_norm_energy` | ACC | **+11,26%** | 0,221 | Ngữ cảnh vận động (phân biệt stress tĩnh vs vận động) |
| **5** | `eda_min` | EDA | **+8,59%** | 0,359 | Mức nền dẫn điện da tối thiểu |
| **6** | `eda_scr_count` | EDA | **+8,11%** | 0,571 | Tần số xuất hiện xung điện da kích thích giao cảm |
| **7** | `eda_max` | EDA | **+7,95%** | 0,382 | Mức đỉnh xung điện da |
| **8** | `acc_x_std` | ACC | **+4,36%** | 0,027 | Dao động ngang hỗ trợ triệt tiêu nhiễu cử động |
| **9** | `acc_norm_mean` | ACC | **+4,14%** | 0,127 | Mức gia tốc trọng trường nền |
| **10**| `eda_std` | EDA | **+3,82%** | 0,359 | Độ biến thiên điện da toàn phần |
| **11**| `acc_z_std` | ACC | **+3,65%** | 0,001 | Hướng rung lắc trục dọc |
| **12**| `hr_max` | HR | **+2,49%** | 0,632 | Nhịp tim đỉnh điểm trong cửa sổ 60s |

> **Kết luận phương pháp luận:** Nhiều đặc trưng có Pearson $|r|$ thấp (`acc_norm_energy` $0.22$, `acc_x_std` $0.03$, `acc_z_std` $0.001$) thực tế lại nằm trong Top đầu về Permutation Importance (+4% đến +11%) vì chúng cung cấp ngữ cảnh đa biến triệt tiêu nhiễu. Toàn bộ 36 đặc trưng đều được bảo lưu để đảm bảo khả năng khái quát hóa tối đa.

---

## 5. Xuất mô hình Sản xuất và Triển khai Bare-Metal TinyML C/C++ (Production Export)

Mô hình quán quân đã được tối ưu hóa cực hạn và xuất hoàn tất tại **Notebook 06**:
* **Kỹ thuật Parameter Folding:** Gộp toàn bộ phép chuẩn hóa `StandardScaler` vào trọng số ($w' = w/\sigma$) và bias ($b' = b - \sum w\mu/\sigma$) từ khâu tiền xử lý offline.
* **Loại bỏ phụ thuộc runtime trung gian:** Không sử dụng ONNX Runtime hay TFLite Micro, triển khai thẳng C++ thuần bare-metal.
* **Artifact Python:** `ai/models/production/wesad_logistic_regression_v1.joblib` và `.json` (phục vụ Python Backend và Telemetry Simulator).
* **C++ Header nhúng ESP32-S3:** [model_generated.h](../../ai/edge_firmware/include/model_generated.h):
  - **Dung lượng Flash:** Chỉ **148 bytes** trong phân vùng `.rodata`.
  - **Dung lượng RAM:** **0 byte dynamic RAM** (hoàn toàn zero heap, không `malloc`/`new`).
  - **Phép chia số thực runtime:** **0 phép chia** (giảm 100% so với bản chưa tối ưu).
  - **Nhánh quyết định nhanh (`edge_predict_stress_fast`):** Khử hàm `expf(-z)`, so sánh trực tiếp $z \ge 0.0\text{f}$ trong **1 chu kỳ so sánh FPU** cho điều khiển còi/rung tức thì (< 1 µs).
  - **Hàm xác suất (`edge_predict_stress_probability`):** Chỉ gọi khi cần log hoặc hiển thị telemetry MQTT.
* **Kiểm chứng đối chuẩn số học (Numerical Parity):** Sai số tuyệt đối tối đa giữa C++ `float32` (folded) và Python `float64` là $2.22 \times 10^{-5}$, tỷ lệ khớp nhãn quyết định **100.00% trên cả 3.040 cửa sổ WESAD**.

---

## 6. Giới hạn và Điểm chặn cần lưu ý

1. **Khác biệt vật lý GSR thiết bị vs E4 WESAD:**
   - WESAD đo bằng Empatica E4, đơn vị dẫn truyền da là µS ($10^{-6}$ Siemens).
   - Thiết bị ASD-EASE hiện tại đo bằng Grove GSR Sensor qua ADC 12-bit của ESP32 (đơn vị raw count 0–4095).
   - Mô hình hiện tại đã chứng minh hiệu quả phân loại xuất sắc trên WESAD. Tuy nhiên, trước khi nạp chạy trên dữ liệu của board thật, cần thực hiện một trong hai giải pháp:
     + Hiệu chuẩn hàm truyền đạt điện áp ADC $\rightarrow$ µS cho cảm biến Grove.
     + Hoặc chuẩn hóa z-score / baseline cá nhân trên chuỗi ADC trước khi đưa vào mô hình.
2. **Trạng thái Firmware:**
   - Firmware ESP32 giữ nguyên toàn bộ, không có bất kỳ thay đổi nào.

---

## 7. Danh mục file và Kiểm chứng

* [stress_features.py](../../ai/src/feature_extraction/stress_features.py): Module trích xuất 36 đặc trưng đa cảm biến.
* [test_feature_extraction.py](../../ai/tests/test_feature_extraction.py): Kiểm thử đơn vị cho trích xuất đặc trưng.
* [extract_wesad_features.py](../../scripts/extract_wesad_features.py): Script trích xuất dataset 3.040 cửa sổ trên 15 đối tượng.
* [train_wesad_baseline.py](../../scripts/train_wesad_baseline.py): Script huấn luyện và cross-validation LOSO 15 fold.
* Tập dữ liệu đã xuất: `ai/data/processed/wesad/features-v1/dataset.csv`.
* Báo cáo chi tiết: `ai/models/wesad-baseline-v1/report.json`.
* Tổng số kiểm thử: **54/54 tests AI đều đạt (PASSED)**.
