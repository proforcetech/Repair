"use client";

import { useState } from "react";
import Link from "next/link";
import { useMutation, useQueryClient } from "@tanstack/react-query";

import { useEstimate } from "@/hooks/use-estimates";
import {
  EstimateItem,
  EstimateStatus,
  updateEstimateStatus,
} from "@/services/estimates";
import { showToast } from "@/stores/toast-store";

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

export default function CustomerEstimateDetailPage({ params }: PageProps) {
  const queryClient = useQueryClient();
  const estimateId = params.estimateId;
  const { data, isLoading, isError } = useEstimate(estimateId);
  const [signature, setSignature] = useState("");
  const [notes, setNotes] = useState("");

  const mutateStatus = useMutation({
    mutationFn: (status: EstimateStatus) => updateEstimateStatus(estimateId, status),
    onSuccess: ({ estimate }) => {
      queryClient.invalidateQueries({ queryKey: ["estimates"] });
      queryClient.invalidateQueries({ queryKey: ["estimates", estimateId] });
      showToast({
        title: `Estimate ${estimate.status === "APPROVED" ? "approved" : "updated"}`,
        description:
          estimate.status === "APPROVED"
            ? "Thank you! Our service team will be in touch shortly."
            : "We have recorded your decision.",
        variant: "success",
      });
    },
    onError: (error: unknown) => {
      showToast({
        title: "Unable to update estimate",
        description:
          typeof error === "object" && error !== null && "message" in error
            ? String((error as { message?: unknown }).message)
            : "Unexpected error",
        variant: "destructive",
      });
    },
  });

  const handleApprove = () => {
    if (!signature.trim()) {
      showToast({
        title: "Signature required",
        description: "Please type your name to provide a digital sign-off.",
        variant: "destructive",
      });
      return;
    }
    mutateStatus.mutate("APPROVED");
  };

  const handleReject = () => {
    mutateStatus.mutate("REJECTED");
  };

  if (isLoading) {
    return <p className="text-sm text-muted-foreground">Loading estimate…</p>;
  }

  if (isError || !data) {
    return (
      <div className="space-y-4">
        <p className="text-sm text-destructive">We couldn&apos;t find that estimate.</p>
        <Link href="/portal/estimates" className="text-sm font-medium text-primary hover:underline">
          Back to estimates
        </Link>
      </div>
    );
  }

  const disabled = mutateStatus.isPending;

  return (
    <div className="space-y-8">
      <header className="space-y-1">
        <h1 className="text-2xl font-semibold text-foreground">Estimate #{data.id}</h1>
        <p className="text-sm text-muted-foreground">
          Current status: <span className="font-medium text-foreground">{formatStatus(data.status)}</span>
        </p>
      </header>

      <section className="space-y-3">
        <h2 className="text-lg font-semibold text-foreground">Work summary</h2>
        <div className="overflow-hidden rounded-md border border-border/70 bg-background shadow-sm">
          <table className="min-w-full divide-y divide-border/70 text-sm">
            <thead className="bg-muted/40">
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
                    No items recorded on this estimate.
                  </td>
                </tr>
              ) : (
                data.items.map((item) => <ItemRow key={item.id} item={item} />)
              )}
            </tbody>
            <tfoot className="bg-muted/40">
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

      <section className="space-y-4 rounded-md border border-border/70 bg-muted/30 p-4">
        <div>
          <h2 className="text-lg font-semibold text-foreground">Digital approval</h2>
          <p className="text-sm text-muted-foreground">
            To approve, please enter your full name as a digital signature. Your approval authorizes our team to begin the work.
          </p>
        </div>
        <div className="space-y-2 text-sm">
          <label className="font-medium text-foreground" htmlFor="signature">
            Signature (type your name)
          </label>
          <input
            id="signature"
            type="text"
            value={signature}
            disabled={disabled}
            onChange={(event) => setSignature(event.target.value)}
            className="w-full max-w-md rounded-md border border-border/70 bg-background px-3 py-2 shadow-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
          />
        </div>
        <div className="space-y-2 text-sm">
          <label className="font-medium text-foreground" htmlFor="notes">
            Notes (optional)
          </label>
          <textarea
            id="notes"
            value={notes}
            disabled={disabled}
            onChange={(event) => setNotes(event.target.value)}
            rows={3}
            className="w-full max-w-md rounded-md border border-border/70 bg-background px-3 py-2 shadow-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
          />
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition hover:bg-primary/90 disabled:opacity-50"
            disabled={disabled}
            onClick={handleApprove}
          >
            {mutateStatus.isPending && mutateStatus.variables === "APPROVED"
              ? "Submitting approval…"
              : "Approve estimate"}
          </button>
          <button
            type="button"
            className="rounded-md border border-border/70 px-4 py-2 text-sm font-medium text-foreground transition hover:bg-muted/60 disabled:opacity-50"
            disabled={disabled}
            onClick={handleReject}
          >
            {mutateStatus.isPending && mutateStatus.variables === "REJECTED"
              ? "Submitting response…"
              : "Reject estimate"}
          </button>
        </div>
      </section>
    </div>
  );
}

function ItemRow({ item }: { item: EstimateItem }) {
  return (
    <tr className="hover:bg-muted/20">
      <td className="px-4 py-3 text-foreground">{item.description}</td>
      <td className="px-4 py-3 text-muted-foreground">{item.qty ?? "—"}</td>
      <td className="px-4 py-3 text-muted-foreground">{item.partId ?? "—"}</td>
      <td className="px-4 py-3 text-right font-medium text-foreground">
        {formatCurrency(item.cost)}
      </td>
    </tr>
  );
}
