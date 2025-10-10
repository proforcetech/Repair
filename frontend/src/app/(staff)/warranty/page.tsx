"use client";

import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";

import { fetchWarrantyClaims, WarrantyClaimSummary } from "@/services/warranty";

const FILTERS = [
  { label: "All", query: {} },
  { label: "Assigned to me", query: { assigned_to_me: "true" } },
  { label: "Unassigned", query: { unassigned: "true" } },
  { label: "Awaiting response", query: { awaiting_response: "true" } },
] as const;

type FilterQuery = (typeof FILTERS)[number]["query"];

function parseFilters(searchParams: URLSearchParams) {
  return {
    assigned_to_me: searchParams.get("assigned_to_me") === "true",
    unassigned: searchParams.get("unassigned") === "true",
    awaiting_response: searchParams.get("awaiting_response") === "true",
  };
}

export default function WarrantyTriagePage() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();

  const paramsKey = searchParams.toString();
  const activeFilters = useMemo(() => parseFilters(new URLSearchParams(paramsKey)), [paramsKey]);

  const claimsQuery = useQuery({
    queryKey: ["warranty", "claims", activeFilters],
    queryFn: () => fetchWarrantyClaims(activeFilters),
  });

  const handleFilterChange = (query: FilterQuery) => {
    const params = new URLSearchParams();
    Object.entries(query).forEach(([key, value]) => {
      if (value) {
        params.set(key, value);
      }
    });
    router.replace(params.size > 0 ? `${pathname}?${params.toString()}` : pathname);
  };

  const claims = claimsQuery.data ?? [];

  return (
    <div className="space-y-6">
      <header className="space-y-2">
        <h1 className="text-2xl font-semibold text-foreground">Warranty triage</h1>
        <p className="text-sm text-muted-foreground">
          Track customer issues, assignments, and SLA risk from a single view.
        </p>
        <div className="flex flex-wrap gap-2">
          {FILTERS.map((filter) => {
            const isActive = isFilterActive(filter.query, activeFilters);
            return (
              <button
                key={filter.label}
                type="button"
                onClick={() => handleFilterChange(filter.query)}
                className={`inline-flex items-center rounded-full border px-3 py-1 text-xs font-medium transition ${
                  isActive
                    ? "border-primary bg-primary/10 text-primary"
                    : "border-border/70 text-muted-foreground hover:border-primary/40 hover:text-primary"
                }`}
              >
                {filter.label}
              </button>
            );
          })}
        </div>
      </header>

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {claimsQuery.isLoading && (
          <div className="rounded-lg border border-border/60 bg-muted/30 p-6 text-sm text-muted-foreground">
            Loading warranty claims…
          </div>
        )}
        {claimsQuery.isError && (
          <div className="rounded-lg border border-destructive/40 bg-destructive/10 p-6 text-sm text-destructive">
            Unable to load claims. Try refreshing the page.
          </div>
        )}
        {!claimsQuery.isLoading && !claimsQuery.isError && claims.length === 0 && (
          <div className="rounded-lg border border-border/60 bg-card/80 p-6 text-sm text-muted-foreground">
            No claims match the selected filters.
          </div>
        )}
        {claims.map((claim) => (
          <ClaimCard key={claim.id} claim={claim} />
        ))}
      </section>
    </div>
  );
}

function isFilterActive(query: FilterQuery, activeFilters: ReturnType<typeof parseFilters>) {
  const expected = {
    assigned_to_me: Boolean(query.assigned_to_me),
    unassigned: Boolean(query.unassigned),
    awaiting_response: Boolean(query.awaiting_response),
  };
  return (
    activeFilters.assigned_to_me === expected.assigned_to_me &&
    activeFilters.unassigned === expected.unassigned &&
    activeFilters.awaiting_response === expected.awaiting_response
  );
}

function ClaimCard({ claim }: { claim: WarrantyClaimSummary }) {
  const createdAt = claim.createdAt ? new Date(claim.createdAt) : null;
  const status = formatStatus(claim.status);
  const assigned =
    claim.assignedTo?.firstName || claim.assignedTo?.lastName || claim.assignedTo?.email
      ? [claim.assignedTo?.firstName, claim.assignedTo?.lastName].filter(Boolean).join(" ") || claim.assignedTo?.email
      : "Unassigned";

  return (
    <article className="flex h-full flex-col justify-between rounded-lg border border-border/60 bg-card/80 p-4 shadow-sm">
      <div className="space-y-3">
        <div className="flex items-center justify-between text-xs">
          <span className="font-semibold text-foreground">Claim #{claim.id}</span>
          <StatusBadge status={status} />
        </div>
        <p className="text-sm text-muted-foreground line-clamp-3">{claim.description ?? "No description provided."}</p>
        <dl className="space-y-1 text-xs text-muted-foreground">
          <div className="flex items-center justify-between">
            <dt>Opened</dt>
            <dd>{createdAt ? createdAt.toLocaleString() : "—"}</dd>
          </div>
          <div className="flex items-center justify-between">
            <dt>Assigned</dt>
            <dd>{assigned}</dd>
          </div>
        </dl>
      </div>
      <Link
        href={`/warranty/${claim.id}`}
        className="mt-4 inline-flex items-center justify-center rounded-md border border-border px-3 py-2 text-sm font-medium text-foreground transition hover:border-primary hover:text-primary"
      >
        View details
      </Link>
    </article>
  );
}

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, string> = {
    Approved: "bg-emerald-100 text-emerald-800",
    Denied: "bg-red-100 text-red-700",
    Pending: "bg-amber-100 text-amber-800",
    Open: "bg-slate-200 text-slate-700",
    "Needs More Info": "bg-blue-100 text-blue-700",
  };

  const classes = map[status] ?? "bg-slate-200 text-slate-700";
  return <span className={`inline-flex rounded-full px-2 py-1 text-[11px] font-medium ${classes}`}>{status}</span>;
}

function formatStatus(status: string) {
  return status
    .toLowerCase()
    .split("_")
    .map((segment) => segment.charAt(0).toUpperCase() + segment.slice(1))
    .join(" ");
}
