import { Activity, FlaskConical, Gauge, Waves } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { DeviceStatus } from "../components/DeviceStatus";
import { StateCard } from "../components/StateCard";
import { SignalQuality } from "../components/SignalQuality";
import { HeartRateChart } from "../components/HeartRateChart";
import { GSRChart } from "../components/GSRChart";
import { MovementChart } from "../components/MovementChart";
import { ProbabilityChart } from "../components/ProbabilityChart";
import { useLiveTelemetry } from "../hooks/useLiveTelemetry";

function display(
  value: number | null | undefined,
  suffix = ""
): string {
  return value == null ? "—" : `${value.toFixed(1)}${suffix}`;
}

export function Dashboard() {
  const {
    telemetry,
    points,
    connectionStatus,
    deviceIds,
    selectedDeviceId,
    setSelectedDeviceId,
  } = useLiveTelemetry();

  const isLive = connectionStatus === "live";
  const liveTelemetry = isLive ? telemetry : null;

  const metrics: {
    icon: LucideIcon;
    label: string;
    value: string;
  }[] = [
    {
      icon: Activity,
      label: "HR",
      value: display(telemetry?.hr_bpm, " bpm"),
    },
    {
      icon: Waves,
      label: "GSR",
      value: display(telemetry?.gsr.raw, " ADC"),
    },
    {
      icon: Gauge,
      label: "Movement",
      value: display(telemetry?.movement.score),
    },
    {
      icon: FlaskConical,
      label: "Session",
      value:
        telemetry === null
          ? "—"
          : telemetry.session_id ?? "Chưa gắn phiên",
    },
  ];

  return (
    <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
      <header className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="eyebrow text-teal-700">
            Local engineering monitor
          </p>

          <h1 className="mt-1 text-3xl font-bold tracking-tight text-slate-950">
            ASD Edge AI
          </h1>

          <p className="mt-2 max-w-2xl text-sm text-slate-600">
            Dashboard hiển thị trạng thái kỹ thuật từ thiết bị.
            Không phải công cụ chẩn đoán y khoa.
          </p>
        </div>

        {telemetry?.data_origin === "SYNTHETIC" && (
          <div className="flex items-center gap-2 self-start rounded-full border border-violet-200 bg-violet-50 px-4 py-2 text-sm font-bold text-violet-800">
            <FlaskConical size={17} aria-hidden="true" />
            SYNTHETIC DATA
          </div>
        )}
      </header>

      <section
        className="card mb-4"
        aria-label="Lựa chọn thiết bị"
      >
        <label
          htmlFor="live-device"
          className="block text-sm font-semibold text-slate-900"
        >
          Thiết bị đang xem
        </label>

        <select
          id="live-device"
          value={selectedDeviceId ?? ""}
          disabled={deviceIds.length === 0}
          onChange={(event) =>
            setSelectedDeviceId(event.target.value || null)
          }
          aria-describedby="live-device-help"
          className="mt-2 min-h-11 w-full min-w-0 rounded-lg border border-slate-300 bg-white px-3 py-2 text-base text-slate-900 disabled:cursor-not-allowed disabled:bg-slate-100 disabled:text-slate-600 sm:max-w-sm"
        >
          {deviceIds.length === 0 && (
            <option value="">Chưa nhận dữ liệu thiết bị</option>
          )}

          {deviceIds.map((deviceId) => (
            <option key={deviceId} value={deviceId}>
              {deviceId}
            </option>
          ))}
        </select>

        <p
          id="live-device-help"
          className="mt-2 text-sm text-slate-600"
        >
          Hiển thị phiên nhận gần nhất của thiết bị được chọn.
          Đổi phiên hoặc nguồn dữ liệu sẽ bắt đầu lại biểu đồ.
        </p>
      </section>

      {!isLive && telemetry !== null && (
        <aside className="mb-4 rounded-xl border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-900">
          <p className="font-semibold">
            Đang hiển thị dữ liệu nhận trước đó
          </p>
          <p className="mt-1">
            Các chỉ số và biểu đồ bên dưới không phản ánh hiện tại.
            Dự đoán và chất lượng tín hiệu hiện tại chỉ hiển thị
            sau khi nhận được dữ liệu mới.
          </p>
        </aside>
      )}

      <div className="grid gap-4 md:grid-cols-3">
        <DeviceStatus
          status={connectionStatus}
          deviceId={selectedDeviceId ?? undefined}
        />

        {liveTelemetry !== null ? (
          <StateCard
            state={liveTelemetry.prediction.state}
            probability={liveTelemetry.prediction.probability}
          />
        ) : (
          <section className="card">
            <p className="eyebrow">Trạng thái kỹ thuật</p>
            <p className="mt-2 font-semibold text-slate-900">
              Chưa có dữ liệu hiện tại
            </p>
            <p className="mt-1 text-sm text-slate-600">
              Không dùng dự đoán cũ để kết luận trạng thái hiện tại.
            </p>
          </section>
        )}

        {liveTelemetry !== null ? (
          <SignalQuality quality={liveTelemetry.signal_quality} />
        ) : (
          <section className="card">
            <p className="eyebrow">Chất lượng tín hiệu</p>
            <p className="mt-2 font-semibold text-slate-900">—</p>
            <p className="mt-1 text-sm text-slate-600">
              Chưa có mẫu mới để hiển thị chất lượng tín hiệu.
            </p>
          </section>
        )}
      </div>

      <section className="my-4" aria-labelledby="metrics-heading">
        <h2
          id="metrics-heading"
          className="mb-3 text-sm font-semibold text-slate-700"
        >
          {isLive
            ? "Chỉ số đang cập nhật"
            : "Chỉ số nhận gần nhất — không phải dữ liệu trực tiếp"}
        </h2>

        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          {metrics.map(({ icon: Icon, label, value }) => (
            <div className="metric min-w-0" key={label}>
              <Icon
                size={18}
                className="shrink-0 text-teal-700"
                aria-hidden="true"
              />
              <div className="min-w-0">
                <p className="eyebrow">{label}</p>
                <p className="mt-0.5 break-all font-mono font-semibold text-slate-900">
                  {value}
                </p>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section aria-labelledby="charts-heading">
        <h2
          id="charts-heading"
          className="font-semibold text-slate-900"
        >
          Biểu đồ dữ liệu gần nhất
        </h2>

        <p className="mb-4 mt-1 text-sm text-slate-600">
          Giữ tối đa 60 điểm của phiên và nguồn đang hiển thị.
          {!isLive && " Luồng hiện không live; biểu đồ có thể là dữ liệu cũ."}
        </p>

        <div className="grid gap-4 lg:grid-cols-2">
          <HeartRateChart data={points} />
          <GSRChart data={points} />
          <MovementChart data={points} />
          <ProbabilityChart data={points} />
        </div>
      </section>

      <footer className="mt-6 flex flex-wrap gap-x-6 gap-y-2 border-t border-slate-200 pt-4 text-xs text-slate-600">
        <span className="break-all">
          Firmware: {telemetry?.firmware_version ?? "—"}
        </span>
        <span className="break-all">
          Model: {telemetry?.model_version ?? "—"}
        </span>
        <span>Schema: {telemetry?.schema_version ?? "—"}</span>
      </footer>
    </main>
  );
}