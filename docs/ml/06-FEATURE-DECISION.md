# Bước 4C — Quyết định Chốt Feature và Xử lý Tín hiệu Đa cảm biến

Ngày: 2026-11-18. Quyết định kỹ thuật sau khi hoàn tất đối chiếu Bước 4A ([04-HR-ECG-REVIEW.md](04-HR-ECG-REVIEW.md)) và Bước 4B ([05-PPG-BENCHMARK.md](05-PPG-BENCHMARK.md)).
**Quy tắc bất biến: Firmware ESP32 giữ nguyên 100%.**

---

## 1. Bối cảnh và Thách thức cốt lõi

Từ kết quả đối chiếu trên 15 đối tượng WESAD:
1. **PPG cổ tay bị suy giảm mạnh trong pha Stress:**
   - Thuật toán heuristic ban đầu bị từ chối đến 83,6% số cửa sổ trong pha Stress.
   - Thuật toán công bố quốc tế MSPTDfast v2 (*Peter H. Charlton et al.*) khi không có cổng chất lượng thì đạt độ phủ 98,87%, nhưng gặp sai số lớn (MAE = 15,95 bpm, P90 = 45 bpm) do **lỗi nửa nhịp (half-rate)** và **nhiễu chuyển động tay (motion artifacts)** trong bài test TSST.
   - Khi áp dụng cổng chất lượng sinh lý (`msptd_gated`), độ phủ pha Stress được phục hồi lên **61,73%** (tăng gấp 3,7 lần) với sai số trung vị chỉ 4,44 bpm.
2. **EDA và ACC có độ phủ hoàn hảo 100%:**
   - EDA phản ánh trực tiếp kích thích thần kinh giao cảm (Sympathetic Nervous System) qua mức nền trương lực (SCL) và các đợt bộc phát pha (SCR peaks).
   - ACC ghi nhận động năng rung lắc, bồn chồn ở cổ tay.
3. **Thách thức:** Không thể loại bỏ các cửa sổ mất HR (gây thiên lệch mẫu), cũng không thể để mô hình tin tưởng mù quáng vào các giá trị HR bị méo do nhiễu động.

---

## 2. Quyết định Kỹ thuật đã Chốt

### Quyết định 1: Chọn thuật toán MSPTD Gated làm bộ trích xuất HR chuẩn
- **Mã nguồn:** Module [ppg_published.py](../../ai/src/preprocessing/ppg_published.py).
- **Cấu hình:** Cửa sổ trượt 10s (bước trượt 1s), lọc thông dải Butterworth SOS 0,5–5,0 Hz, scalogram đa thang đo, yêu cầu tối thiểu 3 nhịp tim, $CV_{\text{RR}} \le 0,35$, dải nhịp sinh lý 40–200 bpm.
- **Lý do:** Khắc phục được tính bảo thủ cực đoan của thuật toán cũ, nâng độ phủ Baseline từ 62,81% lên 85,58% và Stress từ 16,40% lên 61,73% mà vẫn giữ được tính nhất quán sinh lý.

### Quyết định 2: Chiến lược Feature HR Đa tầng (Dual-Representation)
Không ép HR thành một kênh liên tục đơn lẻ không tì vết. Thay vào đó, biểu diễn HR qua 2 khía cạnh:
1. **Giá trị nhịp tim ước lượng (`hr_mean`, `hr_std`, `hr_max`, `hr_min`):** Được tính trên chuỗi HR sau khi áp dụng nội suy forward-fill ngắn hạn (tối đa 10 giây). Nếu cả cửa sổ 60s không có HR hợp lệ, gán bằng mức nhịp tim trung vị của đối tượng lúc nghỉ (baseline median HR).
2. **Đặc trưng độ tin cậy (`hr_valid_ratio`, `hr_is_valid`):**
   - `hr_valid_ratio`: Tỷ lệ phần trăm các giây có nhịp tim hợp lệ trong cửa sổ 60s.
   - `hr_is_valid`: Cờ nhị phân (1 nếu `hr_valid_ratio >= 0.30`, 0 nếu nhỏ hơn).
   - **Tác dụng:** Cờ này báo cho mô hình học máy biết trọng số tin cậy. Khi `hr_is_valid = 0` (đối tượng đang cử động tay mạnh làm mất nhịp PPG), mô hình tự động chuyển dịch trọng số sang EDA và ACC mà không bị "đoán mò" theo số HR sai.

### Quyết định 3: Khóa danh sách 36 Đặc trưng Đa cảm biến (Feature Set Freeze)
Khóa tập 36 đặc trưng trích xuất trên cửa sổ 60s (bước trượt 10s):
* **EDA (14):** `eda_mean`, `eda_std`, `eda_min`, `eda_max`, `eda_ptp`, `eda_slope`, `eda_tonic_mean`, `eda_tonic_std`, `eda_phasic_mean`, `eda_phasic_max`, `eda_phasic_std`, `eda_phasic_auc`, `eda_scr_count`, `eda_scr_amp_mean`.
* **ACC (13):** `acc_norm_mean`, `acc_norm_std`, `acc_norm_min`, `acc_norm_max`, `acc_norm_ptp`, `acc_norm_energy`, `acc_motion_intensity`, `acc_x_mean`, `acc_x_std`, `acc_y_mean`, `acc_y_std`, `acc_z_mean`, `acc_z_std`.
* **HR & Validity (9):** `hr_valid_count`, `hr_valid_ratio`, `hr_is_valid`, `hr_mean`, `hr_std`, `hr_min`, `hr_max`, `hr_ptp`, `hr_slope`.

### Quyết định 4: Cơ chế Đánh giá mô hình chuẩn mực (Evaluation Protocol)
* **Leave-One-Subject-Out (LOSO) 15 fold:** Đánh giá lần lượt trên 15 đối tượng, mỗi fold lấy 1 người làm test và 14 người làm train.
* **Chuẩn hóa độc lập:** Mọi biến đổi `StandardScaler` chỉ được fit trên tập train của từng fold, cấm fit trên test subject.

### Quyết định 5: Giữ nguyên Firmware
* Toàn bộ mã nguồn C++ trên ESP32 (`ai/edge_firmware`) giữ nguyên trạng thái `0.3.23-tracker` / `0.3.26`.
* Thiết bị tiếp tục gửi telemetry và raw streams chuẩn; việc trích xuất đặc trưng cửa sổ 60s diễn ra trên tầng phân tích / backend.

---

## 3. Bằng chứng Thực nghiệm Nghiệm thu Quyết định

1. **Ablation Study (LOSO 15 fold):**
   - Mô hình chỉ dùng EDA + ACC: Accuracy 76,94%, Stress F1 62,97%.
   - Mô hình đầy đủ (bổ sung HR + `hr_is_valid`): Accuracy tăng vọt lên **84,08%** (+7,14%), Stress F1 tăng lên **73,89%** (+10,92%), Recall đạt **75,77%**.
2. **Mô hình Tuyến tính Logistic Regression:**
   - Đạt Accuracy **89,74%**, Macro F1 **87,95%**, Stress F1 **83,30%**.
   - Chứng minh các đặc trưng được chọn có khả năng phân tách tuyến tính rất mạnh và có thể tối ưu cho edge inference cực nhẹ sau này.
3. **Notebook trực quan:**
   - Đã kiểm chứng toàn bộ biểu đồ, dạng sóng và phân tích tương quan tại [ai/notebooks/03-wesad-ppg-benchmark.ipynb](../../ai/notebooks/03-wesad-ppg-benchmark.ipynb), thực thi thành công 0 lỗi.
4. **Kiểm thử tự động:**
   - 54 tests AI đều đạt 100%.
