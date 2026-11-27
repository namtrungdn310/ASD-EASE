# Bước 1 — Cấu trúc dữ liệu đầu vào ML

Ngày: 2026-11-16. Phiên bản đặc tả nội bộ: `ml-input-v1`.

Cập nhật triển khai bước 3: 2026-11-17; các quyết định HR/feature cuối vẫn chưa khóa.

Đã đối chiếu code trên nền commit `8a81f88`. Đây là thiết kế dữ liệu cho xử lý/huấn luyện, **không phải schema MQTT/API mới**. [Bước 3](03-WESAD-PREPARATION.md) đã triển khai bộ chuyển đổi WESAD; HR còn thử nghiệm, chưa chốt cho train. [Kiểm kê bước 2](02-DATA-AUDIT.md) xác nhận raw thiết bị hiện chưa ghi đầy đủ tự động.

## 1. Mục tiêu đã chốt

- Trước mắt nghiên cứu **stress/không stress trên WESAD**, theo quyết định ngày 2026-11-16. Đây là nhãn điều kiện thí nghiệm, không phải mức nghiêm trọng y khoa.
- Đầu vào phiên bản đầu có **5 biến gốc**: HR, điện da và gia tốc ba trục.
- Một đoạn tín hiệu sẽ được chuyển thành các feature. Chưa chốt độ dài đoạn, bước trượt, công thức hoặc số lượng feature cuối cùng.
- Không diễn giải nhãn thành chẩn đoán ASD, hành vi nguy hiểm hoặc mức nghiêm trọng y khoa.

WESAD là dataset làm việc hiện tại; EmpathicSchool tạm chờ cấp quyền. Không tự ghép nhãn hai bộ thành một thang mức độ hoặc đổi baseline/stress/amusement thành nhẹ/vừa/nặng.

## 2. Năm biến gốc

| Vai trò | Tên kênh sau chuyển đổi | Đơn vị | Nguồn ASD-EASE | Nguồn dataset dự kiến |
|---|---|---|---|---|
| Nhịp tim | `hr_bpm` | bpm | HR được firmware chấp nhận; trường telemetry `hr_bpm` | Với WESAD: tính từ BVP cổ tay bằng phương pháp có phiên bản; chưa coi HR là kênh có sẵn trong dữ liệu đồng bộ |
| Điện da | `gsr_adc` hoặc `eda_us` | ADC count hoặc µS, phân biệt bắt buộc | `gsr.raw` là ADC; raw batch dùng `gsr.adc` | EDA đo bằng µS theo tài liệu E4, cần kiểm tra file |
| Gia tốc X | `acc_x_ms2` | m/s² | Telemetry `movement.acceleration.x`; raw batch `imu.ax` theo đặc tả là g | ACC X sau xác minh và đổi đơn vị |
| Gia tốc Y | `acc_y_ms2` | m/s² | Tương tự với Y | ACC Y sau xác minh và đổi đơn vị |
| Gia tốc Z | `acc_z_ms2` | m/s² | Tương tự với Z | ACC Z sau xác minh và đổi đơn vị |

`gsr_adc` và `eda_us` là hai cách biểu diễn của nhóm điện da, **không phải hai cột có thể thay thế trực tiếp**. Mỗi luồng giữ đúng tên và đơn vị thực; việc dùng chung cho một model phải qua bước chứng minh tương thích ở mục 3.

Thêm biến dẫn xuất `acc_norm_ms2 = sqrt(acc_x_ms2² + acc_y_ms2² + acc_z_ms2²)` trên cả hai nguồn. Đây là độ lớn gia tốc có trọng lực, không phải tổng ba trục hoặc cảm biến thứ sáu độc lập. So sánh cấu hình 5 biến gốc với cấu hình thêm độ lớn trên validation theo người; chưa mặc định thêm biến sẽ tốt hơn. Số feature thống kê theo cửa sổ có thể lớn hơn sáu.

Các giá trị phải là số hữu hạn hoặc giá trị thiếu. Không nhận chuỗi giả số, bool, NaN/Infinity trong file xuất JSON. Không thay giá trị lỗi bằng 0 hoặc kẹp về khoảng đẹp để đủ đầu vào.

## 3. Điểm chặn về GSR

Code hiện tại đặt `GSR_CONDUCTANCE_CALIBRATED = false`. Hiệu chuẩn điện áp ADC không đồng nghĩa đã hiệu chuẩn độ dẫn da. Không dùng tên biến `conductance_uS` trong driver làm bằng chứng giá trị đã đúng µS.

Quyết định cho bước 1:

1. Thiết bị giữ `gsr_adc`, đơn vị ADC count, độ phân giải 12 bit; không đổi nhãn thành µS.
2. Dataset giữ `eda_us` nếu tài liệu/file xác nhận đơn vị µS.
3. Chưa có phép biến đổi điện da được chấp thuận để đưa hai nguồn vào cùng một model.
4. Không coi chia ADC cho 4095, min-max hoặc z-score là đã giải quyết khác biệt vật lý giữa hai đầu đo.
5. Khi thẩm định sẽ chọn một hướng: hiệu chuẩn phép đổi độ dẫn; hoặc đánh giá đặc trưng tương đối so với nền theo cùng quy trình trên hai nguồn. Cả hai đều cần kiểm chứng, không bảo đảm tương đương từ tên gọi.

Nếu dùng mức nền cá nhân, phải có đoạn nền trước thời điểm dự đoán và quy tắc khả dụng khi chạy thật. Không dùng cả phiên hoặc tương lai của người test để tính nền. Tham số học từ dữ liệu chỉ được fit trên train.

**Có thể train thử trên dataset, nhưng chưa được gọi model đó là sẵn sàng áp dụng với GSR của thiết bị.**

## 4. Tín hiệu cần giữ nhưng chưa là đầu vào model đầu tiên

| Tín hiệu | Cách lưu và sử dụng |
|---|---|
| RED/IR từ MAX30102 | Giữ từng cặp mẫu thô, thứ tự và thời gian; dùng đối chiếu bộ tính HR/chất lượng. Không coi là BVP E4 cùng thang đo |
| BVP từ dataset | Giữ nguyên tín hiệu và phương pháp xử lý của nguồn; không tự tạo RED/IR từ một kênh BVP |
| Gx/Gy/Gz | Vẫn hiển thị/lưu; chuẩn hóa cách ghi đơn vị °/s. Chưa đưa vào model đầu vì hai dataset đang xét không có gyro |
| Nhiệt độ chip | Chỉ chẩn đoán phần cứng, không thay nhiệt độ da |
| Nhiệt độ da/video trong dataset | Không đưa vào model đầu; không dùng kết quả của model có những kênh này để đại diện thiết bị hiện tại |
| IBI/RR | Nếu nguồn có thì giữ để nghiên cứu; chưa đưa HRV/PRV vào danh sách feature khi chưa chứng minh độ tin cậy phát hiện nhịp |

HR xuất từ thiết bị hoặc dataset là **ước lượng**, không mặc định là HR tham chiếu đã kiểm chứng. Ghi rõ thuật toán/phiên bản. Không ép hai bộ tính HR khác nhau thành cùng một nguồn mà không ghi chú.

## 5. Metadata bắt buộc

Metadata nằm cạnh tín hiệu, không đưa vào danh sách feature dự đoán.

| Trường | Ý nghĩa/quy tắc |
|---|---|
| `dataset_id`, `dataset_version` | Nguồn và phiên bản dữ liệu; phân biệt bản tải về với phiên tự thu |
| `subject_id` | ID giả danh của người, dùng chia tập; khóa nhóm gồm cả `dataset_id` |
| `recording_id` | ID duy nhất của một đoạn ghi có mốc thời gian liên tục; không nối qua reboot/reset đồng hồ |
| `session_id`, `boot_id`, `device_id` | Giữ nếu nguồn có; nếu thiếu ghi null, không bịa định danh thật |
| `data_origin` | Giữ `DEVICE`/`SYNTHETIC` nếu nguồn tự thu có khai báo; nguồn bên ngoài chưa xác minh không tự gán `DEVICE` |
| `time_origin`, `timestamp_kind` | Mốc gốc; thời gian đo, thời gian xuất gói hay tái dựng từ lịch lấy mẫu |
| `sample_rate_nominal_hz`, `sample_rate_measured_hz` | Ghi theo từng kênh; chưa đo thì measured=null |
| `unit`, `processing_stage`, `axis_convention` | Đơn vị, mức xử lý, hệ trục/biến đổi đã áp dụng |
| `firmware_version`, `hr_method`, `preprocessing_version` | Phiên bản nếu biết; unknown/null nếu chưa xác minh |
| `sensor_site` | Vị trí thực tế: PPG cổ tay, điện cực GSR ngón tay... Không mặc định vị trí dataset giống thiết bị |
| `source_file`, `source_sha256` | Đường dẫn tương đối trong bộ dữ liệu và hash file gốc |

Không đổi enum backend để thêm tên dataset. Các trường này thuộc dữ liệu ML nội bộ. Không chứa tên thật, email, mật khẩu Wi-Fi, token hoặc đường dẫn cá nhân tuyệt đối.

## 6. Chất lượng và giá trị thiếu

Giữ riêng `quality_score`, `quality_reason`, `quality_method`, `quality_window_ms` và `sample_count` khi nguồn thực sự cung cấp. Nếu không có thì null; không giả điểm 100% cho dataset bên ngoài. Điểm của các phương pháp khác nhau không mặc định so sánh trực tiếp được.

- Firmware hiện gửi `signal_quality.method`, `window_ms=8000` và chất lượng cho HR/GSR/acceleration/rotation.
- `sample_count` là số mẫu thu trong cửa sổ chất lượng, không phải số mẫu HR độc lập hoặc số bản ghi huấn luyện.
- Chất lượng kỹ thuật không phải xác suất stress hoặc xác suất HR đúng.
- Bản đầu dùng chất lượng để kiểm tra/lọc/ghi báo cáo, chưa dùng điểm chất lượng hay lý do lỗi làm feature dự đoán stress.
- Không tự đặt ngưỡng loại dữ liệu ở bước 1. Ghi rõ ngưỡng khi có phân tích; loại vì lỗi đo khác với loại vì không hợp kỳ vọng nhãn.
- HR mất hợp lệ phải giữ thiếu; không dùng đường nét đứt hoặc giá trị giữ/nội suy trên frontend làm HR mới.
- HR gửi nhiều lần từ cùng một kết quả đo không phải nhiều lần đo độc lập. Nếu thiếu timestamp của lần tính HR, phải ghi giới hạn thời gian; không suy từ số gói rằng HR được tính mới mỗi giây.

Đoạn thiếu kênh cần thiết không được âm thầm đưa vào model đủ 5 biến. Quy tắc bỏ đoạn, nội suy ngắn hoặc model dự phòng chỉ được bổ sung khi đánh giá riêng; chưa chốt ở bước này.

## 7. Nhịp lấy mẫu, thời gian và đơn vị

Đã đọc `board_config.h`: PPG chip 200 Hz, gộp 4 → đầu ra danh định 50 Hz; IMU 50 Hz; GSR 20 Hz; xuất telemetry mục tiêu 1.000 ms/lần. Đây là **cấu hình**, không phải số đo thực nghiệm trong bước này.

- Không gom mọi luồng thành 1 Hz chỉ vì Dashboard nhận một gói/giây.
- Không ghép dòng thứ n của PPG/EDA/ACC: chúng có tần số khác nhau. Ghép theo thời gian và đoạn ghi.
- Quy ước ML dùng `time_ms` tương đối từ cùng mốc đầu `recording_id`, không âm. Cho phép phần thập phân để giữ độ phân giải nguồn, ví dụ bước 15,625 ms ở 64 Hz.
- Giữ timestamp/mốc UTC gốc trong metadata nếu có; không so mốc boot ESP trực tiếp với UTC của dataset.
- Khoảng thời gian dùng `[start_ms, end_ms)`: gồm đầu, không gồm cuối.
- Thời gian raw chỉ được tái dựng từ sample rate khi định dạng và tính liên tục đã được xác nhận. Giữ gap; không dồn các đoạn mất thành tín hiệu liên tục.
- Gia tốc raw ghi bằng g phải nhân `9.80665` để ra m/s². WESAD `.pkl` đã được bước 2 đối chiếu với E4 raw đủ 15 người: ACC còn ở 1/64 g, cần `/64 * 9.80665`. Không áp dụng hệ số này cho telemetry thiết bị vốn đã là m/s² hoặc dữ liệu đã chuẩn hóa.
- Giữ trọng lực trong các kênh gia tốc gốc. Chỉ tách trọng lực khi có phương pháp riêng được ghi phiên bản.
- Driver hiện đã biến đổi dấu Y/Z; không đảo lại chỉ vì muốn đường biểu đồ giống nhau. Trục tương ứng về tên chưa bảo đảm cùng hướng đeo giữa các nguồn.

Telemetry là snapshot đã qua kiểm tra/lọc, khác sóng raw. Đặc tả raw 1.0 của dự án dùng gia tốc g; telemetry 1.1/1.2 dùng m/s². Bộ chuyển đổi phải khai báo nguồn và đơn vị, không đoán từ tên `ax`.

## 8. Nhãn đặt riêng khỏi tín hiệu

Mỗi bản ghi nhãn có:

| Trường | Nội dung |
|---|---|
| `recording_id` | Đoạn ghi được gán nhãn |
| `start_ms`, `end_ms` | Khoảng nhãn trong cùng hệ thời gian với tín hiệu |
| `source_label_code`, `source_label_name` | Giữ mã và tên nguyên gốc |
| `label_method`, `label_resolution_ms` | Tự báo cáo/điều kiện thí nghiệm/chuyên gia; độ phân giải nếu biết |
| `target_label` | Nhãn sau ánh xạ, null nếu chưa chốt hoặc chưa rõ |
| `label_mapping_version` | Phiên bản ánh xạ, null trước khi xác nhận |

Với WESAD, dùng chính sách ban đầu `wesad-binary-v1`: baseline (1) và amusement (3) → `NON_STRESS` (0); stress (2) → `STRESS` (1). Loại đoạn chưa xác định/chuyển tiếp, meditation và mã bỏ qua khỏi bài toán đầu tiên. Giữ nguyên mã nguồn để kiểm tra; không lấy trung bình mã nhãn. Đối chiếu README và phân bố mã file thực trước khi tạo cửa sổ. Có thể báo riêng baseline-vs-stress như phân tích phụ, không trộn hai chính sách trong cùng kết quả.

EmpathicSchool chưa có ánh xạ được chấp nhận. `unknown`, thiếu nhãn và đoạn ngoài thời gian nhãn không tự trở thành không stress.

Không dùng ngưỡng HR/GSR, điểm chất lượng, kết quả simulator hoặc dự đoán cũ để sinh đáp án stress. Không đồng nhất xác suất của model với mức nghiêm trọng. Dữ liệu tự thu chưa được gán nhãn độc lập chỉ dùng kiểm tra kỹ thuật, chưa dùng làm bộ train/test stress.

Không tăng độ phân giải nhãn chỉ bằng chia một đoạn hai phút thành nhiều cửa sổ: các cửa sổ vẫn chia sẻ cùng nhãn thô và cùng nguồn phụ thuộc. Không nội suy hoặc lấy trung bình mã nhãn phân loại để tạo mức stress mới.

## 9. Cách tổ chức dữ liệu sau chuyển đổi

Đây là định dạng đích ban đầu. Bước 3 đã tạo dữ liệu local trong `interim/wesad/normalized-v1`, tách metadata/nhãn theo từng người; xem [cấu trúc cụ thể](03-WESAD-PREPARATION.md). Chưa tạo feature/splits của phần processed:

```text
ai/data/external/wesad/              File gốc, không chỉnh sửa
ai/data/interim/wesad/
    recordings.jsonl                Metadata từng recording và từng kênh
    signals/<recording_id>/<channel>.csv
    labels.csv                      Các khoảng nhãn
ai/data/processed/wesad/
    <experiment_id>/features.parquet Feature đã tạo
    <experiment_id>/splits.json      Danh sách người/phiên của từng tập
    <experiment_id>/preprocessing.json
```

Mỗi file kênh CSV có `time_ms,value`; giá trị thiếu để trống, không điền 0. Danh tính/đơn vị/kiểu timestamp nằm trong metadata kênh của recording. Kênh giữ tần số riêng; các nguồn không có cùng tên file gốc vẫn chuyển về cùng quy ước. Nếu nguồn có cờ hợp lệ/chất lượng theo thời gian, giữ các cột nguồn cùng mô tả, không tự sinh chỉ số mới.

Metadata, labels và kết quả dẫn xuất có thể chứa dữ liệu người tham gia, phải tuân thủ điều kiện sử dụng của nguồn. `.gitignore` bỏ qua dữ liệu WESAD và EmpathicSchool; không đưa chúng lên Git. Mã xử lý và tài liệu quy ước được commit riêng. EmpathicSchool nếu được cấp quyền sẽ dùng thư mục riêng cùng cấu trúc, không ghi đè WESAD.

Định dạng CSV này không thay raw batch đang dùng ở backend. Bước 2 sẽ xác nhận dữ liệu local thực có thể chuyển đổi, không viết adapter giả định raw đã hoạt động.

## 10. Chống lộ đáp án và danh sách không dùng

- Danh sách đầu vào model đầu chỉ được tạo từ HR/điện da/gia tốc đã được chuẩn hóa đúng cách.
- ID người/thiết bị/phiên, đường dẫn, thời gian UTC, số thứ tự hàng, task, nhãn gốc và kết quả AI không được tự lọt vào X.
- Timestamp tương đối dùng chia đoạn và tính đặc trưng thời gian, không lấy thời điểm xuất hiện task làm đáp án ngầm.
- Tách người trước khi tạo cửa sổ; tất cả phiên của cùng người giữ trong cùng tập. Không chia ngẫu nhiên các cửa sổ kề nhau vào train/test.
- Chọn cấu hình trên train/validation. Không dùng test để học scaler, chọn ngưỡng, chọn feature hoặc chỉnh model.
- Nếu đánh giá thích nghi với nền người mới, khai thành bài kiểm thử riêng với đoạn nền có sẵn trước dự đoán, không trộn với kết quả không thích nghi.

## 11. Kết quả bước 1 và việc còn lại

Đã chốt: WESAD làm việc trước, bài toán nhị phân, 5 biến gốc và độ lớn gia tốc dẫn xuất để thử nghiệm, giữ raw/gyro để nghiên cứu, đơn vị rõ, metadata tách khỏi feature, nhãn theo khoảng riêng và quy tắc giữ thiếu.

Chưa chốt: phép tương thích GSR, phương pháp tính HR từ BVP, cửa sổ/hop, số feature, bộ lọc, ngưỡng chất lượng và model. Ánh xạ WESAD cần kiểm tra trên file thực trước train; phân mức stress vẫn ngoài phạm vi nhãn WESAD.

Trạng thái tải được ghi tại [WESAD](../../ai/data/external/wesad/README.md). [Bước 2](02-DATA-AUDIT.md) đã kiểm kê đủ 15 người, nhãn, đơn vị và storage thiết bị. [Bước 3](03-WESAD-PREPARATION.md) đã xuất tín hiệu/metadata/nhãn, đánh dấu kỹ thuật theo cửa sổ và tính HR ứng viên; chưa kiểm chứng sai số HR, tạo feature cuối, train hoặc đo độ chính xác stress. Không cập nhật phase ML thành DONE vì các bước chuẩn bị đã hoàn tất.

**Bước tiếp theo:** kiểm chứng HR từ BVP trong notebook trước khi chốt feature; không thay HR firmware hoặc nạp thiết bị trong bước xử lý dataset này.

## 12. Căn cứ đối chiếu

- [Cấu hình hiện tại](../../ai/edge_firmware/include/board_config.h).
- [Snapshot firmware](../../ai/edge_firmware/src/communication/telemetry_serializer.cpp) và [serializer gửi MQTT](../../ai/edge_firmware/src/communication/session_protocol.cpp).
- [Schema nhận telemetry](../../backend/app/schemas/ingestion.py), [IMU](../../backend/app/schemas/imu.py), [chất lượng](../../backend/app/schemas/quality.py), [schema raw hiện có](../../backend/app/schemas/raw_batch.py).
- [Đặc tả raw/control/telemetry](../contracts/INGESTION_V1.md) và [chất lượng 1.2](../contracts/MEASUREMENT_QUALITY_V1_2.md).
- [Quy trình dataset](../DATASET_PROTOCOL.md), [nguồn WESAD](../../ai/data/external/wesad/README.md), [trang tác giả](https://ubi29.informatik.uni-siegen.de/usi/data_wesad.html).
- [Nguồn EmpathicSchool đang chờ](../../ai/data/external/empathicschool/README.md), [bài báo](https://doi.org/10.1038/s41597-025-05812-0).

Các tài liệu lịch sử có cấu hình cũ. Với phần mô tả firmware ở bước này, ưu tiên code đã đọc; tốc độ thực vẫn phải đo riêng.
