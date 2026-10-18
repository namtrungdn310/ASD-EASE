# 01 — Dọn nền tảng tích hợp

| Thuộc tính | Giá trị |
|---|---|
| Nhánh | `chore/repository-integration-cleanup` |
| Chủ trì | Trung — IT; GPIO/board phối hợp Tân |
| Phụ thuộc | Đã đáp ứng: PR kế hoạch #8 merge vào dev tại 0bcd833 |
| Ước lượng | 0,5–1 ngày |
| Theo dõi | [PROGRESS.md](PROGRESS.md), dòng 01 |

## Kết quả cần đạt

Repo có cấu hình chia sẻ được giữa hai máy, không còn marker conflict, tài liệu phân biệt implementation với kiểm chứng phần cứng. Không thay đổi thuật toán cảm biến trong PR dọn dẹp.

## Hiện trạng trước cleanup và file dự kiến

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
- [x] Hợp nhất pin/sampling config ở mức source: board_config là nguồn chung, giữ wrapper include/alias cho consumer cũ và không đổi giá trị.
- [ ] Tân xác nhận wiring/driver metadata khi có phần cứng; ghi việc phối hợp chưa thực hiện thay vì coi build là xác nhận.
- [ ] Xác nhận wiring GSR trước khi sửa hằng số; nếu chưa có bằng chứng, ghi rõ chưa xác nhận thay vì suy từ comment.
- [x] Giữ sensor enums/`Availability` ở một nguồn để tránh lỗi định nghĩa lại khi communication module dùng `interfaces.h` và sensor headers cùng lúc.
- [x] Không tự đổi flash/PSRAM theo tên thương mại của board; giữ bằng chứng và cấu hình build tách biệt.
- [x] Bổ sung CI kiểm tra marker conflict bằng các dòng bắt đầu `<<<<<<< `, `=======`, `>>>>>>> `; xử lý exit code khi không có match, không để lệnh scan tự làm job fail sai.
- [x] Giữ nguyên tên sáu required checks đang được branch protection dùng.
- [x] Cập nhật phase/hardware docs về code hiện có và bằng chứng còn thiếu; không đánh dấu DONE từ build-only.
- [x] Cập nhật changelog, checklist nhánh và tracker.

## Chế độ học code và công việc còn lại

Theo yêu cầu của Trung, Codex xử lý nhánh/Git, Markdown, môi trường/IDE và CI; Trung tự viết source cốt lõi. Mỗi lần chỉ hướng dẫn một file, sau khi kiểm tra diff file đó mới chuyển tiếp.

Phần hỗ trợ đã làm: sửa conflict trong tài liệu, mẫu môi trường + hướng dẫn `docs/LOCAL_SETUP.md`, ignore/untrack file máy cá nhân (giữ nguyên trên disk), CI scanners và cập nhật phase/tracker. Trung đã tự viết cả năm source headers bên dưới. Codex chỉ sửa comment/khoảng trắng và hạ tầng kiểm tra, không đổi logic Trung viết. Firmware build và cả bốn tổ hợp header đều PASS; phần source của nhánh 01 đã hoàn tất, chờ PR/CI và review, chưa xác minh wiring vật lý.

Thứ tự source dự kiến để Trung tự viết:

1. Đã tạo `ai/edge_firmware/include/common_types.h`; `UNAVAILABLE` đúng trong bản đã lưu, syntax/full firmware build PASS. Đã dọn khoảng trắng cuối dòng trước commit.
2. `board_config.h` đã dùng common types, bỏ enum trùng; comment GPIO4 khớp cấu hình và ghi chưa xác minh wiring. Diff đúng; full firmware build PASS với hai header hiện tại.
3. `interfaces.h` đã dùng common types, bỏ hai định nghĩa enum lặp. Compiler ESP32-S3 kiểm tra include chung với board_config theo cả hai thứ tự, include lặp, dùng enum/TelemetryFrame/placeholder class: PASS.
4. `pins.h` đã thành wrapper include `board_config.h`, bỏ `PIN_UNVERIFIED` và các GPIO trùng. Syntax check độc lập, include lặp và include chung với board_config/interfaces PASS; GPIO alias giữ đúng cấu hình hiện có.
5. `sensor_config.h` đã thành wrapper include board_config, bỏ các sample-rate constants trùng. Syntax check độc lập, include theo các thứ tự và với ba sensor headers đều PASS.

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

- [x] Config source thống nhất hoặc phần còn thiếu được ghi blocker cụ thể.
- [x] Không còn đường dẫn cá nhân trong cấu hình tracked dùng chung.
- [x] CI marker check đã kiểm tra được cả tình huống có/không có marker.
- [x] Required checks xanh; docs ghi đúng phần chưa kiểm chứng. CI cuối ở commit c764210 PASS 6/6.
- [x] Đã mở [PR #9 vào dev](https://github.com/namtrungdn310/ASD-EASE/pull/9). PR #8 đã merge; cleanup đã rebase lên dev mới, không còn đưa lại commit kế hoạch vào ancestry. Chuẩn bị review sau khi required checks trên commit mới pass.

### Kết quả bàn giao

PR #9 đã merge vào dev tại `86cd09f` ngày 2026-10-18. Nhánh 01 hoàn tất trong phạm vi software cleanup; GPIO/rates/flash/driver logic không đổi. Các task xác nhận wiring/đo phần cứng chưa được tick vì chưa có bằng chứng từ Tân; phần còn thiếu đã được ghi rõ và tiếp tục theo dõi trong hardware profile/tracker, không chặn việc sửa trạng thái UI ở nhánh 02.

## Rollback

Giữ bản local config trước khi untrack nếu đang dùng. Nếu cấu hình chung mới làm build hỏng, sửa/revert bằng commit trên nhánh công việc; không reset `dev`, không xoá `.venv` hay thư mục `.platformio` toàn máy.

## Nhật ký / kết quả thực hiện

| Ngày / commit | Task | Command / bằng chứng | Kết quả / blocker |
|---|---|---|---|
| 2026-10-18 / cleanup branch | Tài liệu, env, IDE và CI | Scanner bắt marker cũ (exit 1), repo đã dọn pass (exit 0), ngoài repo trả lỗi Git 128; template đọc được bằng Settings thật; Compose config và diff check pass; 4 file untrack giữ nguyên SHA256 trên disk; 13 backend + 15 AI tests pass; 27 local links tồn tại và 25 phase files giữ nguyên | Phần hỗ trợ xong; chờ Trung viết common_types và cập nhật các headers, cộng xác nhận wiring từ Tân. Chưa đóng toàn nhánh |
| 2026-10-18 / local common_types.h | Trung tạo shared enum header, sửa UNAVAILABLE đúng tên | Compiler ESP32-S3 `-fsyntax-only`, include header hai lần và tham chiếu đủ 8 enum values: PASS | Header đúng; bỏ trailing whitespace dòng 3 trước commit. Tiếp theo board_config.h, chưa build toàn firmware với các consumer mới |
| 2026-10-18 / local board_config.h | Include common types, bỏ enum trùng; comment GPIO do Codex cập nhật | `pio run -d ai/edge_firmware`: FAIL ở MAX30102Sensor.cpp và MPU6050Sensor.cpp vì UNAVAILABLE không có trong enum; disk hiện lại ghi UNVAILABLE | Diff board_config đúng. Chờ Trung sửa/lưu common_types.h rồi build lại; chưa chuyển interfaces.h |
| 2026-10-18 / saved common_types.h + board_config.h | Trung sửa và lưu lại UNAVAILABLE; kiểm tra bản trên disk | `pio run -d ai/edge_firmware`: SUCCESS, exit 0, 26.84 giây | Hai file đạt kiểm tra hiện tại; tiếp interfaces.h. Build này chưa kiểm tra tổ hợp các header legacy/placeholder chưa được main sử dụng |
| 2026-10-18 / local interfaces.h | Trung include common_types và bỏ enum trùng | Firmware build SUCCESS; compiler dùng metadata PlatformIO hiện tại kiểm tra board_config/interfaces theo cả hai thứ tự, include lặp và sử dụng enum/struct/class: PASS | interfaces.h đạt; tiếp pins.h. Header legacy pins/sensor_config chưa hợp nhất |
| 2026-10-18 / local pins.h | Trung chuyển pins thành wrapper board_config | Compiler ESP32-S3 syntax-check pins độc lập và hai tổ hợp với board_config/interfaces/include lặp; static_assert kiểm tra aliases và GSR giữ cấu hình GPIO4: PASS | pins.h đạt; tiếp sensor_config.h. Đây là kiểm tra cấu hình source, không xác minh wiring vật lý |
| 2026-10-18 / local sensor_config.h và final source review | Trung chuyển sample config thành wrapper; Codex dọn khoảng trắng và thêm script CI kiểm tra headers | Firmware build SUCCESS; `.github/scripts/check-firmware-headers.py`: 4 tổ hợp PASS; frontend build, Compose config, conflict scan và diff check PASS; backend/AI vẫn giữ kết quả 13/15 tests đã chạy trên phần hỗ trợ | Năm file core của cleanup đã hoàn tất; chờ PR/CI. GPIO/rate/flash/driver algorithms không đổi; wiring vẫn chưa xác nhận |
| 2026-10-18 / rebase sau PR #8 | Đưa ba commit cleanup lên dev 0bcd833 sau squash merge kế hoạch | Nội dung tree trước/sau rebase giống nhau, 4 local generated files giữ nguyên SHA256; CI trước rebase đã PASS 6/6 ở 7ff1851 | Phụ thuộc #8 đã xử lý; chạy lại CI trên commit mới và review PR #9. Chưa merge cleanup hoặc bắt đầu nhánh 02 |

Nhánh tiếp: [02](02-frontend-live-connection-status.md) hoặc [03](03-device-ingestion-contract.md) sau khi 01 merge.
