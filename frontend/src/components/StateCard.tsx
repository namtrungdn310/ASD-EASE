import type {EngineeringState} from "../types/telemetry";

const styles: Record<EngineeringState, string> = {NORMAL: "bg-emerald-50 text-emerald-800 border-emerald-200", ATTENTION: "bg-orange-50 text-orange-800 border-orange-200", UNCERTAIN: "bg-amber-50 text-amber-800 border-amber-200", CALIBRATING: "bg-blue-50 text-blue-800 border-blue-200"};

export function StateCard({state = "CALIBRATING", probability}: {state?: EngineeringState; probability?: number | null}) {
  return <section className={`card border ${styles[state]}`}><p className="eyebrow opacity-70">Trạng thái kỹ thuật</p><div className="mt-1 flex items-end justify-between gap-4"><p className="text-2xl font-bold tracking-tight">{state}</p><p className="font-mono text-sm">{probability == null ? "—" : `${Math.round(probability * 100)}%`}</p></div></section>;
}

