import { formatDistanceToNow } from "date-fns";

import type {
  AdminSummaryFilters,
  AdminSummaryResponse,
  InventoryPart,
  PaymentInvoiceSummary,
  RawJobTimer,
  TechnicianDashboardResponse,
  TechnicianPartsSummaryResponse,
} from "@/services/dashboard";

export interface JobTimerView {
  id: string;
  jobId: string;
  jobTitle: string;
  startedAt: Date;
  elapsedSeconds: number;
  elapsedLabel: string;
  progressPercent: number;
}

export interface TechnicianDashboardView {
  assignedJobs: Array<{
    id: string;
    title: string;
    status: string;
    dueDateLabel: string;
  }>;
  activeTimers: JobTimerView[];
  activeTimerCount: number;
}

export interface AdminSummaryMetric {
  id: string;
  label: string;
  value: number;
}

export interface OverdueInvoiceRow {
  id: string;
  status: string;
  total: number;
}

export interface LowStockPartRow {
  id: string;
  sku: string;
  description: string;
  quantity: number;
  reorderMin: number;
  suggestedOrder: number;
}

export interface DashboardNotification {
  id: string;
  title: string;
  description: string;
  severity: "info" | "warning" | "success" | "muted";
}

export function mapJobTimer(timer: RawJobTimer, index: number): JobTimerView {
  const startedAt = new Date(timer.startedAt);
  const elapsedSeconds = timer.elapsedSeconds ?? 0;
  const hoursBudget = 8 * 3600;
  const progress = Math.min(100, Math.round((elapsedSeconds / hoursBudget) * 100));

  return {
    id: `${timer.jobId}-${index}`,
    jobId: timer.jobId,
    jobTitle: timer.jobTitle ?? `Job ${timer.jobId.slice(0, 8)}`,
    startedAt,
    elapsedSeconds,
    elapsedLabel: formatDistanceToNow(startedAt, { addSuffix: true }),
    progressPercent: Number.isFinite(progress) ? progress : 0,
  };
}

export function mapTechnicianDashboard(
  data: TechnicianDashboardResponse,
): TechnicianDashboardView {
  const activeTimers = (data.active_timers ?? []).map(mapJobTimer);
  const assignedJobs = (data.assigned_jobs ?? []).map((job) => ({
    id: job.id,
    title: job.title ?? `Job ${job.id.slice(0, 6)}`,
    status: job.status ?? "UNKNOWN",
    dueDateLabel: job.dueDate
      ? `Due ${formatDistanceToNow(new Date(job.dueDate), { addSuffix: true })}`
      : job.promiseDate
        ? `Promise ${formatDistanceToNow(new Date(job.promiseDate), { addSuffix: true })}`
        : "No due date",
  }));

  return {
    activeTimers,
    assignedJobs,
    activeTimerCount: activeTimers.length,
  };
}

export function mapAdminSummary(data: AdminSummaryResponse): AdminSummaryMetric[] {
  return [
    { id: "open_jobs", label: "Open Jobs", value: data.open_jobs ?? 0 },
    {
      id: "overdue_invoices",
      label: "Overdue Invoices",
      value: data.overdue_invoices ?? 0,
    },
    {
      id: "parts_to_reorder",
      label: "Parts to Reorder",
      value: data.parts_to_reorder ?? 0,
    },
  ];
}

export function mapOverdueInvoices(data: PaymentInvoiceSummary[]): OverdueInvoiceRow[] {
  return (data ?? []).map((invoice) => ({
    id: invoice.id,
    status: invoice.status,
    total: Number(invoice.total ?? 0),
  }));
}

export function mapLowStockParts(parts: InventoryPart[]): LowStockPartRow[] {
  return (parts ?? [])
    .filter((part) => typeof part.reorderMin === "number" && part.reorderMin !== null)
    .filter((part) => part.quantity < Number(part.reorderMin))
    .map((part) => {
      const reorderMin = Number(part.reorderMin ?? 0);
      const suggested = Math.max(reorderMin * 2 - Number(part.quantity ?? 0), 0);
      return {
        id: part.id,
        sku: part.sku,
        description: part.description ?? "Unlabeled part",
        quantity: Number(part.quantity ?? 0),
        reorderMin,
        suggestedOrder: suggested,
      };
    });
}

export function buildSummaryCsv(
  metrics: AdminSummaryMetric[],
  filters: AdminSummaryFilters,
): string {
  const headers = ["Metric", "Value"];
  const filterRows = Object.entries(filters)
    .filter(([, value]) => value !== undefined && value !== "")
    .map(([key, value]) => [
      `Filter: ${key.replace(/[A-Z]/g, (match) => ` ${match.toLowerCase()}`)}`,
      Array.isArray(value) ? value.join(", ") : String(value),
    ]);
  const metricRows = metrics.map((metric) => [metric.label, String(metric.value)]);
  const rows = [headers, ...filterRows, ...metricRows];
  return rows.map((row) => row.map((cell) => `"${cell.replace(/"/g, '""')}"`).join(",")).join("\n");
}

export function mapTechnicianPartsSummary(
  summary: TechnicianPartsSummaryResponse,
): DashboardNotification[] {
  if (!summary) {
    return [];
  }

  return [
    {
      id: "parts-today",
      title: "Parts received today",
      description: `${summary.parts_received_today} items scanned`,
      severity: summary.parts_received_today > 0 ? "success" : "muted",
    },
    {
      id: "parts-week",
      title: "Parts received this week",
      description: `${summary.parts_received_week} items scanned`,
      severity: "info",
    },
    {
      id: "events-today",
      title: "Inventory events today",
      description: `${summary.events_today} adjustments recorded`,
      severity: summary.events_today > 5 ? "warning" : "muted",
    },
  ];
}
