# 01 — Dọn nền tảng tích hợp

| Mục | Nội dung |
|---|---|
| Nhánh | `chore/repository-integration-cleanup` |
| Phụ trách | Trung — IT; Tân phối hợp GPIO/board |
| Phụ thuộc | PRkế hoạch #8 đã merge tại0bcd833 |
| Ước lượng |0,5–1 ngày |
| Tiến độ |[Dòng01](PROGRESS.md) |

## Mục tiêu và tình trạng

Cấu hình chia sẻ được giữa hai máy, không dấu conflict, tài liệu tách code khỏi bằng chứng phần cứng. Không đổi thuật toán cảm biến.

**Đã merge PR #9 vào dev tại86cd09f ngày2026-10-18.** Hoàn tất phần dọn phần mềm; wiring/rate/flash vẫn cần đo. GPIO4 dưới đây là cấu hình thời điểm cleanup, hiện sau PR #11 đã là7.

## Vấn đề lúc bắt đầu

FINAL_VERIFICATION còn conflict ở lệnh PlatformIO; .env.example bị xoá trong PR #7; file IDE/compile_commands có đường dẫn riêng nhưng đã theo dõi trong Git; header chân/rate/enum bị trùng; tài liệu chưa phản ánh driver đã có.

## Công việc và bàn giao

- [x] Tạo nhánh từ dev sạch; sửa nội dung conflict, dùng pio run -d ai/edge_firmware từ root.
- [x] Khôi phục mẫu môi trường không secret, phân biệt cấu hình backend/Vite lúc build.
- [x] Bỏ theo dõi file IDE riêng nhưng giữ file trên đĩa; ignore không tự bỏ file đã theo dõi.
- [x] Không thay đường dẫn máy Tân bằng máy Trung hoặc xoá sản phẩm của người khác.
- [x] board_config là nguồn cấu hình chung, giữ include/alias tương thích, không đổi giá trị.
- [ ] Tân xác nhận dây nối/board/driver bằng phép đo thật.
- [ ] Xác nhận wiring GSR trước thay hằng số; comment không là bằng chứng.
- [x] Enum Availability/EngineeringState chỉ một nguồn, không lỗi khi ghép interfaces và header cảm biến.
- [x] Không đoán flash/PSRAM từ tên board.
- [x] CI kiểm tra marker conflict, phân biệt mã trả về không có kết quả với lỗi Git.
- [x] Giữ nguyên tên6 checks bảo vệ nhánh.
- [x] Cập nhật phần cứng/giai đoạn/changelog/tracker, không đánh DONE từ build.
- [x] CI cuối c764210 đạt6/6, PR #9 đã merge sau kế hoạch #8.

## Các file cốt lõi Trung đã viết

1. common_types.h: enum chung, UNAVAILABLE đúng tên.
2. board_config.h: dùng kiểu chung, bỏ enum trùng, giữ cấu hình lúc đó.
3. interfaces.h: bỏ định nghĩa lặp, dùng chung enum/TelemetryFrame.
4. pins.h: chuyển thành include board_config, giữ alias.
5. sensor_config.h: chuyển thành include board_config, bỏ rate trùng.

Codex xử lý Git/tài liệu/comment/cấu hình/tests. Build từng bước và tổ hợp header đều đạt, không đổi logic Trung viết.

## Bằng chứng đã ghi

| Lần kiểm tra2026-10-18 | Kết quả |
|---|---|
| Quét conflict | Có marker trả1, repo sạch0, ngoài repo lỗi Git128 |
| Môi trường/Compose | Settings đọc mẫu, Compose và diff đạt |
| File máy riêng |4 file bỏ theo dõi, SHA256 trên đĩa không đổi |
| Backend/AI |13/15 tests đạt |
| Tài liệu |27 link local tồn tại, đủ25 giai đoạn |
| common_types | Kiểm tra cú pháp, include lặp, đủ8 giá trị enum |
| Lần build sau board_config | Ban đầu lỗi UNVAILABLE trong file đã lưu; sửa UNAVAILABLE thì build đạt26.84 s |
| interfaces/pins/sensor_config | Include độc lập/lặp/đảo thứ tự và alias đạt, GPIO4 lúc đó giữ nguyên |
| Bước cuối |Firmware build,4 tổ hợp header, frontend build, Compose, conflict/diff đạt |
| Sau PR #8 |3 commit cleanup được rebase lên0bcd833, tree trước/sau giống nhau;4 file local giữ hash |
| CI |6/6 ở7ff1851 trước rebase; kết quả cuối c7642106/6 trước merge |

Không coi kiểm tra cú pháp hoặc GPIOalias là xác nhận dây vật lý. Sau PR #11 có một số file IDE được đưa lại; đó là diễn biến sau cleanup, không thay kết quả lịch sử.

## Kiểm tra lại và khôi phục

Dùng git ls-files, git check-ignore -v <path>, git diff --check và [lệnh dùng lại](README.md#lệnh-kiểm-tra-dùng-lại). Xem diff để không lẫn credential/dữ liệu người tham gia.

Giữ bản cấu hình local trước bỏ theo dõi. Sửa/hoàn tác bằng commit trên nhánh công việc, không reset dev hoặc xoá .venv/.platformio toàn máy.

Sau01: [02](02-frontend-live-connection-status.md) hoặc [03](03-device-ingestion-contract.md).
