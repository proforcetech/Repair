"use client";

import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";

import type { InventoryPart, StockTransferPayload } from "@/services/inventory";
import { validateTransferQuantity } from "@/hooks/use-inventory";

type StockTransferFormValues = {
  toLocation: string;
  quantity: number;
  note?: string;
};

type StockTransferDialogProps = {
  part: InventoryPart | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSubmit: (values: StockTransferPayload) => Promise<void>;
  isSubmitting?: boolean;
};

export function StockTransferDialog({
  part,
  open,
  onOpenChange,
  onSubmit,
  isSubmitting = false,
}: StockTransferDialogProps) {
  const [serverError, setServerError] = useState<string | null>(null);
  const form = useForm<StockTransferFormValues>({
    defaultValues: {
      toLocation: "",
      quantity: 1,
      note: "",
    },
  });

  const availableQuantity = part?.quantity ?? 0;

  useEffect(() => {
    if (!open) {
      form.reset({ toLocation: "", quantity: 1, note: "" });
      setServerError(null);
    }
  }, [open, form]);

  const quantityValue = form.watch("quantity");
  const validationMessage = validateTransferQuantity(quantityValue ?? 0, availableQuantity);

  if (!open || !part) {
    return null;
  }

  const handleSubmit = form.handleSubmit(async (values) => {
    const errorMessage = validateTransferQuantity(values.quantity ?? 0, availableQuantity);
    if (errorMessage) {
      form.setError("quantity", { message: errorMessage });
      return;
    }

    setServerError(null);
    try {
      await onSubmit({
        partId: part.id,
        fromLocation: part.location ?? "", 
        toLocation: values.toLocation,
        quantity: values.quantity,
        note: values.note || undefined,
      });
      onOpenChange(false);
    } catch (error) {
      const message =
        typeof error === "object" && error !== null && "message" in error
          ? String((error as { message?: unknown }).message ?? "Unable to transfer stock")
          : "Unable to transfer stock";
      setServerError(message);
    }
  });

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="w-full max-w-md rounded-lg border border-border/60 bg-background p-6 shadow-xl">
        <div className="space-y-1">
          <h2 className="text-lg font-semibold text-foreground">Transfer stock</h2>
          <p className="text-xs text-muted-foreground">
            Move <span className="font-medium text-foreground">{part.sku}</span> from {part.location ?? "default location"} to a new site.
          </p>
        </div>
        <form className="mt-4 space-y-4" onSubmit={handleSubmit} noValidate>
          <div className="space-y-2">
            <label htmlFor="transfer-to" className="text-sm font-medium text-foreground">
              Destination location
            </label>
            <input
              id="transfer-to"
              type="text"
              className="w-full rounded-md border border-border/70 bg-background px-3 py-2 text-sm shadow-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
              placeholder="e.g. Truck #2"
              {...form.register("toLocation", { required: "Destination is required" })}
            />
            {form.formState.errors.toLocation?.message && (
              <p className="text-xs text-destructive">{form.formState.errors.toLocation.message}</p>
            )}
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <label htmlFor="transfer-quantity" className="text-sm font-medium text-foreground">
                Quantity
              </label>
              <input
                id="transfer-quantity"
                type="number"
                min={1}
                max={availableQuantity}
                className="w-full rounded-md border border-border/70 bg-background px-3 py-2 text-sm shadow-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
                {...form.register("quantity", { valueAsNumber: true })}
              />
              {(form.formState.errors.quantity?.message || validationMessage) && (
                <p className="text-xs text-destructive">
                  {form.formState.errors.quantity?.message ?? validationMessage}
                </p>
              )}
            </div>
            <div className="space-y-2">
              <span className="text-sm font-medium text-foreground">Available</span>
              <p className="rounded-md border border-border/70 bg-muted/30 px-3 py-2 text-sm text-muted-foreground">
                {availableQuantity} units on hand
              </p>
            </div>
          </div>
          <div className="space-y-2">
            <label htmlFor="transfer-note" className="text-sm font-medium text-foreground">
              Notes (optional)
            </label>
            <textarea
              id="transfer-note"
              className="h-20 w-full resize-none rounded-md border border-border/70 bg-background px-3 py-2 text-sm shadow-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
              {...form.register("note")}
            />
          </div>
          {serverError && <p className="text-sm text-destructive">{serverError}</p>}
          <div className="flex justify-end gap-2">
            <button
              type="button"
              onClick={() => onOpenChange(false)}
              className="inline-flex items-center rounded-md border border-border px-4 py-2 text-sm font-medium text-foreground transition-colors hover:bg-accent"
              disabled={isSubmitting}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="inline-flex items-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
              disabled={isSubmitting}
            >
              {isSubmitting ? "Transferring…" : "Transfer"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
