# Quy trình Git/GitHub cho nhóm hai người

## Vai trò nhánh

- main: bản ổn định, chỉ nhận PR từ dev.
- dev: tích hợp hằng ngày, nhận PR từ nhánh công việc.
- feature/<scope>-<description>: tính năng mới.
- fix/<scope>-<description>: sửa lỗi.
- docs/<description>: tài liệu.
- chore/<description>: cấu hình, công cụ, bảo trì.

Không push trực tiếp dev/main. Mỗi nhánh một mục tiêu; không để hai người dùng chung một nhánh tính năng.

## Luồng bắt buộc

```text
feature/*, fix/*, docs/*, chore/*
                 |
                 | PR + CI + review
                 v
                dev
                 |
                 | PR + CI + review
                 v
                main
```

Trung review PR của Tân. PR do Trung tạo được dùng “Bypass rules and merge” theo quyền đã thiết lập, nhưng chỉ sau khi CI đạt, nhánh cập nhật, không xung đột và mọi trao đổi đã xử lý. Không dùng quyền này để tự bỏ review PR của Tân.

## Thiết lập lần đầu

Chủ repo vào Settings → Collaborators → Add people, mời tài khoản Tân với quyền Write, không Admin. Tân nhận lời mời rồi:

```powershell
git clone https://github.com/namtrungdn310/ASD-EASE.git
cd ASD-EASE
git switch dev
git pull --ff-only origin dev
```

Mỗi người cấu hình danh tính riêng:

```powershell
git config user.name "YOUR NAME"
git config user.email "YOUR VERIFIED GITHUB EMAIL"
```

Thay giá trị ví dụ bằng tên/email đã xác minh của mình.

## Bắt đầu công việc

Chỉ chuyển nhánh khi không có thay đổi chưa xử lý hoặc merge/rebase dở:

```powershell
git status
git switch dev
git pull --ff-only origin dev
git switch -c feature/firmware-max30102
```

Dùng scope backend/frontend/ai/firmware khi phù hợp, không tạo việc mới từ nhánh tính năng đã cũ.

## Lưu và đẩy nhánh

```powershell
git status
git add <specific-files>
git diff --staged
git commit -m "feat(firmware): thêm khung driver MAX30102"
git push -u origin feature/firmware-max30102
```

Chỉ add file đã xem. Giữ tiền tố feat/fix/docs/test/refactor/chore/ci; mô tả commit mới bằng tiếng Việt ngắn, nói việc đã làm. Không viết lại commit đã đẩy chỉ để đổi ngôn ngữ.

## PR vào dev

Trên GitHub: base=dev, compare=nhánh công việc. Tân chọn Trung làm reviewer. Điền mẫu PR, chờ đủ CI và giải quyết trao đổi; commit mới làm hết hiệu lực approval cũ theo chính sách đã ghi.

Merge bằng Squash and merge cho công việc tập trung. Sau merge, hai người cập nhật:

```powershell
git switch dev
git pull --ff-only origin dev
git branch -d feature/firmware-max30102
```

Sau squash, -d có thể từ chối vì lịch sử khác. Kiểm tra diff/commit trước, không tự chuyển sang -D. Không xoá nhánh chứa việc chưa bàn giao.

## Đưa bản ổn định lên main

1. Có bằng chứng nghiệm thu và tài liệu đã cập nhật.
2. Mở PR base=main, compare=dev.
3. Đủ CI, không xung đột; PR của Tân cần Trung approve.
4. Xử lý mọi trao đổi, chủ repo kiểm tra cuối.
5. Squash nếu là một mốc phát hành; có thể rebase để giữ các commit đã review khi phù hợp.
6. Không force-push hoặc xoá dev/main.

Sửa khẩn cấp vẫn theo fix/* → dev → main. Ngoại lệ tách từ main cần quyết định rõ của chủ repo, cập nhật chính sách bằng review và đưa bản sửa về dev; CI hiện chỉ chấp nhận PRmain từ dev.

## Bảo vệ nhánh

Theo cấu hình đã ghi nhận, dev/main yêu cầu PR, CI trên nhánh cập nhật, giải quyết trao đổi và lịch sử tuyến tính; chặn push trực tiếp/force-push/xoá nhánh. PR cộng tác viên cần chủ repo duyệt; chỉ chủ repo có ngoại lệ lúc merge PR của mình.

Nhánh mặc định là dev. Đây là mô tả quy trình đã thống nhất, không phải kết quả kiểm tra quyền GitHub trực tuyến trong lần dịch tài liệu này.
