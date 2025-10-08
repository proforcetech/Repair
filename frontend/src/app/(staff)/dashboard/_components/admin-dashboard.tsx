"use client";

import { useState } from "react";

import { LowStockPartsTable } from "@/components/dashboard/low-stock-parts-table";
import { OverdueInvoicesTable } from "@/components/dashboard/overdue-invoices-table";
import { SummaryFilters } from "@/components/dashboard/summary-filters";
import { SummaryGrid } from "@/components/dashboard/summary-grid";
import {
  useAdminSummary,
  useLowStockParts,
  useOverdueInvoices,
  useSummaryCsv,
  useTechnicianOptions,
} from "@/hooks/use-dashboard-data";
import type { AdminSummaryFilters } from "@/services/dashboard";

function exportCsv(content: string) {
  const blob = new Blob([content], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = "admin-dashboard-summary.csv";
  anchor.click();
  URL.revokeObjectURL(url);
}

export function AdminDashboardView() {
  const [filters, setFilters] = useState<AdminSummaryFilters>({ overdueOnly: true });
  const { data: metrics, isLoading } = useAdminSummary(filters, true);
  const { data: overdueInvoices } = useOverdueInvoices();
  const { data: lowStock } = useLowStockParts();
  const { data: technicians } = useTechnicianOptions();
  const csv = useSummaryCsv(metrics ?? [], filters);

  return (
    <div className="space-y-6">
      <header className="space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight text-foreground">Admin command center</h1>
        <p className="text-sm text-muted-foreground">
          Finance-ready KPIs, receivables aging, and replenishment signals consolidated from the API.
        </p>
      </header>
      <SummaryFilters filters={filters} technicians={technicians ?? []} onChange={setFilters} />
      <div className="flex items-center justify-between gap-3">
        <p className="text-xs text-muted-foreground">
          Export respects technician, job status, and overdue filters via query parameters.
        </p>
        <button
          type="button"
          onClick={() => exportCsv(csv)}
          className="inline-flex items-center gap-2 rounded-md bg-primary px-3 py-2 text-xs font-semibold text-primary-foreground shadow hover:bg-primary/90"
        >
          Download CSV snapshot
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
        <LowStockPartsTable parts={lowStock ?? []} />
      </div>
    </div>
  );
}
