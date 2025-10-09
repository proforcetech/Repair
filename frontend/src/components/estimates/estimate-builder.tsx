"use client";

import { useMemo, useState } from "react";

import {
  EstimateCreateInput,
  EstimateItemDraft,
  LaborItemDraft,
  PartItemDraft,
  calculateEstimateTotals,
  draftToEstimateItem,
} from "@/services/estimates";

import { LaborItemEditor, PartItemEditor } from "./estimate-item-editors";

type EstimateBuilderProps = {
  onSubmit: (payload: EstimateCreateInput) => Promise<void> | void;
  isSubmitting?: boolean;
};

export function EstimateBuilder({ onSubmit, isSubmitting }: EstimateBuilderProps) {
  const [vehicleId, setVehicleId] = useState("");
  const [labor, setLabor] = useState<LaborItemDraft[]>([]);
  const [parts, setParts] = useState<PartItemDraft[]>([]);

  const draftItems: EstimateItemDraft[] = useMemo(
    () => [...labor, ...parts],
    [labor, parts],
  );

  const totals = useMemo(() => calculateEstimateTotals(draftItems), [draftItems]);

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const items = draftItems.map(draftToEstimateItem).filter((item) => item.cost > 0);
    if (!vehicleId || items.length === 0) {
      return;
    }
    await onSubmit({ vehicle_id: vehicleId, items });
  };

  return (
    <form className="space-y-6" onSubmit={handleSubmit}>
      <div className="space-y-2">
        <label className="text-sm font-medium text-foreground" htmlFor="vehicleId">
          Vehicle ID
        </label>
        <input
          id="vehicleId"
          type="text"
          value={vehicleId}
          onChange={(event) => setVehicleId(event.target.value)}
          placeholder="Enter the vehicle identifier"
          className="w-full max-w-sm rounded-md border border-border/70 bg-background px-3 py-2 text-sm shadow-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
        />
      </div>

      <LaborItemEditor items={labor} onChange={setLabor} />

      <PartItemEditor items={parts} onChange={setParts} />

      <div className="rounded-md border border-border/70 bg-muted/40 p-4">
        <h3 className="text-sm font-semibold text-foreground">Totals</h3>
        <dl className="mt-3 grid grid-cols-1 gap-2 text-sm sm:grid-cols-3">
          <div className="rounded-md bg-background p-3 shadow-sm">
            <dt className="text-muted-foreground">Labor</dt>
            <dd className="text-lg font-semibold text-foreground">
              ${totals.laborTotal.toFixed(2)}
            </dd>
          </div>
          <div className="rounded-md bg-background p-3 shadow-sm">
            <dt className="text-muted-foreground">Parts</dt>
            <dd className="text-lg font-semibold text-foreground">
              ${totals.partsTotal.toFixed(2)}
            </dd>
          </div>
          <div className="rounded-md bg-background p-3 shadow-sm sm:col-span-3 sm:flex sm:items-center sm:justify-between">
            <dt className="text-muted-foreground">Grand total</dt>
            <dd className="text-2xl font-bold text-foreground">
              ${totals.total.toFixed(2)}
            </dd>
          </div>
        </dl>
      </div>

      <button
        type="submit"
        disabled={isSubmitting || !vehicleId || draftItems.length === 0}
        className="inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {isSubmitting ? "Saving…" : "Create estimate"}
      </button>
    </form>
  );
}
