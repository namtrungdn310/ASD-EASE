/** Chỉ tự chọn USB Serial/JTAG của ESP32-S3, không chọn cổng Bluetooth. */
export function selectEspPort(ports) {
  const candidates = ports.filter(port => port.vid === 0x303a && port.pid === 0x1001);
  if (candidates.length > 1) {
    throw new Error("Có nhiều ESP qua USB. Chỉ cắm một ESP cần nạp rồi chạy lại npm run device:flash.");
  }
  return candidates[0]?.device ?? null;
}

export function prepareFirmware({ command, executable, prefix, wifiConfigured, requirePort = false }) {
  if (!wifiConfigured) {
    console.log("Chưa cấu hình Wi-Fi; bỏ qua build/nạp ESP. Điền network_config.h rồi chạy lại.");
    return;
  }
  command(executable, [...prefix, "-c", "import platformio, serial.tools.list_ports"], {
    failure: "Cần PlatformIO và pyserial trong Python đang dùng. Cài bằng python -m pip install platformio==6.2.0 pyserial rồi thử lại.",
  });
  console.log("Đang build firmware với network_config.h hiện tại...");
  const args = [...prefix, "-m", "platformio", "run", "-d", "ai/edge_firmware", "-e", "esp32s3_supermini"];
  command(executable, args, { stdio: "inherit", failure: "Build firmware lỗi; chưa nạp ESP. Sửa lỗi phía trên rồi chạy lại." });
  const ports = JSON.parse(command(executable, [...prefix, "-c",
    "import json; from serial.tools.list_ports import comports; print(json.dumps([dict(device=p.device,vid=p.vid,pid=p.pid) for p in comports()]))",
  ]));
  const port = selectEspPort(ports);
  if (!port) {
    if (requirePort) throw new Error("Không tìm thấy ESP32-S3 qua USB; firmware đã build nhưng chưa nạp. Cắm cáp USB truyền dữ liệu rồi chạy lại npm run device:flash.");
    console.log("Build xong nhưng không thấy ESP32-S3 qua USB: chưa nạp firmware.");
    return;
  }
  console.log(`Đang nạp ESP qua ${port}; ESP sẽ khởi động lại và tạo phiên theo boot mới.`);
  command(executable, [...args, "-t", "upload", "--upload-port", port], {
    stdio: "inherit", failure: "Nạp ESP chưa thành công. Đóng Serial Monitor, kiểm tra dây USB rồi chạy lại; không tự bỏ qua lỗi nạp.",
  });
  console.log("Đã nạp ESP. Dữ liệu Dashboard vẫn truyền qua Wi-Fi/MQTT, không qua USB.");
}
