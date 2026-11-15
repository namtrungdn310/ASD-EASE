import { API_BASE_URL } from "../api";
import { isDeviceId } from "../api/devices";

const key = `asd-ease:device:${API_BASE_URL.replace(/\/$/, "")}`;
export function readDevicePreference(): { selected: string | null; ids: string[] } {
  try {
    const value = JSON.parse(window.localStorage.getItem(key) ?? "null");
    if (value?.source === "DEVICE" && isDeviceId(value.selected) && Array.isArray(value.ids)) {
      return { selected: value.selected, ids: [...new Set<string>([value.selected, ...value.ids.filter(isDeviceId)])].slice(0, 32) };
    }
  } catch { /* Storage bị chặn/hỏng không được cản dữ liệu thời gian thực. */ }
  const configured = import.meta.env.VITE_DEFAULT_DEVICE_ID;
  return { selected: null, ids: isDeviceId(configured) ? [configured] : [] };
}
export function rememberDevice(selected: string, ids: string[]) {
  try { window.localStorage.setItem(key, JSON.stringify({ source: "DEVICE", selected, ids: [selected, ...ids.filter(id => id !== selected)].slice(0, 32) })); }
  catch { /* Vẫn cho phép chọn thiết bị khi storage không khả dụng. */ }
}
