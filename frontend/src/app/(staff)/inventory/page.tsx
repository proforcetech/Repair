"use client";

import { useState } from "react";

import { ConsumePartDialog } from "@/components/inventory/consume-part-dialog";
import { PartCatalogTable } from "@/components/inventory/part-catalog-table";
import { StockTransferDialog } from "@/components/inventory/stock-transfer-dialog";
import { useConsumePart, useInventoryParts, useTransferStock } from "@/hooks/use-inventory";
import type { InventoryPart, PartConsumptionPayload, StockTransferPayload } from "@/services/inventory";

type ActiveDialog =
  | { type: "transfer"; part: InventoryPart }
  | { type: "consume"; part: InventoryPart }
  | null;

export default function InventoryCatalogPage() {
  const [activeDialog, setActiveDialog] = useState<ActiveDialog>(null);
  const { data: parts, isLoading, error } = useInventoryParts();
  const transferMutation = useTransferStock();
  const consumeMutation = useConsumePart();

  const handleTransfer = async (payload: StockTransferPayload) => {
    await transferMutation.mutateAsync(payload);
  };

  const handleConsume = async (payload: PartConsumptionPayload & { note?: string | null }) => {
    const { note: _note, ...rest } = payload;
    await consumeMutation.mutateAsync(rest);
  };

  const closeDialog = () => setActiveDialog(null);

  const errorMessage = error
    ? typeof error === "object" && error !== null && "message" in error
      ? String((error as { message?: unknown }).message ?? "Unable to load parts")
      : "Unable to load parts"
    : null;

  return (
    <div className="space-y-6">
      <header className="space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight text-foreground">Inventory catalog</h1>
        <p className="text-sm text-muted-foreground">
          Search the master part list, transfer stock between locations, and record consumption in real time.
        </p>
      </header>

      <PartCatalogTable
        parts={parts}
        isLoading={isLoading}
        error={errorMessage}
        onTransfer={(part) => setActiveDialog({ type: "transfer", part })}
        onConsume={(part) => setActiveDialog({ type: "consume", part })}
      />

      <StockTransferDialog
        part={activeDialog?.type === "transfer" ? activeDialog.part : null}
        open={activeDialog?.type === "transfer"}
        onOpenChange={(open) => {
          if (!open) closeDialog();
        }}
        onSubmit={handleTransfer}
        isSubmitting={transferMutation.isPending}
      />

      <ConsumePartDialog
        part={activeDialog?.type === "consume" ? activeDialog.part : null}
        open={activeDialog?.type === "consume"}
        onOpenChange={(open) => {
          if (!open) closeDialog();
        }}
        onSubmit={handleConsume}
        isSubmitting={consumeMutation.isPending}
      />
    </div>
  );
}
