import test from "node:test";
import assert from "node:assert/strict";
import { prepareFirmware, selectEspPort } from "./dev-firmware.mjs";

const esp = { device: "COM7", vid: 0x303a, pid: 0x1001 };
test("chỉ chọn ESP, không nạp Bluetooth hoặc USB khác", () => {
  assert.equal(selectEspPort([{ device: "COM3", vid: null, pid: null }, esp]), "COM7");
  assert.equal(selectEspPort([{ device: "COM8", vid: 1234, pid: 5678 }]), null);
  assert.throws(() => selectEspPort([esp, { ...esp, device: "COM9" }]), /nhiều ESP/);
});
test("build trước, nạp đúng cổng, không chọn cổng khi build lỗi", () => {
  const calls = [];
  const command = (exe, args) => {
    calls.push(args);
    return args.at(-1).includes("comports()") ? JSON.stringify([esp]) : "";
  };
  prepareFirmware({ command, executable: "python", prefix: [], wifiConfigured: true });
  assert.equal(calls.length, 4);
  assert.ok(calls[1].includes("platformio"));
  assert.ok(!calls[1].includes("upload"));
  assert.deepEqual(calls[3].slice(-4), ["-t", "upload", "--upload-port", "COM7"]);
  let count = 0;
  assert.throws(() => prepareFirmware({ command: () => { if (++count === 2) throw new Error("build failed"); return ""; }, executable: "python", prefix: [], wifiConfigured: true }), /build failed/);
  assert.equal(count, 2);
});
test("thiếu USB vẫn build; thiếu Wi-Fi không nạp", () => {
  const calls = [];
  const command = (exe, args) => { calls.push(args); return "[]"; };
  prepareFirmware({ command, executable: "python", prefix: [], wifiConfigured: true });
  assert.equal(calls.length, 3);
  assert.ok(!calls.some(args => args.includes("upload")));
  calls.length = 0;
  prepareFirmware({ command, executable: "python", prefix: [], wifiConfigured: false });
  assert.equal(calls.length, 0);
});
