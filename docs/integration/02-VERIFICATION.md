# Nhánh02 — bằng chứng kiểm tra

Hồ sơ ngày2026-10-20, nhánh fix/frontend-live-connection-status. [PR #10](https://github.com/namtrungdn310/ASD-EASE/pull/10) tạo bản nháp ở head feb8ba3; sau đó đã merge theo tracker. Các lệnh dưới không tự xác nhận CI của head khác.

Trung viết mã cốt lõi; bước kiểm tra thêm tests, dependency và tài liệu. Thay đổi gồm kiểm tra payload, lịch sử60 điểm theo thiết bị/phiên/nguồn, trạng thái còn mới, dọn kết nối lại, chọn thiết bị, nhãn dữ liệu cũ và nguồn giả lập.

## Kết quả đã ghi

| Mục | Lệnh/bằng chứng | Kết quả |
|---|---|---|
| Frontend và vòng đời React | cd frontend; npm test |26/26 PASS |
| TypeScript/build | cd frontend; npm run build |PASS, cảnh báo bundle>500 kB |
| Audit production | cd frontend; npm audit --omit=dev |0 lỗ hổng ở lần đó |
| Backend | pytest từ backend bằng .venv |13 PASS, cảnh báo dependency cũ |
| AI | pytest từ ai bằng .venv |15 PASS, cảnh báo dependency cũ |
| Simulator HTTP→backend→WS thật | .github/scripts/check-mock-transport.py |18/18 gói khớp ở NORMAL_REST/POOR_SIGNAL/DISCONNECT_RECONNECT |
| Ngắt/nối | Cùng script trên |HTTP422 không phát gói sai; tạm ngắt2 s giữ timestamp; subscriber nhận lại bản mới |
| Compose | docker compose config --quiet |PASS |
| Header firmware | .github/scripts/check-firmware-headers.py |4 tổ hợp PASS, không xác nhận board |
| Container | docker compose up -d --build backend frontend |Hai image build/container chạy, backend khoẻ |
| Phục vụ local | health8000 và frontend5173 |HTTP200, chưa bằng chứng trực quan |

Script mạng dùng DB/cổng tạm, không DB ứng dụng. Tạm ngắt2 s chưa kiểm tra ngưỡng stale5 s; ngưỡng đó được thử riêng với đồng hồ có kiểm soát trong tests React.

## Giới hạn

- Render server dùng component/helper thật, hook mẫu để kiểm soát trạng thái.
- React DOM/hooks/StrictMode thật trong jsdom; socket, đồng hồ và timer được thay có kiểm soát.
- Kiểm tra chuyển lịch sử60 điểm không chứng minh nét vẽ/CSS/bố cục hoặc trình đọc màn hình.
- Kiểm tra đường truyền thật không có browser; chưa phải một lần E2E liên tục simulator→browser.

## Còn thiếu nghiệm thu trực quan

Công cụ trả No browser is available, discovery=[], dù đã thử theo hướng dẫn. Giữ BLOCKED_BROWSER/Phase02 IN_PROGRESS. Việc merge code sau đó không biến kiểm tra hiển thị thành PASS.

## Các bước kiểm tra tay

1. Chạy docker compose up -d --build backend frontend.
2. Mở http://localhost:5173, tải lại mạnh; trước phát lại phải thấy backend có kết nối/đang chờ. Trang mới không tự tải lịch sử.
3. Từ root phát lại:

```powershell
$env:PYTHONPATH = (Resolve-Path .\ai).Path
.\.venv\Scripts\python.exe -m simulator.mock_device --scenario attention_mock --duration 15
```

4. Chụp trạng thái live, SYNTHETIC DATA, SIM-001, phiên, số đo và đường biểu đồ. Không coi đây là bằng chứng lâm sàng.
5. Giữ trang sau khi dừng simulator ít nhất6 s; chụp stale, cảnh báo cũ, biểu đồ/số giữ lại và dự đoán/chất lượng hiện tại chưa có. Nhãn nguồn vẫn rõ.
6. Phát poor_signal, kiểm tra UNCERTAIN/probabilitynull, không giả0%.
7. Dừng riêng backend bằng docker compose stop backend, chụp disconnected; docker compose start backend, phải waiting tới gói mới rồi live.
8. Thử hai device ID, bàn phím, màn hình375px và desktop; ghi lỗi/tràn bố cục. Tests DOM không thay kiểm tra này.
9. Đính kèm ảnh, trình duyệt/thiết bị rồi mới tick nghiệm thu; không suy từ build/HTTP200.
