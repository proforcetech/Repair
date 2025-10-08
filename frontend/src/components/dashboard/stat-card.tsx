import { ReactNode } from "react";
import { clsx } from "clsx";

type StatCardProps = {
  title: string;
  value: ReactNode;
  hint?: ReactNode;
  icon?: ReactNode;
  tone?: "default" | "success" | "warning" | "critical";
};

const toneClasses: Record<NonNullable<StatCardProps["tone"]>, string> = {
  default: "border-border/70",
  success: "border-emerald-500/30 bg-emerald-500/5",
  warning: "border-amber-500/30 bg-amber-500/5",
  critical: "border-red-500/30 bg-red-500/5",
};

export function StatCard({ title, value, hint, icon, tone = "default" }: StatCardProps) {
  return (
    <div
      className={clsx(
        "flex flex-col gap-2 rounded-xl border bg-background/80 p-4 shadow-sm",
        toneClasses[tone],
      )}
    >
      <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
        {icon && <span className="text-foreground/70">{icon}</span>}
        {title}
      </div>
      <div className="text-2xl font-semibold tracking-tight text-foreground">{value}</div>
      {hint && <div className="text-xs text-muted-foreground">{hint}</div>}
    </div>
  );
}
