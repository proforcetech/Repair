"use client";

import { useQuery } from "@tanstack/react-query";

import { getWarrantyHistory } from "@/services/customers";

export default function WarrantyHistoryPage() {
  const warrantyQuery = useQuery({
    queryKey: ["portal", "warranty"],
    queryFn: getWarrantyHistory,
  });

  if (warrantyQuery.isLoading) {
    return <p className="text-sm text-muted-foreground">Loading warranty history…</p>;
  }

  if (warrantyQuery.isError) {
    return <p className="text-sm text-destructive">Unable to load warranty claims.</p>;
  }

  const claims = warrantyQuery.data ?? [];

  return (
    <div className="space-y-6">
      <header className="space-y-2">
        <h1 className="text-2xl font-semibold text-foreground">Warranty claims</h1>
        <p className="text-sm text-muted-foreground">
          Review your submitted warranty claims and track their progress with our service team.
        </p>
      </header>

      {claims.length ? (
        <ul className="space-y-3">
          {claims.map((claim) => (
            <li key={claim.id} className="rounded-md border border-border/60 bg-card/80 p-4 text-sm shadow-sm">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div>
                  <p className="font-medium text-foreground">Claim #{claim.id}</p>
                  <p className="text-xs text-muted-foreground">
                    {claim.status} · {claim.createdAt ? new Date(claim.createdAt).toLocaleDateString() : "Pending"}
                  </p>
                </div>
                {claim.invoiceTotal !== null && claim.invoiceTotal !== undefined && (
                  <span className="text-xs font-medium text-foreground">Invoice total ${claim.invoiceTotal.toFixed(2)}</span>
                )}
              </div>
              {claim.resolutionNotes && (
                <p className="mt-2 text-xs text-muted-foreground">Resolution: {claim.resolutionNotes}</p>
              )}
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-sm text-muted-foreground">You have not submitted any warranty claims.</p>
      )}
    </div>
  );
}
