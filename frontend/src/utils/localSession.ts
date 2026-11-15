/** Chỉ dùng trong dev: browser nhận cookie HttpOnly, không đọc token. */
export async function openLocalSession(parentSignal: AbortSignal): Promise<void> {
  const request = new AbortController();
  const abort = () => request.abort();
  parentSignal.addEventListener("abort", abort, { once: true });
  if (parentSignal.aborted) abort();
  const timeout = window.setTimeout(abort, 8000);
  try {
    const response = await fetch("/__local/session", {
      method: "POST", credentials: "include", signal: request.signal,
    });
    const result = await response.json();
    if (request.signal.aborted) throw new DOMException("Session request aborted", "AbortError");
    if (!response.ok || result.authenticated !== true) {
      throw new Error(result.error === "OPEN_LOCALHOST" ? "LOCALHOST" : "SERVICE");
    }
  } finally {
    window.clearTimeout(timeout);
    parentSignal.removeEventListener("abort", abort);
  }
}
