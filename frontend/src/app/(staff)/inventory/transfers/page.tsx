"use client";

import { useState } from "react";

import { PartCatalogTable } from "@/components/inventory/part-catalog-table";
import { StockTransferDialog } from "@/components/inventory/stock-transfer-dialog";
import { useInventoryParts, useTransferStock } from "@/hooks/use-inventory";
import type { InventoryPart, StockTransferPayload } from "@/services/inventory";

type TransferDialogState = { type: "transfer"; part: InventoryPart } | null;

export default function InventoryTransfersPage() {
  const [dialog, setDialog] = useState<TransferDialogState>(null);
  const { data: parts, isLoading, error } = useInventoryParts();
  const transferMutation = useTransferStock();

  const errorMessage = error
    ? typeof error === "object" && error !== null && "message" in error
      ? String((error as { message?: unknown }).message ?? "Unable to load parts")
      : "Unable to load parts"
    : null;

  const handleTransfer = async (payload: StockTransferPayload) => {
    await transferMutation.mutateAsync(payload);
  };

  return (
    <div className="space-y-6">
      <header className="space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight text-foreground">Stock transfers</h1>
        <p className="text-sm text-muted-foreground">
          Coordinate inventory moves between warehouses and mobile vans with validation against on-hand counts.
        </p>
      </header>

      <PartCatalogTable
        parts={parts}
        isLoading={isLoading}
        error={errorMessage}
        onTransfer={(part) => setDialog({ type: "transfer", part })}
      />

      <StockTransferDialog
        part={dialog?.part ?? null}
        open={dialog !== null}
        onOpenChange={(open) => {
          if (!open) setDialog(null);
        }}
        onSubmit={handleTransfer}
        isSubmitting={transferMutation.isPending}
      />
    </div>
  );
}
