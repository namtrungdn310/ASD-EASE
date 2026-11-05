import { useEffect, useState, type ReactNode } from "react";

/** Chỉ dùng bởi Vite dev. Production không có endpoint tự mở phiên. */
export function LocalConnection({ children }: { children: ReactNode }) {
  const [ready, setReady] = useState(false);
  const [error, setError] = useState("");
  const [connecting, setConnecting] = useState(false);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let active = true;
    let pending = false;
    let timer: number | undefined;
    const controller = new AbortController();
    const connect = async () => {
      if (pending || !active) return;
      pending = true;
      setConnecting(true);
      if (timer !== undefined) window.clearTimeout(timer);
      try {
        const response = await fetch("/__local/session", {
          method: "POST", credentials: "include", signal: controller.signal,
        });
        const result = await response.json();
        if (!response.ok || result.authenticated !== true) {
          throw new Error(result.error === "OPEN_LOCALHOST" ? "LOCALHOST" : "SERVICE");
        }
        if (!active) return;
        setReady(true);
        setError("");
        // Cookie backend có hạn1 giờ; gia hạn và làm mới khi quay lại tab.
        timer = window.setTimeout(connect, 20 * 60 * 1000);
      } catch (failure) {
        if (!active) return;
        setError(failure instanceof Error && failure.message === "LOCALHOST"
          ? "Mở Dashboard tại http://localhost:5173."
          : "Chưa kết nối được dịch vụ local. Kiểm tra Docker Desktop đang chạy rồi thử lại.");
        timer = window.setTimeout(connect, 3000);
      } finally {
        pending = false;
        if (active) setConnecting(false);
      }
    };
    const resume = () => { if (document.visibilityState === "visible") void connect(); };
    void connect();
    document.addEventListener("visibilitychange", resume);
    return () => {
      active = false;
      controller.abort();
      if (timer !== undefined) window.clearTimeout(timer);
      document.removeEventListener("visibilitychange", resume);
    };
  }, [attempt]);

  if (ready) return children;
  return (
    <main className="mx-auto max-w-lg px-4 py-12">
      <section className="card" aria-busy={!error || connecting}>
        <img src="/brand/asd-ease-logo.svg" alt="ASD-EASE" width={760} height={160} className="mb-6 h-auto w-60 max-w-full" />
        <h1 className="text-xl font-bold text-slate-900">Đang kết nối dữ liệu thiết bị</h1>
        <p className="mt-3 text-sm text-slate-600" role={error ? "alert" : "status"}>
          {error || "Đang chuẩn bị kết nối. Dashboard sẽ tự hiển thị khi sẵn sàng."}
        </p>
        {error && <button type="button" disabled={connecting} onClick={() => setAttempt(value => value + 1)}
          className="mt-5 min-h-11 rounded-lg bg-blue-700 px-4 py-2 font-semibold text-white hover:bg-blue-800 disabled:cursor-wait disabled:opacity-60">
          {connecting ? "Đang kết nối..." : "Thử lại"}
        </button>}
      </section>
    </main>
  );
}
