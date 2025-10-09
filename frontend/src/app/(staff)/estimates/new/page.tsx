"use client";

import { useRouter } from "next/navigation";

import { EstimateBuilder } from "@/components/estimates/estimate-builder";
import { useCreateEstimate } from "@/hooks/use-estimates";

export default function NewEstimatePage() {
  const router = useRouter();
  const createEstimate = useCreateEstimate();

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <header className="space-y-2">
        <h1 className="text-2xl font-semibold text-foreground">New estimate</h1>
        <p className="text-sm text-muted-foreground">
          Build a proposal by combining labor and parts with automatic totals.
        </p>
      </header>

      <EstimateBuilder
        isSubmitting={createEstimate.isPending}
        onSubmit={async (payload) => {
          const estimate = await createEstimate.mutateAsync(payload);
          if (estimate) {
            router.push(`/estimates/${estimate.id}`);
          }
        }}
      />
    </div>
  );
}
