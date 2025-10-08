"use client";

import { useMemo, useState } from "react";

import { LowStockPartsTable } from "@/components/dashboard/low-stock-parts-table";
import { OverdueInvoicesTable } from "@/components/dashboard/overdue-invoices-table";
import { SummaryFilters, type TechnicianOption } from "@/components/dashboard/summary-filters";
import { SummaryGrid } from "@/components/dashboard/summary-grid";
import {
  useAdminSummary,
  useLowStockParts,
  useOverdueInvoices,
  useSummaryCsv,
  useTechnicianOptions,
} from "@/hooks/use-dashboard-data";
import type { AdminSummaryFilters } from "@/services/dashboard";

function downloadCsv(content: string, fileName: string) {
  const blob = new Blob([content], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = fileName;
  anchor.click();
  URL.revokeObjectURL(url);
}

export function ManagerDashboardView() {
  const [filters, setFilters] = useState<AdminSummaryFilters>({ overdueOnly: false });
  const { data: metrics, isLoading } = useAdminSummary(filters, true);
  const { data: technicians } = useTechnicianOptions();
  const { data: overdueInvoices } = useOverdueInvoices();
  const { data: lowStockParts } = useLowStockParts();
  const csv = useSummaryCsv(metrics ?? [], filters);

  const technicianOptions: TechnicianOption[] = useMemo(
    () => technicians ?? [],
    [technicians],
  );

  return (
    <div className="space-y-6">
      <header className="space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight text-foreground">Manager dashboard</h1>
        <p className="text-sm text-muted-foreground">
          Cross-team visibility into open jobs, receivables, and inventory readiness.
        </p>
      </header>
      <SummaryFilters filters={filters} technicians={technicianOptions} onChange={setFilters} />
      <div className="flex items-center justify-between gap-3">
        <p className="text-xs text-muted-foreground">
          Filters sync with the admin summary endpoint so exports mirror your selection.
        </p>
        <button
          type="button"
          onClick={() => downloadCsv(csv, "dashboard-summary.csv")}
          className="inline-flex items-center gap-2 rounded-md border border-border/70 bg-background px-3 py-2 text-xs font-medium text-foreground transition-colors hover:bg-accent"
        >
          Export summary CSV
        </button>
      </div>
      {isLoading || !metrics ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 3 }).map((_, index) => (
            <div key={index} className="h-24 animate-pulse rounded-xl bg-muted/40" />
          ))}
        </div>
      ) : (
        <SummaryGrid metrics={metrics} />
      )}
      <div className="grid gap-6 lg:grid-cols-2">
        <OverdueInvoicesTable invoices={overdueInvoices ?? []} />
        <LowStockPartsTable parts={lowStockParts ?? []} />
      </div>
    </div>
  );
}
