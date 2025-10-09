import { Fragment } from "react";

import type { InvoiceMarginAnalytics } from "@/services/invoices";

import { StatCard } from "./stat-card";

export type InvoiceMarginInsightsProps = {
  analytics: InvoiceMarginAnalytics | null | undefined;
  isLoading?: boolean;
};

export function InvoiceMarginInsights({ analytics, isLoading = false }: InvoiceMarginInsightsProps) {
  if (isLoading) {
    return (
      <div className="grid gap-4 sm:grid-cols-2">
        {Array.from({ length: 2 }).map((_, index) => (
          <div key={index} className="h-28 animate-pulse rounded-xl bg-muted/40" />
        ))}
      </div>
    );
  }

  if (!analytics) {
    return (
      <div className="rounded-xl border border-border/60 bg-muted/10 p-6 text-sm text-muted-foreground">
        Margin analytics will appear once invoices are finalized with cost data.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="grid gap-4 sm:grid-cols-2">
        <StatCard
          title="Average gross margin"
          value={`${analytics.averageMarginPercent.toFixed(2)}%`}
          hint={`Threshold ${analytics.threshold.toFixed(0)}%`}
          tone={analytics.averageMarginPercent < analytics.threshold ? "warning" : "success"}
        />
        <StatCard
          title="Invoices below threshold"
          value={analytics.lowMarginInvoices}
          hint="Review these jobs to protect profitability"
          tone={analytics.lowMarginInvoices > 0 ? "critical" : "success"}
        />
      </div>

      <div className="overflow-hidden rounded-xl border border-border/60">
        <table className="min-w-full divide-y divide-border/70 text-sm">
          <thead className="bg-muted/40">
            <tr>
              <th className="px-4 py-2 text-left font-medium text-muted-foreground">Invoice</th>
              <th className="px-4 py-2 text-left font-medium text-muted-foreground">Customer</th>
              <th className="px-4 py-2 text-left font-medium text-muted-foreground">Finalized</th>
              <th className="px-4 py-2 text-right font-medium text-muted-foreground">Margin</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border/70">
            {analytics.series.length === 0 ? (
              <tr>
                <td colSpan={4} className="px-4 py-4 text-center text-muted-foreground">
                  No finalized invoices yet.
                </td>
              </tr>
            ) : (
              analytics.series.map((entry) => (
                <Fragment key={entry.invoiceId}>
                  <tr className={entry.isBelowThreshold ? "bg-red-500/5" : undefined}>
                    <td className="px-4 py-2 font-medium text-foreground">#{entry.number}</td>
                    <td className="px-4 py-2 text-muted-foreground">{entry.customer ?? "—"}</td>
                    <td className="px-4 py-2 text-muted-foreground">{formatDate(entry.finalizedAt)}</td>
                    <td className="px-4 py-2 text-right font-semibold text-foreground">
                      {entry.grossMarginPercent.toFixed(2)}%
                    </td>
                  </tr>
                </Fragment>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function formatDate(value: string | null | undefined) {
  if (!value) {
    return "—";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "—";
  }
  return date.toLocaleDateString();
}
