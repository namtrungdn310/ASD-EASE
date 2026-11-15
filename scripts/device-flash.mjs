/** Build và nạp ESP theo cấu hình local; chỉ chạy khi người dùng gọi rõ lệnh này. */
import { existsSync } from "node:fs";
import { join } from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { prepareFirmware } from "./dev-firmware.mjs";

const root = fileURLToPath(new URL("../", import.meta.url));
const fail = message => { throw new Error(message); };

function python() {
  const local = join(root, ".venv", process.platform === "win32" ? "Scripts/python.exe" : "bin/python");
  for (const [executable, prefix] of [[local, []], ["py", ["-3.12"]], ["python3", []], ["python", []]]) {
    const result = spawnSync(executable, [...prefix, "-c", "import sys; print(sys.version_info >= (3, 12))"], { encoding: "utf8" });
    if (!result.error && result.status === 0 && result.stdout.trim() === "True") return [executable, prefix];
  }
  fail("Cần Python 3.12 trở lên. Cài Python rồi chạy lại npm run device:flash.");
}

try {
  const [executable, prefix] = python();
  if (!existsSync(join(root, "ai/edge_firmware/platformio.ini"))) fail("Không tìm thấy firmware trong repo này.");
  const prepared = spawnSync(executable, [...prefix, join(root, "scripts/local_dev.py")], { cwd: root, encoding: "utf8" });
  if (prepared.error || prepared.status !== 0) fail(prepared.stderr?.trim() || "Chưa chuẩn bị được cấu hình thiết bị local.");
  const local = JSON.parse(prepared.stdout);
  if (!local.wifiConfigured) fail("Chưa điền WIFI_SSID và WIFI_PASSWORD trong network_config.h.");

  const command = (exe, args, options = {}) => {
    const result = spawnSync(exe, args, { cwd: root, encoding: "utf8", ...options });
    if (result.error || result.status !== 0) fail(options.failure ?? "Lệnh build/nạp firmware chưa chạy được.");
    return result.stdout?.trim() ?? "";
  };
  prepareFirmware({ command, executable, prefix, wifiConfigured: true, requirePort: true });
} catch (error) {
  console.error(error instanceof Error ? error.message : "Chưa build/nạp được ESP.");
  process.exitCode = 1;
}
