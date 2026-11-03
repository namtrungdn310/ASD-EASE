# Cấu hình broker

Cấu hình thống nhất nằm ở `infra/mosquitto/` và service `broker` trong compose.yaml.
Đường thử `asd/v1/devices/.../sensors/*` của PR #14 đã bỏ vì khác contract và không có xác thực phiên.
Không chạy broker/subscriber thứ hai để ghép sensor hoặc bỏ qua receiver04.

Đọc `docs/integration/05-SETUP.md` cho thiết bị DEVICE/LAN và `04-SETUP.md` cho simulator.
Credential cũ trong config local vẫn bị Git bỏ qua; không chuyển lên repo.
