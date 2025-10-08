import { StatCard } from "@/components/dashboard/stat-card";
import type { AdminSummaryMetric } from "@/services/dashboard-mappers";

type SummaryGridProps = {
  metrics: AdminSummaryMetric[];
};

const metricTone: Record<string, "default" | "warning" | "critical" | "success"> = {
  overdue_invoices: "warning",
  parts_to_reorder: "critical",
};

export function SummaryGrid({ metrics }: SummaryGridProps) {
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {metrics.map((metric) => (
        <StatCard
          key={metric.id}
          title={metric.label}
          value={metric.value}
          tone={metricTone[metric.id] ?? "default"}
        />
      ))}
    </div>
  );
}
