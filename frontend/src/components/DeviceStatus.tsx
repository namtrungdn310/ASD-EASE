import {
  Clock3,
  Radio,
  TriangleAlert,
  WifiOff,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import type { ConnectionStatus } from "../types/connection";

interface DeviceStatusProps {
  status?: ConnectionStatus;
  deviceId?: string;

  /** Tạm tương thích với Dashboard cũ; ưu tiên status nếu có. */
  connected?: boolean;
}

interface StatusConfig {
  label: string;
  description: string;
  icon: LucideIcon;
  iconClassName: string;
  dotClassName: string;
}

const STATUS_CONFIG: Record<ConnectionStatus, StatusConfig> = {
  backend_disconnected: {
    label: "Mất kết nối backend",
    description:
      "Đang thử kết nối lại. Dữ liệu cũ không phản ánh hiện tại.",
    icon: WifiOff,
    iconClassName: "bg-slate-100 text-slate-700",
    dotClassName: "bg-slate-500",
  },
  waiting: {
    label: "Đang chờ dữ liệu",
    description:
      "Backend đã kết nối; đang chờ mẫu mới từ thiết bị.",
    icon: Clock3,
    iconClassName: "bg-sky-100 text-sky-800",
    dotClassName: "bg-sky-600",
  },
  live: {
    label: "Dữ liệu đang cập nhật",
    description: "Backend đã kết nối và dữ liệu còn mới.",
    icon: Radio,
    iconClassName: "bg-emerald-100 text-emerald-800",
    dotClassName: "bg-emerald-600",
  },
  stale: {
    label: "Dữ liệu đã cũ",
    description:
      "Backend vẫn kết nối, nhưng đã quá ngưỡng chờ mẫu mới.",
    icon: TriangleAlert,
    iconClassName: "bg-amber-100 text-amber-900",
    dotClassName: "bg-amber-600",
  },
};

export function DeviceStatus({
  status,
  deviceId,
  connected,
}: DeviceStatusProps) {
  const resolvedStatus =
    status ??
    (connected ? "live" : "backend_disconnected");

  const config = STATUS_CONFIG[resolvedStatus];
  const Icon = config.icon;

  return (
    <section
      className="card flex items-start gap-3"
      aria-label="Trạng thái kết nối và dữ liệu"
    >
      <span
        className={`icon-shell shrink-0 ${config.iconClassName}`}
      >
        <Icon size={20} aria-hidden="true" />
      </span>

      <div className="min-w-0 flex-1">
        <p className="eyebrow">Kết nối dữ liệu</p>

        <div
          role="status"
          aria-live="polite"
          aria-atomic="true"
        >
          <p className="mt-1 font-semibold text-slate-900">
            {config.label}
          </p>

          <p className="mt-1 text-sm text-slate-600">
            {config.description}
          </p>
        </div>

        <p className="mt-2 break-all font-mono text-xs text-slate-600">
          {deviceId ?? "Chưa có thiết bị"}
        </p>
      </div>

      <span
        className={`status-dot mt-1 shrink-0 ${config.dotClassName}`}
        aria-hidden="true"
      />
    </section>
  );
}