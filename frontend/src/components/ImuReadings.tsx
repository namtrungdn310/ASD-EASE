import { MoveUpRight, Rotate3D } from "lucide-react";
import type { AxisVector, ChartPoint, Telemetry } from "../types/telemetry";
import { SensorPanel } from "./SensorPanel";
import { ImuChart } from "./ImuChart";

function AxisValues({ prefix, values }: { prefix: string; values?: AxisVector | null }) {
  return <dl className="axis-readings">
    {(["x", "y", "z"] as const).map(axis => <div key={axis} data-axis={axis}>
      <dt>{prefix}{axis}</dt><dd>{values == null ? "—" : values[axis].toFixed(2)}</dd>
    </div>)}
  </dl>;
}
export function ImuReadings({ telemetry, points = [], live = false }: { telemetry: Telemetry | null; points?: ChartPoint[]; live?: boolean }) {
  const movement = telemetry && telemetry.schema_version !== "1.0" ? telemetry.movement : null;
  const acceleration = movement?.acceleration;
  const rotation = movement?.angular_velocity;
  const magnitude = (values?: AxisVector | null) => values == null ? "—" : Math.hypot(values.x, values.y, values.z).toFixed(2);
  return <>
    <SensorPanel title="Gia tốc" icon={MoveUpRight} value={magnitude(acceleration)} unit="m/s²"
      quality={telemetry?.schema_version === "1.2" ? telemetry.signal_quality.acceleration : undefined} live={live}
      detail={<><span className="sr-only">Độ lớn tổng hợp. </span><AxisValues prefix="A" values={acceleration} /></>}>
      <ImuChart data={points} kind="acceleration" embedded />
    </SensorPanel>
    <SensorPanel title="Tốc độ xoay" icon={Rotate3D} value={magnitude(rotation)} unit="°/s"
      quality={telemetry?.schema_version === "1.2" ? telemetry.signal_quality.rotation : undefined} live={live}
      detail={<><span className="sr-only">Độ lớn tổng hợp. </span><AxisValues prefix="G" values={rotation} /></>}>
      <ImuChart data={points} kind="angular_velocity" embedded />
    </SensorPanel>
  </>;
}
