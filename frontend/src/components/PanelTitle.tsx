import type { ReactNode } from "react";
import type { LucideIcon } from "lucide-react";

export function PanelTitle({ children, icon: Icon, id, className = "", as: Tag = "h2" }: {
  children: ReactNode; icon?: LucideIcon; id?: string; className?: string; as?: "h2" | "h3";
}) {
  return <Tag id={id} className={`panel-title ${className}`.trim()}>
    {Icon && <Icon size={16} strokeWidth={1.75} aria-hidden="true" />}
    {children}
  </Tag>;
}
