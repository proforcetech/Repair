"use client";

import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";

import { validateConsumptionQuantity } from "@/hooks/use-inventory";
import type { InventoryPart, PartConsumptionPayload } from "@/services/inventory";

type ConsumePartFormValues = {
  jobId: string;
  quantity: number;
  note?: string;
};

type ConsumePartDialogProps = {
  part: InventoryPart | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSubmit: (values: PartConsumptionPayload & { note?: string | null }) => Promise<void>;
  isSubmitting?: boolean;
};

export function ConsumePartDialog({
  part,
  open,
  onOpenChange,
  onSubmit,
  isSubmitting = false,
}: ConsumePartDialogProps) {
  const [serverError, setServerError] = useState<string | null>(null);
  const form = useForm<ConsumePartFormValues>({
    defaultValues: {
      jobId: "",
      quantity: 1,
      note: "",
    },
  });

  const availableQuantity = part?.quantity ?? 0;

  useEffect(() => {
    if (!open) {
      form.reset({ jobId: "", quantity: 1, note: "" });
      setServerError(null);
    }
  }, [open, form]);

  if (!open || !part) {
    return null;
  }

  const quantityValue = form.watch("quantity");
  const quantityError = validateConsumptionQuantity(quantityValue ?? 0, availableQuantity);

  const handleSubmit = form.handleSubmit(async (values) => {
    const message = validateConsumptionQuantity(values.quantity ?? 0, availableQuantity);
    if (message) {
      form.setError("quantity", { message });
      return;
    }

    if (!values.jobId) {
      form.setError("jobId", { message: "Job reference is required" });
      return;
    }

    setServerError(null);
    try {
      await onSubmit({
        jobId: values.jobId,
        partId: part.id,
        quantity: values.quantity,
        note: values.note || undefined,
      });
      onOpenChange(false);
    } catch (error) {
      const errorMessage =
        typeof error === "object" && error !== null && "message" in error
          ? String((error as { message?: unknown }).message ?? "Unable to record usage")
          : "Unable to record usage";
      setServerError(errorMessage);
    }
  });

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="w-full max-w-md rounded-lg border border-border/60 bg-background p-6 shadow-xl">
        <div className="space-y-1">
          <h2 className="text-lg font-semibold text-foreground">Consume part</h2>
          <p className="text-xs text-muted-foreground">
            Deduct <span className="font-medium text-foreground">{part.sku}</span> for a work order and update stock levels.
          </p>
        </div>
        <form className="mt-4 space-y-4" onSubmit={handleSubmit} noValidate>
          <div className="space-y-2">
            <label htmlFor="consume-job" className="text-sm font-medium text-foreground">
              Job or work order ID
            </label>
            <input
              id="consume-job"
              type="text"
              className="w-full rounded-md border border-border/70 bg-background px-3 py-2 text-sm shadow-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
              placeholder="e.g. RO-1024"
              {...form.register("jobId", { required: "Job reference is required" })}
            />
            {form.formState.errors.jobId?.message && (
              <p className="text-xs text-destructive">{form.formState.errors.jobId.message}</p>
            )}
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <label htmlFor="consume-quantity" className="text-sm font-medium text-foreground">
                Quantity
              </label>
              <input
                id="consume-quantity"
                type="number"
                min={1}
                max={availableQuantity}
                className="w-full rounded-md border border-border/70 bg-background px-3 py-2 text-sm shadow-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
                {...form.register("quantity", { valueAsNumber: true })}
              />
              {(form.formState.errors.quantity?.message || quantityError) && (
                <p className="text-xs text-destructive">
                  {form.formState.errors.quantity?.message ?? quantityError}
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
            <label htmlFor="consume-note" className="text-sm font-medium text-foreground">
              Notes (optional)
            </label>
            <textarea
              id="consume-note"
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
              {isSubmitting ? "Recording…" : "Record usage"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
