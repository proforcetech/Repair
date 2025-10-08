"use client";

import { JobTimersCard } from "@/components/dashboard/job-timers-card";
import { useTechnicianDashboard } from "@/hooks/use-dashboard-data";
import { useOverdueInvoices, useLowStockParts } from "@/hooks/use-dashboard-data";

export function TechnicianDashboardView() {
  const { data: dashboard, isLoading: loadingDashboard } = useTechnicianDashboard(true);
  const { data: overdueInvoices } = useOverdueInvoices();
  const { data: lowStockParts } = useLowStockParts();

  return (
    <div className="space-y-6">
      <header className="space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight text-foreground">Technician dashboard</h1>
        <p className="text-sm text-muted-foreground">
          Monitor active jobs, timers, and open invoices assigned to your bay.
        </p>
      </header>
      {loadingDashboard ? (
        <div className="h-48 animate-pulse rounded-xl bg-muted/40" />
      ) : (
        <JobTimersCard dashboard={dashboard} />
      )}
      <div className="grid gap-4 lg:grid-cols-2">
        <div>
          <h2 className="mb-2 text-sm font-semibold text-foreground">Overdue invoices snapshot</h2>
          <p className="text-xs text-muted-foreground">
            {overdueInvoices && overdueInvoices.length > 0
              ? `${overdueInvoices.length} invoices require follow-up.`
              : "No overdue invoices linked to your work orders."}
          </p>
        </div>
        <div>
          <h2 className="mb-2 text-sm font-semibold text-foreground">Low stock hints</h2>
          <p className="text-xs text-muted-foreground">
            {lowStockParts && lowStockParts.length > 0
              ? `${lowStockParts.length} parts are below threshold.`
              : "All assigned parts are adequately stocked."}
          </p>
        </div>
      </div>
    </div>
  );
}
