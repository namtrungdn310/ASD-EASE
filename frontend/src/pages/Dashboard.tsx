import { useEffect, useState, type MouseEvent } from "react";
import { Activity, ChevronDown, CircleAlert, Monitor, FileChartColumn, PanelLeftClose, PanelLeftOpen, Waves } from "lucide-react";
import { DeviceStatus } from "../components/DeviceStatus";
import { PredictionPanel } from "../components/PredictionPanel";
import { AiReports } from "./AiReports";
import { HeartRateChart } from "../components/HeartRateChart";
import { GSRChart } from "../components/GSRChart";
import { ImuReadings } from "../components/ImuReadings";
import { SensorPanel } from "../components/SensorPanel";
import { SessionControl } from "../components/SessionControl";
import { DataLabelModal } from "../components/DataLabelModal";
import { useDatasetCapture } from "../hooks/useDatasetCapture";
import { useLiveTelemetry } from "../hooks/useLiveTelemetry";
import { formatChartTime } from "../utils/chartFormat";
import { heartRateDisplay } from "../utils/heartRateDisplay";

export function Dashboard() {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const { telemetry, points, connectionStatus, deviceIds, selectedDeviceId, setSelectedDeviceId,
    monitoring, connectionTimedOut, connectDevice, disconnectDevice, resetAiWindow } = useLiveTelemetry();
  const [page, setPage] = useState<"devices" | "reports">(() =>
    typeof window !== "undefined" && window.location.hash === "#reports" ? "reports" : "devices");
  useEffect(() => {
    const navigate = () => setPage(window.location.hash === "#reports" ? "reports" : "devices");
    window.addEventListener("hashchange", navigate);
    return () => window.removeEventListener("hashchange", navigate);
  }, []);
  const navigatePage = (event: MouseEvent<HTMLAnchorElement>, next: "devices" | "reports") => {
    if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
    event.preventDefault();
    window.location.hash = next;
    setPage(next);
  };
  const live = connectionStatus === "live";
  const { pendingCapture, dismissCapture, clearActiveCapture } = useDatasetCapture(telemetry, live);
  const connecting = monitoring && !connectionTimedOut && !live && connectionStatus !== "stale";
  const current = live ? telemetry : null;
  const chartScope = JSON.stringify([selectedDeviceId, telemetry?.session_id, telemetry?.data_origin, telemetry?.schema_version]);
  const hr = heartRateDisplay(telemetry, points, live);
  const display = (value: number | null | undefined, digits: number) => value == null ? "—" : value.toFixed(digits);

  return <div className="workspace-shell" data-sidebar-collapsed={sidebarCollapsed} data-origin={telemetry?.data_origin}>
    <a className="skip-link" href="#dashboard-content">Đến số đo</a>
    <aside className="workspace-sidebar" aria-label="Điều hướng chính">
      <div className="sidebar-top">
      <a className="sidebar-brand" href="#devices" aria-label="ASD-EASE · Thiết bị" onClick={event => navigatePage(event, "devices")}>
        <img src={sidebarCollapsed ? "/brand/asd-ease-mark.svg" : "/brand/asd-ease-logo.svg"} alt="ASD-EASE" width={760} height={160} />
      </a>
      </div>
      <nav className="sidebar-nav" id="sidebar-navigation">
        <a href="#devices" aria-label="Thiết bị" title={sidebarCollapsed ? "Thiết bị" : undefined} aria-current={page === "devices" ? "page" : undefined} onClick={event => navigatePage(event, "devices")}><Monitor size={18} aria-hidden="true" /><span>Thiết bị</span></a>
        <a href="#reports" aria-label="Báo cáo AI" title={sidebarCollapsed ? "Báo cáo AI" : undefined} aria-current={page === "reports" ? "page" : undefined} onClick={event => navigatePage(event, "reports")}><FileChartColumn size={18} aria-hidden="true" /><span>Báo cáo AI</span></a>
        <button className="sidebar-toggle" type="button" aria-label={sidebarCollapsed ? "Mở rộng sidebar" : "Thu gọn sidebar"}
          aria-expanded={!sidebarCollapsed} aria-controls="sidebar-navigation" title={sidebarCollapsed ? "Mở rộng" : undefined}
          onClick={() => setSidebarCollapsed(value => !value)}>
          {sidebarCollapsed ? <PanelLeftOpen size={18} aria-hidden="true" /> : <PanelLeftClose size={18} aria-hidden="true" />}
          <span>{sidebarCollapsed ? "Mở rộng" : "Thu gọn"}</span>
        </button>
      </nav>
      <section className="sidebar-device-info" aria-label="Thông tin thiết bị">
        <dl>
          <div><dt>Firmware</dt><dd title={telemetry?.firmware_version}>{telemetry?.firmware_version ?? "—"}</dd></div>
          <div><dt>Gói dữ liệu</dt><dd>{telemetry?.schema_version ?? "—"}</dd></div>
          <div><dt>Thời gian thiết bị</dt><dd>{telemetry ? formatChartTime(telemetry.timestamp_ms / 1000) : "—"}</dd></div>
        </dl>
        <p className="sidebar-footnote">Dữ liệu nghiên cứu.<br />Không dùng để chẩn đoán.</p>
      </section>
    </aside>
    <div className="workspace-main">
    <header className="app-header">
      <div className="page-width header-inner">
        <div className="header-status">
          <SessionControl deviceId={selectedDeviceId} origin={telemetry?.data_origin} live={live} telemetrySessionId={telemetry?.session_id ?? null} />
          <div className="device-actions">
            <div className="header-device" data-status={connectionStatus}>
              <div className="header-device-name" aria-hidden="true">
                <span>{selectedDeviceId ?? "Chưa có thiết bị"}</span>
              </div>
              <div className="device-control">
                <label htmlFor="live-device" className="sr-only">Thiết bị</label>
                <select id="live-device" value={selectedDeviceId ?? ""} disabled={!selectedDeviceId}
                  onChange={event => setSelectedDeviceId(event.target.value || null)} aria-describedby="device-selection-help">
                  {deviceIds.length === 0 && <option value="">Chưa có thiết bị</option>}
                  {deviceIds.map(deviceId => <option key={deviceId} value={deviceId}>{deviceId}</option>)}
                </select>
                <p id="device-selection-help" className="sr-only">Chọn thiết bị cần theo dõi. Chọn thiết bị chưa bắt đầu kết nối.</p>
              </div>
              {selectedDeviceId && <DeviceStatus status={connectionStatus} deviceId={selectedDeviceId}
                connecting={connecting} inline />}
              <ChevronDown className="header-device-arrow" size={14} aria-hidden="true" />
            </div>
            <button type="button" className="device-connect-button" disabled={!selectedDeviceId || connecting}
              aria-busy={connecting}
              data-connected={live} onClick={live ? disconnectDevice : connectDevice}>
              {live ? "Ngắt kết nối" : monitoring && (connectionTimedOut || connectionStatus === "stale") ? "Thử lại" : "Kết nối"}
            </button>
            {monitoring && connectionTimedOut && !live && <p className="connection-feedback" role="alert">
              Chưa nhận dữ liệu sau 15 giây. Kiểm tra ESP, Wi-Fi và cấu hình MQTT rồi thử lại.
            </p>}
          </div>
        </div>
      </div>
    </header>

    <main id="dashboard-content" className={`workspace-content ${page === "devices" ? "device-workspace" : "reports-workspace"}`} tabIndex={-1}>
      {page === "devices" ? <>
      <div className="sensor-grid" data-live={live}>
        <SensorPanel title={hr.estimated ? "Nhịp tim ước tính" : "Nhịp tim"} icon={Activity} value={display(hr.value, 1)} unit="bpm" quality={current?.schema_version === "1.2" ? current.signal_quality.hr : undefined} live={live}
          footer={hr.tracked ? <><CircleAlert size={14} aria-hidden="true" /><span>Nét đứt: nhịp duy trì tối đa 15 giây.</span></> : undefined}
          detail={hr.predicted ? <p className="sensor-note">Đang duy trì · {hr.ageSeconds} giây chờ xung mới.</p> :
            hr.held ? <p className="sensor-note">Nhận cách đây {hr.ageSeconds} giây · đang tìm lại nhịp.</p> :
            hr.estimated && !hr.tracked ? <p className="sensor-note">Bản demo · số đo tương đối.</p> : null}>
          <HeartRateChart key={chartScope} data={points} embedded tracked={hr.tracked} />
        </SensorPanel>
        <SensorPanel title="Điện da (GSR)" icon={Waves} value={display(telemetry?.gsr.raw, 0)} unit="ADC" quality={current?.schema_version === "1.2" ? current.signal_quality.gsr : undefined} live={live}>
          <GSRChart key={chartScope} data={points} embedded />
        </SensorPanel>
        <ImuReadings key={chartScope} telemetry={telemetry} points={points} live={live} />
      </div>

      <PredictionPanel telemetry={telemetry} points={points} live={live}
        onResetAi={selectedDeviceId ? async () => { clearActiveCapture(); await resetAiWindow(selectedDeviceId); } : undefined}
        onViewDetails={() => { window.location.hash = "reports"; setPage("reports"); }} />
      </> : <AiReports key={selectedDeviceId} deviceId={selectedDeviceId} points={points} />}
    </main>
    {pendingCapture && <DataLabelModal capture={pendingCapture} onClose={dismissCapture} />}
    </div>
  </div>;
}
