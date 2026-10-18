# 01 — Dọn nền tảng tích hợp

| Thuộc tính | Giá trị |
|---|---|
| Nhánh | `chore/repository-integration-cleanup` |
| Chủ trì | Trung — IT; GPIO/board phối hợp Tân |
| Phụ thuộc | PR kế hoạch đã merge vào dev |
| Ước lượng | 0,5–1 ngày |
| Theo dõi | [PROGRESS.md](PROGRESS.md), dòng 01 |

## Kết quả cần đạt

Repo có cấu hình chia sẻ được giữa hai máy, không còn marker conflict, tài liệu phân biệt implementation với kiểm chứng phần cứng. Không thay đổi thuật toán cảm biến trong PR dọn dẹp.

## Hiện trạng và file dự kiến

- `docs/FINAL_VERIFICATION.md` còn marker conflict ở lệnh PlatformIO.
- `.env.example` bị xoá trong PR #7.
- `ai/edge_firmware/.vscode/` và `compile_commands.json` đã tracked dù có đường dẫn máy Tân; ignore không tự bỏ file đã tracked.
- Driver mới đọc `board_config.h`, trong khi `pins.h`/`sensor_config.h` còn định nghĩa trùng hoặc cũ.
- `docs/HARDWARE_PROFILE.md`, `PROGRESS.md`, phase 03–06 chưa phản ánh việc đã có implementation driver.
- File sửa: các file trên, `.gitignore`, `.github/workflows/ci.yml`, `docs/CHANGELOG.md`.

## Checklist triển khai

- [x] Xác nhận working tree sạch, cập nhật `dev`, tạo đúng tên nhánh.
- [x] Xử lý conflict bằng nội dung đúng: từ root chạy `pio run -d ai/edge_firmware`; tìm marker còn sót trong file tracked.
- [x] Khôi phục `.env.example` từ cấu hình thực dùng, chỉ placeholder; mô tả khác biệt biến backend với biến Vite được đưa vào lúc build.
- [x] Bỏ tracking các file IDE sinh tự động chứa đường dẫn máy; giữ lại file trên máy người dùng nếu cần, thêm ignore. Không xoá source hay build artefact của người khác ngoài phạm vi.
- [x] Giữ cấu hình IDE chia sẻ được chỉ khi đã loại đường dẫn tuyệt đối và chứng minh có tác dụng; không thay bằng đường dẫn máy Trung.
- [ ] Thống nhất với Tân cách hợp nhất pin/sampling config. Chọn một nguồn định nghĩa, giữ wrapper include/alias nếu còn consumer.
- [ ] Xác nhận wiring GSR trước khi sửa hằng số; nếu chưa có bằng chứng, ghi rõ chưa xác nhận thay vì suy từ comment.
- [ ] Giữ sensor enums/`Availability` ở một nguồn để tránh lỗi định nghĩa lại khi communication module dùng `interfaces.h` và sensor headers cùng lúc.
- [x] Không tự đổi flash/PSRAM theo tên thương mại của board; giữ bằng chứng và cấu hình build tách biệt.
- [x] Bổ sung CI kiểm tra marker conflict bằng các dòng bắt đầu `<<<<<<< `, `=======`, `>>>>>>> `; xử lý exit code khi không có match, không để lệnh scan tự làm job fail sai.
- [x] Giữ nguyên tên sáu required checks đang được branch protection dùng.
- [x] Cập nhật phase/hardware docs về code hiện có và bằng chứng còn thiếu; không đánh dấu DONE từ build-only.
- [x] Cập nhật changelog, checklist nhánh và tracker.

## Chế độ học code và công việc còn lại

Theo yêu cầu của Trung, Codex xử lý nhánh/Git, Markdown, môi trường/IDE và CI; Trung tự viết source cốt lõi. Mỗi lần chỉ hướng dẫn một file, sau khi kiểm tra diff file đó mới chuyển tiếp.

Phần hỗ trợ đã làm: sửa conflict trong tài liệu, mẫu môi trường + hướng dẫn `docs/LOCAL_SETUP.md`, ignore/untrack file máy cá nhân (giữ nguyên trên disk), CI scanner và cập nhật phase/tracker. Source `.py`, `.ts`, `.tsx`, `.h`, `.cpp` chưa sửa.

Thứ tự source dự kiến để Trung tự viết:

1. Tạo `ai/edge_firmware/include/common_types.h` làm nguồn chung cho `Availability` và `EngineeringState`.
2. Sửa `board_config.h` dùng common types, bỏ enum trùng; chú thích GPIO chỉ phản ánh giá trị cấu hình, chưa khẳng định wiring đã xác minh.
3. Sửa `interfaces.h` dùng common types, bỏ định nghĩa enum lặp.
4. Sửa `pins.h` thành wrapper cấu hình tương thích, không giữ bộ GPIO khác với `board_config.h`.
5. Sửa `sensor_config.h` thành wrapper cho sample-rate config, không khai báo hằng số lặp.

Build/kiểm tra include sau từng thay đổi phù hợp, rồi kiểm tra cả tổ hợp headers để phát hiện duplicate definitions. Chưa đổi giá trị GPIO/flash hoặc thuật toán driver khi thiếu bằng chứng phần cứng.

## Kiểm thử / bằng chứng cần lưu

| Kiểm tra | Kết quả mong đợi |
|---|---|
| Scan marker trên tracked files | Không còn marker thật; phân biệt ví dụ tài liệu nếu có |
| Kiểm tra ignore/tracked IDE config | File máy cá nhân không còn trong commit; local config cần thiết vẫn dùng được |
| Firmware build trên Windows và CI Linux | Không lỗi include, enum hay case đường dẫn |
| Compose config, backend/AI tests, frontend build | Không regression |
| Diff review | Không credential, dữ liệu người tham gia hay thay đổi driver ngoài phạm vi |

Lệnh tham khảo: `git ls-files`, `git check-ignore -v <path>`, `git diff --check`, các lệnh baseline trong [README](README.md#lệnh-kiểm-tra-dùng-lại).

## Điều kiện merge / bàn giao

- [ ] Config source thống nhất hoặc phần còn thiếu được ghi blocker cụ thể.
- [x] Không còn đường dẫn cá nhân trong cấu hình tracked dùng chung.
- [x] CI marker check đã kiểm tra được cả tình huống có/không có marker.
- [ ] Required checks xanh; docs ghi đúng phần chưa kiểm chứng.
- [ ] PR vào `dev`, commit gợi ý: `chore: clean up firmware integration configuration`.

## Rollback

Giữ bản local config trước khi untrack nếu đang dùng. Nếu cấu hình chung mới làm build hỏng, sửa/revert bằng commit trên nhánh công việc; không reset `dev`, không xoá `.venv` hay thư mục `.platformio` toàn máy.

## Nhật ký / kết quả thực hiện

| Ngày / commit | Task | Command / bằng chứng | Kết quả / blocker |
|---|---|---|---|
| 2026-10-18 / cleanup branch | Tài liệu, env, IDE và CI | Scanner bắt marker cũ (exit 1), repo đã dọn pass (exit 0), ngoài repo trả lỗi Git 128; template đọc được bằng Settings thật; Compose config và diff check pass; 4 file untrack giữ nguyên SHA256 trên disk; 13 backend + 15 AI tests pass; 27 local links tồn tại và 25 phase files giữ nguyên | Phần hỗ trợ xong; chờ Trung viết common_types và cập nhật các headers, cộng xác nhận wiring từ Tân. Chưa đóng toàn nhánh |

Nhánh tiếp: [02](02-frontend-live-connection-status.md) hoặc [03](03-device-ingestion-contract.md) sau khi 01 merge.
