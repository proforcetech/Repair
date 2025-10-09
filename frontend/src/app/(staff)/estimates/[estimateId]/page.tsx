"use client";

import { useState } from "react";
import Link from "next/link";

import {
  useEstimate,
  useEstimateMutations,
} from "@/hooks/use-estimates";
import { EstimateItem } from "@/services/estimates";

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

type PageProps = {
  params: { estimateId: string };
};

export default function EstimateDetailPage({ params }: PageProps) {
  const estimateId = params.estimateId;
  const { data, isLoading, isError } = useEstimate(estimateId);
  const { statusMutation, approveMutation, rejectMutation, duplicateMutation, applyTemplateMutation } =
    useEstimateMutations(estimateId);
  const [templateId, setTemplateId] = useState("");

  if (isLoading) {
    return <p className="text-sm text-muted-foreground">Loading estimate…</p>;
  }

  if (isError || !data) {
    return (
      <div className="space-y-4">
        <p className="text-sm text-destructive">Unable to load estimate details.</p>
        <Link href="/estimates" className="text-sm font-medium text-primary hover:underline">
          Back to estimates
        </Link>
      </div>
    );
  }

  const disableActions =
    statusMutation.isPending ||
    approveMutation.isPending ||
    rejectMutation.isPending ||
    duplicateMutation.isPending ||
    applyTemplateMutation.isPending;

  return (
    <div className="space-y-8">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-foreground">Estimate #{data.id}</h1>
          <p className="text-sm text-muted-foreground">
            Status: <span className="font-medium text-foreground">{formatStatus(data.status)}</span>
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            className="rounded-md border border-border/70 px-3 py-1.5 text-sm font-medium text-foreground transition hover:bg-muted/70"
            disabled={statusMutation.isPending || disableActions}
            onClick={() => statusMutation.mutate("PENDING_CUSTOMER_APPROVAL")}
          >
            Request customer approval
          </button>
          <button
            type="button"
            className="rounded-md bg-emerald-600 px-3 py-1.5 text-sm font-medium text-white transition hover:bg-emerald-700 disabled:opacity-50"
            disabled={approveMutation.isPending || disableActions}
            onClick={() => approveMutation.mutate()}
          >
            {approveMutation.isPending ? "Approving…" : "Approve"}
          </button>
          <button
            type="button"
            className="rounded-md bg-red-600 px-3 py-1.5 text-sm font-medium text-white transition hover:bg-red-700 disabled:opacity-50"
            disabled={rejectMutation.isPending || disableActions}
            onClick={() => rejectMutation.mutate()}
          >
            {rejectMutation.isPending ? "Rejecting…" : "Reject"}
          </button>
          <button
            type="button"
            className="rounded-md border border-border/70 px-3 py-1.5 text-sm font-medium text-foreground transition hover:bg-muted/70"
            disabled={duplicateMutation.isPending}
            onClick={() => duplicateMutation.mutate()}
          >
            {duplicateMutation.isPending ? "Duplicating…" : "Duplicate"}
          </button>
        </div>
      </div>

      <section className="space-y-4">
        <header className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 className="text-lg font-semibold text-foreground">Line items</h2>
            <p className="text-sm text-muted-foreground">
              Labor and parts captured on this estimate with calculated totals.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <input
              type="text"
              value={templateId}
              onChange={(event) => setTemplateId(event.target.value)}
              placeholder="Template ID"
              className="w-40 rounded-md border border-border/70 bg-background px-3 py-2 text-sm shadow-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
            />
            <button
              type="button"
              className="rounded-md bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground transition hover:bg-primary/90 disabled:opacity-50"
              disabled={!templateId || applyTemplateMutation.isPending}
              onClick={() => applyTemplateMutation.mutate(templateId)}
            >
              {applyTemplateMutation.isPending ? "Applying…" : "Apply template"}
            </button>
          </div>
        </header>

        <div className="overflow-hidden rounded-md border border-border/70 bg-background shadow-sm">
          <table className="min-w-full divide-y divide-border/70 text-sm">
            <thead className="bg-muted/50">
              <tr>
                <th className="px-4 py-3 text-left font-medium text-muted-foreground">Description</th>
                <th className="px-4 py-3 text-left font-medium text-muted-foreground">Qty</th>
                <th className="px-4 py-3 text-left font-medium text-muted-foreground">Part</th>
                <th className="px-4 py-3 text-right font-medium text-muted-foreground">Cost</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border/70">
              {data.items.length === 0 ? (
                <tr>
                  <td colSpan={4} className="px-4 py-6 text-center text-muted-foreground">
                    No items on this estimate yet.
                  </td>
                </tr>
              ) : (
                data.items.map((item) => <ItemRow key={item.id} item={item} />)
              )}
            </tbody>
            <tfoot className="bg-muted/50">
              <tr>
                <td colSpan={3} className="px-4 py-3 text-right text-sm font-medium text-muted-foreground">
                  Total
                </td>
                <td className="px-4 py-3 text-right text-lg font-semibold text-foreground">
                  {formatCurrency(data.total)}
                </td>
              </tr>
            </tfoot>
          </table>
        </div>
      </section>
    </div>
  );
}

function ItemRow({ item }: { item: EstimateItem }) {
  return (
    <tr className="hover:bg-muted/40">
      <td className="px-4 py-3 text-foreground">{item.description}</td>
      <td className="px-4 py-3 text-muted-foreground">{item.qty ?? "—"}</td>
      <td className="px-4 py-3 text-muted-foreground">{item.partId ?? "—"}</td>
      <td className="px-4 py-3 text-right font-medium text-foreground">
        {formatCurrency(item.cost)}
      </td>
    </tr>
  );
}
