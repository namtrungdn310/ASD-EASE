# Chuỗi Notebook Nghiên cứu WESAD

Chuỗi notebook trực quan hóa toàn bộ quy trình từ chuẩn hóa dữ liệu, đối chiếu thuật toán, trích xuất đặc trưng đến huấn luyện mô hình phân loại Stress.

Tất cả notebook đã được chạy sẵn output (kèm bảng số liệu và biểu đồ trực quan), bạn có thể mở ra xem ngay lập tức mà không cần bấm chạy lại.

## Danh mục theo thứ tự:

1. [01-wesad-data-preparation.ipynb](01-wesad-data-preparation.ipynb): **Chuẩn hóa & Khám phá Dữ liệu WESAD**
   - Bảng quy chuẩn hóa thông số cảm biến (ACC, BVP, EDA) và tổng quan 15 đối tượng (`S2`–`S17`).
   - Phân bố thời lượng 8 mã gốc WESAD và chuẩn hóa thành bài toán nhị phân 2 lớp (Bình thường vs Stress).

2. [02-wesad-hr-ecg-review.ipynb](02-wesad-hr-ecg-review.ipynb): **Đánh giá Thuật toán Nhịp tim Cổ tay (HR vs ECG)**
   - Đối chiếu nhịp tim BVP cổ tay với ECG ngực làm thước đo chuẩn.
   - Phát hiện lỗi mất **83,6% dữ liệu ở pha Stress** của thuật toán cũ và soi dạng sóng co mạch.

3. [03-wesad-ppg-benchmark.ipynb](03-wesad-ppg-benchmark.ipynb): **Đối chiếu Thuật toán PPG Công bố (MSPTD)**
   - Đánh giá thuật toán MSPTDfast v2 (*Peter H. Charlton et al.*) để cứu dữ liệu stress.
   - Tăng độ phủ nhịp tim pha Stress từ 16,40% lên **61,73%** (tăng gấp 3,7 lần), MAE ổn định ~1,6–3,3 bpm.

4. [04-wesad-feature-extraction.ipynb](04-wesad-feature-extraction.ipynb): **Trích xuất & Phân tích 36 Đặc trưng Stress**
   - Khám phá 36 đặc trưng sinh lý (14 EDA, 13 ACC, 9 HR) trích xuất từ 3.040 cửa sổ 60s.
   - So sánh phân bố đặc trưng và xếp hạng Top 10 đặc trưng tương quan mạnh nhất với nhãn Stress.

5. [05-wesad-model-training.ipynb](05-wesad-model-training.ipynb): **Huấn luyện & Đánh giá Mô hình Stress (LOSO)**
   - Đánh giá kiểm thử chéo 15 người (Leave-One-Subject-Out) chống rò rỉ dữ liệu (data leakage).
   - So sánh hiệu năng mô hình (Logistic Regression đạt F1 Stress **83,30%**), phân tích đóng góp của kênh HR (Ablation Study) và ma trận nhầm lẫn.

---

> **Mẹo sử dụng:** Mở notebook bằng kernel `.venv`. Nếu muốn chạy lại toàn bộ từ đầu, chỉ cần chạy script `.\.venv\Scripts\python.exe scripts/build_notebooks.py`.
