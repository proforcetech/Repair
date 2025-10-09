"use client";

import Link from "next/link";

import { useEstimates } from "@/hooks/use-estimates";
import { EstimateSummary } from "@/services/estimates";

function formatCurrency(value: number | null | undefined) {
  if (typeof value !== "number") {
    return "—";
  }
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
  }).format(value);
}

function formatStatus(status: string) {
  return status
    .toLowerCase()
    .split("_")
    .map((segment) => segment.charAt(0).toUpperCase() + segment.slice(1))
    .join(" ");
}

function StatusPill({ status }: { status: string }) {
  const map: Record<string, string> = {
    APPROVED: "bg-emerald-100 text-emerald-800",
    REJECTED: "bg-red-100 text-red-800",
    PENDING_CUSTOMER_APPROVAL: "bg-amber-100 text-amber-800",
    DRAFT: "bg-slate-200 text-slate-800",
  };
  const classes = map[status] ?? "bg-slate-200 text-slate-800";
  return (
    <span className={`inline-flex items-center rounded-full px-2 py-1 text-xs font-medium ${classes}`}>
      {formatStatus(status)}
    </span>
  );
}

export default function EstimatesPage() {
  const { data, isLoading, isError } = useEstimates();

  return (
    <div className="space-y-6">
      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
        <div>
          <h1 className="text-2xl font-semibold text-foreground">Estimates</h1>
          <p className="text-sm text-muted-foreground">
            Track drafts awaiting approval and manage customer commitments.
          </p>
        </div>
        <Link
          href="/estimates/new"
          className="inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition hover:bg-primary/90"
        >
          Create estimate
        </Link>
      </div>

      <div className="overflow-hidden rounded-md border border-border/70 bg-background shadow-sm">
        <table className="min-w-full divide-y divide-border/70 text-sm">
          <thead className="bg-muted/50">
            <tr>
              <th className="px-4 py-3 text-left font-medium text-muted-foreground">Estimate</th>
              <th className="px-4 py-3 text-left font-medium text-muted-foreground">Customer</th>
              <th className="px-4 py-3 text-left font-medium text-muted-foreground">Vehicle</th>
              <th className="px-4 py-3 text-left font-medium text-muted-foreground">Status</th>
              <th className="px-4 py-3 text-right font-medium text-muted-foreground">Total</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border/70">
            {isLoading && (
              <tr>
                <td colSpan={5} className="px-4 py-6 text-center text-muted-foreground">
                  Loading estimates…
                </td>
              </tr>
            )}
            {isError && (
              <tr>
                <td colSpan={5} className="px-4 py-6 text-center text-destructive">
                  Unable to load estimates. Try refreshing the page.
                </td>
              </tr>
            )}
            {!isLoading && !isError && data && data.length === 0 && (
              <tr>
                <td colSpan={5} className="px-4 py-6 text-center text-muted-foreground">
                  No estimates yet. Create your first draft to get started.
                </td>
              </tr>
            )}
            {!isLoading && !isError && data?.map((estimate) => (
              <EstimateRow key={estimate.id} estimate={estimate} />
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function EstimateRow({ estimate }: { estimate: EstimateSummary }) {
  return (
    <tr className="hover:bg-muted/30">
      <td className="px-4 py-3">
        <Link href={`/estimates/${estimate.id}`} className="font-semibold text-primary hover:underline">
          #{estimate.id}
        </Link>
      </td>
      <td className="px-4 py-3 text-muted-foreground">
        {estimate.customerName ?? "—"}
      </td>
      <td className="px-4 py-3 text-muted-foreground">
        {estimate.vehicleLabel ?? "—"}
      </td>
      <td className="px-4 py-3">
        <StatusPill status={estimate.status} />
      </td>
      <td className="px-4 py-3 text-right font-medium text-foreground">
        {formatCurrency(estimate.total ?? null)}
      </td>
    </tr>
  );
}
