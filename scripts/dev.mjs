/** Cùng launcher cho npm run dev ở root hoặc frontend. Không ghi/in secret. */
import { createHash } from "node:crypto";
import { existsSync, readFileSync, readdirSync, writeFileSync } from "node:fs";
import net from "node:net";
import { join } from "node:path";
import { spawn, spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const root = fileURLToPath(new URL("../", import.meta.url));
const frontend = join(root, "frontend");
const fail = message => { throw new Error(message); };

function command(executable, args, options = {}) {
  const result = spawnSync(executable, args, { cwd: root, encoding: "utf8", ...options });
  if (result.error || result.status !== 0) fail(options.failure ?? `Lệnh ${executable} chưa chạy được.`);
  return result.stdout?.trim() ?? "";
}

function python() {
  const local = join(root, ".venv", process.platform === "win32" ? "Scripts/python.exe" : "bin/python");
  for (const [executable, prefix] of [[local, []], ["py", ["-3.12"]], ["python3", []], ["python", []]]) {
    const result = spawnSync(executable, [...prefix, "-c", "import sys; print(sys.version_info >= (3, 12))"], { encoding: "utf8" });
    if (!result.error && result.status === 0 && result.stdout.trim() === "True") return [executable, prefix];
  }
  fail("Cần Python3.12 trở lên. Cài Python rồi chạy lại npm run dev.");
}

function availablePort(host) {
  return new Promise((resolvePort, reject) => {
    const probe = net.createServer();
    probe.once("error", error => {
      if (["EADDRNOTAVAIL", "EAFNOSUPPORT"].includes(error.code)) resolvePort();
      else reject(new Error("Cổng5173 đang được dùng. Dừng phiên frontend cũ rồi chạy lại npm run dev."));
    });
    probe.listen(5173, host, () => probe.close(resolvePort));
  });
}

function sourceHash() {
  const hash = createHash("sha256");
  function visit(directory) {
    for (const entry of readdirSync(directory, { withFileTypes: true }).sort((a, b) => a.name.localeCompare(b.name))) {
      const path = join(directory, entry.name);
      if (entry.isDirectory() && entry.name !== "__pycache__") visit(path);
      else if (entry.isFile() && entry.name.endsWith(".py")) hash.update(path.slice(root.length)).update(readFileSync(path));
    }
  }
  visit(join(root, "backend/app"));
  for (const name of ["Dockerfile", "requirements.txt", ".dockerignore"]) hash.update(readFileSync(join(root, "backend", name)));
  return hash.digest("hex");
}

async function main() {
  command("docker", ["info", "--format", "{{.ServerVersion}}"], { failure: "Hãy mở Docker Desktop, chờ engine chạy rồi thử lại." });
  if (process.argv.includes("--stop")) {
    if (!existsSync(join(root, ".env"))) fail("Chưa có cấu hình local để dừng.");
    const saved = Object.fromEntries(readFileSync(join(root, ".env"), "utf8").split(/\r?\n/)
      .filter(line => /^(COMPOSE_PROJECT_NAME|MQTT_LOCAL_DIR|MQTT_BIND_IP|MQTT_HOST_PORT|APP_BIND_IP)=/.test(line))
      .map(line => [line.slice(0, line.indexOf("=")), line.slice(line.indexOf("=")+1).replace(/^["']|["']$/g, "")]));
    if (!/^[a-z0-9][a-z0-9_-]*$/.test(saved.COMPOSE_PROJECT_NAME ?? "")) fail("Không xác định được Compose project local.");
    command("docker", ["compose", "-p", saved.COMPOSE_PROJECT_NAME, "stop", "broker", "backend"], {
      stdio: "inherit", env: { ...process.env, ...saved },
    });
    console.log("Đã dừng broker/backend local, giữ nguyên dữ liệu.");
    return;
  }
  await availablePort("127.0.0.1");
  await availablePort("::1");
  const [executable, prefix] = python();
  const prepared = spawnSync(executable, [...prefix, join(root, "scripts/local_dev.py")], { cwd: root, encoding: "utf8" });
  if (prepared.error || prepared.status !== 0) fail(prepared.stderr?.trim() || "Chưa chuẩn bị được cấu hình local.");
  const local = JSON.parse(prepared.stdout);
  const environment = {
    ...process.env, ...local.compose, ASD_DEV_CREDENTIALS_DIR: local.credentialsDirectory,
    VITE_API_BASE_URL: "http://localhost:8000", VITE_WS_URL: "ws://localhost:8000/api/v1/ws/live",
  };
  console.log(`Thiết bị ${local.deviceId}; broker LAN ${local.brokerHost}:${local.brokerPort}.`);
  if (local.firmwareChanged) console.log("Đã đồng bộ network_config.h local. Nạp lại ESP để dùng cấu hình này.");
  if (!local.wifiConfigured) console.log("Điền WIFI_SSID/WIFI_PASSWORD trong network_config.h và nạp ESP lần đầu. Dashboard vẫn mở để chờ thiết bị.");

  const statePath = join(local.credentialsDirectory, "dev-state.json");
  let state = {};
  if (existsSync(statePath)) {
    try { state = JSON.parse(readFileSync(statePath, "utf8")); } catch { /* Tạo lại metadata, giữ credential. */ }
  }
  const dependencies = createHash("sha256").update(readFileSync(join(frontend, "package-lock.json"))).digest("hex");
  if (!existsSync(join(frontend, "node_modules/vite/bin/vite.js")) || state.frontendLock !== dependencies) {
    if (!process.env.npm_execpath) fail("Chạy launcher bằng npm run dev để cài dependencies frontend lần đầu.");
    console.log("Đang đồng bộ dependencies frontend theo package-lock...");
    command(process.execPath, [process.env.npm_execpath, "ci", "--prefix", frontend, "--prefer-offline", "--no-audit"], { stdio: "inherit" });
  }
  const digest = sourceHash();
  const image = spawnSync("docker", ["image", "inspect", `${local.compose.COMPOSE_PROJECT_NAME}-backend`], { stdio: "ignore" });
  const build = state.backendSource !== digest || image.status !== 0;
  const up = ["compose", "up", "-d", "--wait", "--wait-timeout", "90"];
  if (build) up.push("--build");
  up.push("broker", "backend");
  console.log(build ? "Đang chuẩn bị broker/backend..." : "Đang bật broker/backend đã cài...");
  command("docker", up, { env: environment, stdio: "inherit", failure: "Broker/backend chưa sẵn sàng. Xem lỗi Docker phía trên." });
  writeFileSync(statePath, JSON.stringify({ backendSource: digest, frontendLock: dependencies }, null, 2) + "\n");
  const url = "http://localhost:5173";
  console.log(`Dashboard: ${url} — tự kết nối, không cần nhập token.`);
  console.log("Ctrl+C dừng frontend. Dùng npm run dev:stop ở root để dừng broker/backend khi cần.");
  const args = [join(frontend, "node_modules/vite/bin/vite.js"), "--host", "localhost", "--port", "5173", "--strictPort"];
  if (!process.argv.includes("--no-open")) args.push("--open", url);
  const child = spawn(process.execPath, args, { cwd: frontend, env: environment, stdio: "inherit" });
  let stopping = false;
  const stop = () => { stopping = true; child.kill("SIGTERM"); };
  process.on("SIGINT", stop);
  process.on("SIGTERM", stop);
  child.once("error", () => { console.error("Không khởi động được Vite."); process.exitCode = 1; });
  await new Promise(resolveChild => child.once("close", code => {
    process.exitCode = stopping ? 0 : code ?? 1;
    resolveChild();
  }));
  process.removeListener("SIGINT", stop);
  process.removeListener("SIGTERM", stop);
}

main().catch(error => { console.error(error.message); process.exitCode = 1; });
