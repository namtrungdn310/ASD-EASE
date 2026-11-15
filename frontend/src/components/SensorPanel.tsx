import type { ReactNode } from "react";
import type { LucideIcon } from "lucide-react";
import type { QualityReading } from "../types/telemetry";
import { MetricQuality } from "./MetricQuality";
import { PanelTitle } from "./PanelTitle";

export function SensorPanel({ title, icon: Icon, value, unit, detail, quality, live = false, footer, children }: {
  title: string; icon: LucideIcon; value: string; unit: string;
  detail?: ReactNode; children: ReactNode; quality?: QualityReading; live?: boolean; footer?: ReactNode;
}) {
  return <section className="sensor-panel" aria-label={`${title}, đơn vị ${unit}`}>
    <div className="sensor-heading">
      <PanelTitle className="sensor-title" icon={Icon}>{title}</PanelTitle>
      <MetricQuality reading={quality} live={live} />
    </div>
    <div className="sensor-readings">
      <div className="sensor-summary">
        <p className="sensor-value" data-missing={value === "—"}><span>{value}</span><span className="sensor-unit"> {unit}</span></p>
        {detail && <div className="sensor-detail">{detail}</div>}
      </div>
    </div>
    <div className="sensor-visual">{children}</div>
    {footer && <p className="sensor-footer">{footer}</p>}
  </section>;
}
