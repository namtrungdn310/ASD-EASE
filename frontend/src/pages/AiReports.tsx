import { useEffect, useState } from "react";
import { FileChartColumn, CircleAlert } from "lucide-react";
import { CartesianGrid, ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis } from "recharts";
import { eventTime, listAiReportPage } from "../api/reports";
import type { AiEvent } from "../api/reports";
import { axisStyle, tooltipStyle } from "../utils/chartFormat";
import { PanelTitle } from "../components/PanelTitle";

const clock = (value: number) => new Date(value).toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
const dateTime = (value: string) => new Date(eventTime(value)).toLocaleString("vi-VN");

export function AiReports({ deviceId }: { deviceId: string | null }) {
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [events, setEvents] = useState<AiEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    let active = true;
    let timer: number | undefined;
    let controller: AbortController | undefined;
    setEvents([]); setLoading(true); setError("");
    const poll = async () => {
      if (!deviceId) { setLoading(false); return; }
      controller = new AbortController();
      const timeout = window.setTimeout(() => controller?.abort(), 8000);
      try {
        const result = await listAiReportPage(deviceId, page, controller.signal);
        const lastPage = Math.max(1, Math.ceil(result.total / 10));
        if (active && page > lastPage) { setPage(lastPage); return; }
        if (active) { setEvents(result.items); setTotal(result.total); setError(""); }
      } catch {
        if (active) setError("Chưa tải được báo cáo. Dữ liệu hiển thị có thể chưa cập nhật.");
      } finally {
        window.clearTimeout(timeout);
        if (active) { setLoading(false); timer = window.setTimeout(poll, 10000); }
      }
    };
    void poll();
    return () => { active = false; controller?.abort(); if (timer !== undefined) window.clearTimeout(timer); };
  }, [deviceId, retry, page]);
  const pages = Math.max(1, Math.ceil(total / 10));
  const chartData = [...events].sort((a, b) => eventTime(a.created_at) - eventTime(b.created_at))
    .map(event => ({ time: eventTime(event.created_at), probability: Math.round(event.probability * 100) }));
  return <div className="ai-reports">
    {error && <div className="report-error" role="alert"><span>{error}</span><button type="button" onClick={() => setRetry(value => value + 1)}>Thử lại</button></div>}
    <section className="report-history-card" aria-labelledby="report-chart-title">
      <div className="report-section-heading"><PanelTitle as="h3" id="report-chart-title">Lịch sử dự đoán AI</PanelTitle><span>Xác suất (%)</span></div>
      {events.length ? <div className="report-chart" role="group" aria-label="Xác suất tại các thời điểm cần chú ý">
        <ResponsiveContainer width="100%" height="100%"><ScatterChart margin={{ top: 12, right: 20, bottom: 8, left: 0 }} accessibilityLayer>
          <CartesianGrid vertical={false} stroke="#e8edf4" strokeDasharray="3 4" />
          <XAxis {...axisStyle} type="number" dataKey="time" domain={["dataMin", "dataMax"]} tickFormatter={clock} minTickGap={40} tickMargin={12} height={38} />
          <YAxis {...axisStyle} type="number" dataKey="probability" domain={[0, 100]} ticks={[0, 50, 100]} width={42} />
          <Tooltip contentStyle={tooltipStyle} formatter={(value, name) => name === "time" ? [new Date(Number(value)).toLocaleString("vi-VN"), "Thời điểm"] : [`${value}%`, "Xác suất"]} />
          <Scatter data={chartData} fill="#b66b21" isAnimationActive={false} />
        </ScatterChart></ResponsiveContainer>
      </div> : <div className="report-empty"><FileChartColumn size={28} aria-hidden="true" /><strong>{loading ? "Đang tải báo cáo ..." : error ? "Chưa có dữ liệu báo cáo" : "Chưa có cảnh báo AI"}</strong></div>}
    </section>
    <section className="report-table-card" aria-label="Bảng báo cáo AI">
      <div className="report-table-scroll"><table>
        <colgroup><col className="report-time-column" /><col className="report-period-column" /><col className="report-state-column" /><col className="report-probability-column" /><col /></colgroup>
        <thead><tr><th>Thời điểm</th><th>Khoảng thời gian</th><th>Trạng thái cảnh báo</th><th>Xác suất</th><th>Lý do</th></tr></thead>
        <tbody>{events.map(event => <tr key={event.id}>
          <td><strong>{dateTime(event.created_at)}</strong></td>
          <td>{event.record_count > 1 && eventTime(event.ended_at) > eventTime(event.created_at)
            ? `${clock(eventTime(event.created_at))} – ${clock(eventTime(event.ended_at))}` : "—"}</td>
          <td><span className="attention-label"><CircleAlert size={14} aria-hidden="true" />Cần chú ý</span></td>
          <td>{Math.round(event.probability * 100)}%</td>
          <td className="report-reason"><span>{event.reason ?? "—"}</span><small>{event.record_count} bản ghi</small></td>
        </tr>)}</tbody></table>{!events.length && <div className="report-empty report-table-empty"><FileChartColumn size={28} aria-hidden="true" /><strong>{loading ? "Đang tải ..." : error ? "Chưa tải được lịch sử" : "Chưa có bản ghi"}</strong></div>}</div>
      <nav className="report-pagination" aria-label="Phân trang báo cáo">
        <span>{total} kết quả</span>
        <div><button type="button" disabled={loading || page <= 1} onClick={() => setPage(value => value - 1)}>Trước</button>
          <span aria-live="polite">Trang {page} / {pages}</span>
          <button type="button" disabled={loading || page >= pages} onClick={() => setPage(value => value + 1)}>Sau</button></div>
      </nav>
    </section>
  </div>;
}
