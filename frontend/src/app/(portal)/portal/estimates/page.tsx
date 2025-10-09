"use client";

import Link from "next/link";

import { useEstimates } from "@/hooks/use-estimates";
import { EstimateSummary } from "@/services/estimates";

function formatStatus(status: string) {
  return status
    .toLowerCase()
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

export default function CustomerEstimatesPage() {
  const { data, isLoading, isError } = useEstimates();

  return (
    <div className="space-y-6">
      <header className="space-y-2">
        <h1 className="text-2xl font-semibold text-foreground">Your estimates</h1>
        <p className="text-sm text-muted-foreground">
          Review pending service proposals and approve work directly from the portal.
        </p>
      </header>

      <div className="rounded-md border border-border/70 bg-background shadow-sm">
        <table className="min-w-full divide-y divide-border/70 text-sm">
          <thead className="bg-muted/40">
            <tr>
              <th className="px-4 py-3 text-left font-medium text-muted-foreground">Estimate</th>
              <th className="px-4 py-3 text-left font-medium text-muted-foreground">Status</th>
              <th className="px-4 py-3 text-right font-medium text-muted-foreground">Total</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border/70">
            {isLoading && (
              <tr>
                <td colSpan={3} className="px-4 py-6 text-center text-muted-foreground">
                  Loading your estimates…
                </td>
              </tr>
            )}
            {isError && (
              <tr>
                <td colSpan={3} className="px-4 py-6 text-center text-destructive">
                  We couldn&apos;t load your estimates. Please refresh the page.
                </td>
              </tr>
            )}
            {!isLoading && !isError && data && data.length === 0 && (
              <tr>
                <td colSpan={3} className="px-4 py-6 text-center text-muted-foreground">
                  No estimates to review right now.
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
        <Link href={`/portal/estimates/${estimate.id}`} className="font-semibold text-primary hover:underline">
          Estimate #{estimate.id}
        </Link>
      </td>
      <td className="px-4 py-3 text-muted-foreground">{formatStatus(estimate.status)}</td>
      <td className="px-4 py-3 text-right font-medium text-foreground">
        {typeof estimate.total === "number"
          ? new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(estimate.total)
          : "—"}
      </td>
    </tr>
  );
}
