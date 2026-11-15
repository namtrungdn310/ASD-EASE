import { useEffect, useState, type ReactNode } from "react";
import { openLocalSession } from "../utils/localSession";

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
        await openLocalSession(controller.signal);
        if (!active) return;
        setReady(true);
        setError("");
        // Cookie backend có hạn1 giờ; gia hạn và làm mới khi quay lại tab.
        timer = window.setTimeout(connect, 20 * 60 * 1000);
      } catch (failure) {
        if (!active) return;
        setError(failure instanceof Error && failure.message === "LOCALHOST"
          ? "Mở Dashboard tại http://localhost:5173."
          : "Mở Docker Desktop rồi thử lại.");
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
    <main className="session-shell">
      <section className="connection-card" aria-busy={!error || connecting}>
        <img src="/brand/asd-ease-logo.svg" alt="ASD-EASE" width={760} height={160} />
        <h1>{error ? "Chưa kết nối được" : "Đang mở bảng theo dõi"}</h1>
        <p role={error ? "alert" : "status"}>
          {error || "Vui lòng chờ trong giây lát."}
        </p>
        {error && <button type="button" disabled={connecting} onClick={() => setAttempt(value => value + 1)}
          className="primary-button">
          {connecting ? "Đang kết nối..." : "Thử lại"}
        </button>}
      </section>
    </main>
  );
}
