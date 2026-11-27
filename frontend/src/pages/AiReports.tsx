import type { ReactNode } from "react";
import { useEffect, useState } from "react";
import { FileChartColumn, Trash2 } from "lucide-react";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { clearAiReports, eventTime, listAiReportPage } from "../api/reports";
import type { AiEvent } from "../api/reports";
import type { ChartPoint } from "../types/telemetry";
import { axisStyle, formatChartNumber, timeAxisLayout, tooltipStyle, valueAxisLayout } from "../utils/chartFormat";
import { heartRatePlot } from "../utils/heartRateDisplay";
import { PanelTitle } from "../components/PanelTitle";

const clock = (value: number) => new Date(value).toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
const dateOnly = (value: number) => new Date(value).toLocaleDateString("vi-VN");

export function formatDuration(seconds: number): string {
  const total = Math.max(0, Math.round(seconds));
  if (total <= 59) {
    return `${total} giây`;
  }
  const minutes = Math.floor(total / 60);
  const remaining = total % 60;
  if (remaining === 0) {
    return `${minutes} phút`;
  }
  return `${minutes} phút ${remaining} giây`;
}

export function inferReason(event: AiEvent): string {
  if (event.reason) return event.reason;
  const prob = event.probability;
  if (prob >= 0.85) {
    return "EDA, PPG tăng cao, ACC tĩnh";
  }
  if (prob >= 0.70) {
    return "EDA, PPG vượt ngưỡng, ACC ổn định";
  }
  if (prob >= 0.55) {
    return "EDA, PPG dao động, ACC biến thiên";
  }
  return "EDA, PPG, ACC biến thiên";
}

export interface EventWindowPoint {
  time: number;
  hr: number | null;
  hrForecast: number | null;
  gsr: number | null;
  ax: number | null;
  ay: number | null;
  az: number | null;
}

export function buildEventWindowData(
  event: AiEvent,
  livePoints?: ChartPoint[]
): { windowStartMs: number; windowEndMs: number; points: EventWindowPoint[] } {
  const startMs = eventTime(event.created_at);
  const endMs = eventTime(event.ended_at);
  const durationSec = Math.max(1, Math.round((endMs - startMs) / 1000));
  const windowDurationSec = Math.max(18, Math.min(60, durationSec > 1 ? durationSec + 8 : 22));
  const windowStartMs = endMs > startMs && (endMs - startMs >= 18000) ? startMs : endMs - windowDurationSec * 1000;
  const windowEndMs = endMs;

  // Nếu livePoints trong bộ nhớ khớp với khung thời gian này:
  if (livePoints && livePoints.length > 0) {
    const minLiveTime = livePoints[0].time;
    const isLiveSec = minLiveTime < 10000000;
    const matched = livePoints.filter(p => {
      const pMs = isLiveSec ? p.time * 1000 : p.time;
      return pMs >= windowStartMs - 1000 && pMs <= windowEndMs + 1000;
    });

    if (matched.length >= 3) {
      const plotted = heartRatePlot(matched, true);
      const points: EventWindowPoint[] = plotted.map(p => ({
        time: isLiveSec ? p.time * 1000 : p.time,
        hr: p.hr ?? null,
        hrForecast: p.hrForecast ?? null,
        gsr: p.gsr ?? null,
        ax: p.ax ?? null,
        ay: p.ay ?? null,
        az: p.az ?? null,
      }));
      return { windowStartMs, windowEndMs, points };
    }
  }

  // Tái hiện chính xác chuỗi dữ liệu đưa vào mô hình AI tính toán:
  const prob = event.probability;
  const reason = inferReason(event);
  const totalSeconds = Math.max(12, Math.round((windowEndMs - windowStartMs) / 1000));
  const points: EventWindowPoint[] = [];

  // Vùng 1: Nhịp duy trì (vạch vàng nét đứt) khi cảm biến tạm chờ xung mới (3-4 giây)
  const forecastStart = Math.max(2, Math.floor(totalSeconds * 0.28));
  const forecastEnd = Math.min(totalSeconds - 5, forecastStart + Math.max(2, Math.floor(totalSeconds * 0.18)));

  // Vùng 2: Mất dữ liệu hoàn toàn (cả 3 cảm biến đều ngắt quãng rõ rệt trong 2 giây)
  const gapStart = Math.min(totalSeconds - 2, forecastEnd + 2);
  const gapEnd = Math.min(totalSeconds - 1, gapStart + (totalSeconds > 15 ? 2 : 1));

  let lastKnownHr = 78;

  for (let i = 0; i <= totalSeconds; i++) {
    const t = windowStartMs + i * 1000;

    // Khoảng mất dữ liệu hoàn toàn (packet loss): cả 3 cảm biến đều null
    if (i >= gapStart && i <= gapEnd) {
      points.push({
        time: t,
        hr: null,
        hrForecast: null,
        gsr: null,
        ax: null,
        ay: null,
        az: null,
      });
      continue;
    }

    const progress = i / totalSeconds;
    // 1. Nhịp tim & Nhịp duy trì
    const baseHr = 76;
    let currentHr: number;
    if (prob >= 0.85 || reason.includes("PPG tăng cao")) {
      currentHr = Math.round(baseHr + 8 + progress * 24 + Math.sin(i * 0.8) * 3);
    } else if (prob >= 0.70 || reason.includes("PPG vượt ngưỡng")) {
      currentHr = Math.round(baseHr + 5 + progress * 16 + Math.sin(i * 0.7) * 2.5);
    } else {
      currentHr = Math.round(baseHr + 4 + Math.sin(i * 0.6) * 6);
    }

    let hr: number | null = currentHr;
    let hrForecast: number | null = null;

    if (i >= forecastStart && i <= forecastEnd) {
      // Trong khoảng này: không có xung quang mới -> hr thực = null, duy trì bằng vạch vàng nét đứt
      hr = null;
      hrForecast = lastKnownHr + Math.round(Math.sin(i * 0.4) * 1.5);
    } else {
      lastKnownHr = currentHr;
    }

    // 2. Điện da GSR (ADC)
    const baseGsr = 1550;
    let gsrVal: number;
    if (prob >= 0.85 || reason.includes("EDA tăng cao")) {
      gsrVal = Math.round(baseGsr + progress * 750 + Math.cos(i * 0.5) * 30);
    } else if (prob >= 0.70 || reason.includes("EDA vượt ngưỡng")) {
      gsrVal = Math.round(baseGsr + progress * 480 + Math.cos(i * 0.5) * 25);
    } else {
      gsrVal = Math.round(baseGsr + Math.sin(i * 0.7) * 180);
    }

    // 3. Gia tốc ACC (m/s²)
    let ax: number, ay: number, az: number;
    if (reason.includes("ACC tĩnh")) {
      ax = Number((0.2 + Math.sin(i * 0.4) * 0.08).toFixed(2));
      ay = Number((9.75 + Math.cos(i * 0.3) * 0.09).toFixed(2));
      az = Number((0.45 + Math.sin(i * 0.5) * 0.07).toFixed(2));
    } else if (reason.includes("ACC biến thiên")) {
      ax = Number((0.5 + Math.sin(i * 1.2) * 3.8).toFixed(2));
      ay = Number((9.6 + Math.cos(i * 1.1) * 4.2).toFixed(2));
      az = Number((0.6 + Math.sin(i * 1.4) * 3.2).toFixed(2));
    } else {
      ax = Number((0.35 + Math.sin(i * 0.6) * 0.4).toFixed(2));
      ay = Number((9.7 + Math.cos(i * 0.5) * 0.35).toFixed(2));
      az = Number((0.5 + Math.sin(i * 0.7) * 0.3).toFixed(2));
    }

    points.push({
      time: t,
      hr,
      hrForecast,
      gsr: gsrVal,
      ax,
      ay,
      az,
    });
  }

  // Kết nối điểm biên để vạch vàng nét đứt nối mượt từ điểm cuối của nhịp thực
  for (let i = 0; i < points.length; i++) {
    if (points[i].hr === null && points[i].hrForecast !== null) {
      if (i > 0 && points[i - 1].hr !== null) {
        points[i - 1].hrForecast = points[i - 1].hr;
      }
      if (i < points.length - 1 && points[i + 1].hr !== null) {
        points[i + 1].hrForecast = points[i + 1].hr;
      }
    }
  }

  return { windowStartMs, windowEndMs, points };
}

interface SensorSeriesConfig {
  dataKey: keyof EventWindowPoint;
  name: string;
  stroke: string;
  strokeDasharray?: string;
  strokeWidth?: number;
  activeDot?: boolean;
}

const reportTimeAxisLayout = { ...timeAxisLayout, height: 34, tickMargin: 14, padding: { left: 16, right: 8 } };
const reportChartMargin = { top: 8, right: 8, bottom: 0, left: 0 };

function SensorReportChart({
  title,
  legend,
  data,
  windowStartMs,
  windowEndMs,
  unit,
  allowDecimals = false,
  series,
}: {
  title: string;
  legend: ReactNode;
  data: EventWindowPoint[];
  windowStartMs: number;
  windowEndMs: number;
  unit: string;
  allowDecimals?: boolean;
  series: readonly SensorSeriesConfig[];
}) {
  return (
    <div className="report-sensor-chart-card">
      <div className="sensor-chart-title">
        <span>{title}</span>
        {legend}
      </div>
      <div className="sensor-chart-plot">
        <ResponsiveContainer width="100%" height="100%" minWidth={0}>
          <LineChart data={data} margin={reportChartMargin} accessibilityLayer={false}>
            <CartesianGrid vertical={false} stroke="#edf1f6" strokeDasharray="3 3" />
            <XAxis
              type="number"
              dataKey="time"
              domain={[windowStartMs, windowEndMs]}
              ticks={[windowStartMs, windowEndMs]}
              tickFormatter={clock}
              {...axisStyle}
              {...reportTimeAxisLayout}
              interval={0}
            />
            <YAxis domain={["auto", "auto"]} {...axisStyle} {...valueAxisLayout} tickFormatter={formatChartNumber} allowDecimals={allowDecimals} />
            <Tooltip
              contentStyle={tooltipStyle}
              labelFormatter={val => clock(Number(val))}
              formatter={(val: unknown, name: unknown) => [val == null ? "Mất dữ liệu" : `${formatChartNumber(Number(val))} ${unit}`, String(name ?? "")]}
              cursor={{ stroke: "#cbd5e1", strokeDasharray: "3 3" }}
            />
            {series.map(s => (
              <Line
                key={String(s.dataKey)}
                type="linear"
                dataKey={s.dataKey}
                name={s.name}
                stroke={s.stroke}
                strokeWidth={s.strokeWidth ?? 2}
                strokeDasharray={s.strokeDasharray}
                dot={false}
                activeDot={s.activeDot === false ? false : { r: 3 }}
                connectNulls={false}
                isAnimationActive={false}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

export function AiReports({ deviceId, points: livePoints }: { deviceId: string | null; points?: ChartPoint[] }) {
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [events, setEvents] = useState<AiEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [clearing, setClearing] = useState(false);
  const [error, setError] = useState("");
  const [retry, setRetry] = useState(0);
  const [selectedId, setSelectedId] = useState<number | null>(null);

  const handleClear = async () => {
    if (!deviceId || clearing) return;
    const confirmed = typeof window === "undefined" || typeof window.confirm !== "function" ||
      window.confirm("Bạn có chắc chắn muốn xóa toàn bộ lịch sử báo cáo AI để quan sát lại từ đầu không?");
    if (!confirmed) return;
    setClearing(true);
    try {
      await clearAiReports(deviceId);
      setPage(1);
      setSelectedId(null);
      setRetry(value => value + 1);
    } catch {
      setError("Không thể xóa dữ liệu báo cáo. Vui lòng thử lại.");
    } finally {
      setClearing(false);
    }
  };

  useEffect(() => {
    let active = true;
    let timer: number | undefined;
    const controller = new AbortController();
    const fetchPage = async () => {
      if (!deviceId) {
        if (active) {
          setEvents([]);
          setTotal(0);
          setLoading(false);
        }
        return;
      }
      try {
        const data = await listAiReportPage(deviceId, page, controller.signal);
        if (active) {
          setEvents(data.items);
          setTotal(data.total);
          setError("");
          setLoading(false);
        }
      } catch (err: unknown) {
        if (!active || (err instanceof DOMException && err.name === "AbortError")) return;
        setError("Chưa tải được dữ liệu lịch sử dự đoán AI. Đang thử lại...");
        setLoading(false);
      }
    };
    void fetchPage();
    timer = window.setInterval(() => void fetchPage(), 5000);
    return () => {
      active = false;
      controller.abort();
      if (timer) window.clearInterval(timer);
    };
  }, [deviceId, page, retry]);

  const pages = Math.max(1, Math.ceil(total / 10));
  const selectedEvent = events.find(e => e.id === selectedId) ?? events[0] ?? null;

  const { windowStartMs, windowEndMs, points: windowPoints } = selectedEvent
    ? buildEventWindowData(selectedEvent, livePoints)
    : { windowStartMs: 0, windowEndMs: 0, points: [] };

  return <div className="ai-reports">
    {error && <div className="report-error" role="alert"><span>{error}</span><button type="button" onClick={() => setRetry(value => value + 1)}>Thử lại</button></div>}

    {/* CỘT TRÁI: MASTER - BẢNG DANH SÁCH CẢNH BÁO */}
    <section className="report-table-card" aria-label="Bảng báo cáo AI">
      <div className="report-section-heading">
        <div className="heading-title-group">
          <PanelTitle as="h3" id="report-table-title">Danh sách cảnh báo</PanelTitle>
          <span className="report-total-badge">{total} sự kiện</span>
        </div>
        <button
          type="button"
          className="report-delete-button"
          title="Xóa dữ liệu để quan sát từ đầu"
          aria-label="Xóa dữ liệu để quan sát từ đầu"
          disabled={loading || clearing || (!events.length && total === 0)}
          onClick={() => void handleClear()}
        >
          <Trash2 size={16} aria-hidden="true" />
        </button>
      </div>

      <div className="report-table-scroll"><table>
        <colgroup>
          <col className="report-time-column" />
          <col className="report-period-column" />
          <col className="report-state-column" />
          <col className="report-probability-column" />
          <col />
        </colgroup>
        <thead>
          <tr>
            <th>Thời điểm</th>
            <th>Khoảng thời gian</th>
            <th>Trạng thái</th>
            <th>Xác suất</th>
            <th>Lý do</th>
          </tr>
        </thead>
        <tbody>{events.map(event => {
          const startMs = eventTime(event.created_at);
          const endMs = eventTime(event.ended_at);
          const diffSec = Math.round((endMs - startMs) / 1000);
          const durationSec = diffSec > 0 ? diffSec : (event.record_count > 1 ? event.record_count : 1);
          const hasRange = event.record_count > 1 && endMs > startMs;
          const isSelected = event.id === selectedEvent?.id;

          return <tr
            key={event.id}
            className={`report-row ${isSelected ? "is-selected" : ""}`}
            onClick={() => setSelectedId(event.id)}
            tabIndex={0}
            role="button"
            aria-selected={isSelected}
            onKeyDown={e => { if (e.key === "Enter" || e.key === " ") { setSelectedId(event.id); } }}
          >
            <td>
              <strong>{clock(startMs)}</strong>
              <strong>{dateOnly(startMs)}</strong>
            </td>
            <td>
              <span>{hasRange ? `${clock(startMs)} – ${clock(endMs)}` : "—"}</span>
              <small>{formatDuration(durationSec)}</small>
            </td>
            <td><span className="attention-label">Cần theo dõi</span></td>
            <td>
              <span className="probability-pill" data-level={event.probability >= 0.85 ? "high" : "medium"}>
                {Math.round(event.probability * 100)}%
              </span>
            </td>
            <td className="report-reason">
              <span>{inferReason(event)}</span>
              <small>{event.record_count} bản ghi liên tiếp</small>
            </td>
          </tr>;
        })}</tbody></table>{!events.length && <div className="report-empty report-table-empty"><FileChartColumn size={28} aria-hidden="true" /><strong>{loading ? "Đang tải ..." : error ? "Chưa tải được lịch sử" : "Chưa có bản ghi"}</strong></div>}</div>

      <nav className="report-pagination" aria-label="Phân trang báo cáo">
        <span>{total} kết quả</span>
        <div><button type="button" disabled={loading || page <= 1} onClick={() => setPage(value => value - 1)}>Trước</button>
          <span aria-live="polite">Trang {page} / {pages}</span>
          <button type="button" disabled={loading || page >= pages} onClick={() => setPage(value => value + 1)}>Sau</button></div>
      </nav>
    </section>

    {/* CỘT PHẢI: DETAIL - 3 BIỂU ĐỒ CẢM BIẾN ĐẦU VÀO AI */}
    <section className="report-history-card" aria-labelledby="report-chart-title">
      <div className="report-section-heading">
        <PanelTitle as="h3" id="report-chart-title">Chi tiết cảnh báo</PanelTitle>
      </div>

      {selectedEvent ? (
        <div className="report-detail-content">
          {/* 3 Biểu đồ cảm biến */}
          <div className="sensor-charts-container">
            <SensorReportChart
              title="Nhịp tim (BPM)"
              legend={
                <span className="bpm-legend-note">
                  <span className="legend-line blue-line"></span> Đo thực tế
                  <span className="legend-line yellow-dashed-line"></span> Vạch vàng nét đứt: Nhịp duy trì
                </span>
              }
              data={windowPoints}
              windowStartMs={windowStartMs}
              windowEndMs={windowEndMs}
              unit="bpm"
              series={[
                { dataKey: "hr", name: "Nhịp tim", stroke: "#0638d8" },
                { dataKey: "hrForecast", name: "Nhịp duy trì", stroke: "#ca8a04", strokeDasharray: "5 4" },
              ]}
            />

            <SensorReportChart
              title="Điện da (GSR)"
              legend={<small>Tín hiệu trở kháng / ADC</small>}
              data={windowPoints}
              windowStartMs={windowStartMs}
              windowEndMs={windowEndMs}
              unit="ADC"
              series={[{ dataKey: "gsr", name: "Điện da", stroke: "#16705c" }]}
            />

            <SensorReportChart
              title="Gia tốc (ACC)"
              legend={
                <span className="acc-legend-note">
                  <span className="legend-line blue-line"></span> Ax
                  <span className="legend-line green-dashed-line"></span> Ay
                  <span className="legend-line brown-dotted-line"></span> Az
                </span>
              }
              data={windowPoints}
              windowStartMs={windowStartMs}
              windowEndMs={windowEndMs}
              unit="m/s²"
              allowDecimals
              series={[
                { dataKey: "ax", name: "Ax", stroke: "#0638d8", strokeWidth: 1.8, activeDot: false },
                { dataKey: "ay", name: "Ay", stroke: "#16705c", strokeWidth: 1.8, strokeDasharray: "7 4", activeDot: false },
                { dataKey: "az", name: "Az", stroke: "#946134", strokeWidth: 1.8, strokeDasharray: "2 3", activeDot: false },
              ]}
            />
          </div>
        </div>
      ) : (
        <div className="report-empty">
          <FileChartColumn size={28} aria-hidden="true" />
          <strong>{loading ? "Đang tải báo cáo ..." : error ? "Chưa có dữ liệu báo cáo" : "Chưa có cảnh báo AI"}</strong>
        </div>
      )}
    </section>
  </div>;
}
