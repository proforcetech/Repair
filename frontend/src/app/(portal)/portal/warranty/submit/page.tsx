"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";
import { useMutation } from "@tanstack/react-query";

import { submitWarrantyClaim } from "@/services/warranty";
import { showToast } from "@/stores/toast-store";

export default function WarrantySubmitPage() {
  const router = useRouter();
  const [workOrderId, setWorkOrderId] = useState("");
  const [description, setDescription] = useState("");
  const [attachment, setAttachment] = useState<File | null>(null);

  const submitMutation = useMutation({
    mutationFn: submitWarrantyClaim,
    onSuccess: () => {
      showToast({
        title: "Warranty claim submitted",
        description: "Our team will review your submission and follow up shortly.",
        variant: "success",
      });
      router.push("/portal/warranty");
    },
    onError: (error) => {
      const message =
        typeof error === "object" && error !== null && "message" in error
          ? String((error as { message?: unknown }).message ?? "Unable to submit claim")
          : "Unable to submit claim";
      showToast({
        title: "Submission failed",
        description: message,
        variant: "destructive",
      });
    },
  });

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!workOrderId.trim() || !description.trim()) {
      showToast({
        title: "Missing information",
        description: "Work order ID and issue description are required.",
        variant: "warning",
      });
      return;
    }

    submitMutation.mutate({
      workOrderId: workOrderId.trim(),
      description: description.trim(),
      attachment,
    });
  };

  return (
    <div className="space-y-6">
      <header className="space-y-2">
        <h1 className="text-2xl font-semibold text-foreground">Submit warranty claim</h1>
        <p className="text-sm text-muted-foreground">
          Provide details about the issue you are experiencing. Our warranty specialists will respond within 48 hours.
        </p>
        <Link
          href="/portal/warranty"
          className="inline-flex items-center text-sm font-medium text-primary hover:underline"
        >
          ← Back to warranty history
        </Link>
      </header>

      <form onSubmit={handleSubmit} className="space-y-6">
        <div className="space-y-2">
          <label htmlFor="workOrder" className="text-sm font-medium text-foreground">
            Work order number
          </label>
          <input
            id="workOrder"
            name="workOrder"
            type="text"
            required
            value={workOrderId}
            onChange={(event) => setWorkOrderId(event.target.value)}
            className="w-full rounded-md border border-border/70 bg-background px-3 py-2 text-sm shadow-sm focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
            placeholder="e.g. WO-10234"
          />
          <p className="text-xs text-muted-foreground">Find this on the invoice or repair order we provided.</p>
        </div>

        <div className="space-y-2">
          <label htmlFor="issue" className="text-sm font-medium text-foreground">
            Describe the issue
          </label>
          <textarea
            id="issue"
            name="issue"
            required
            value={description}
            onChange={(event) => setDescription(event.target.value)}
            className="min-h-[120px] w-full rounded-md border border-border/70 bg-background px-3 py-2 text-sm shadow-sm focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
            placeholder="Share what went wrong, when you noticed it, and any supporting details."
          />
        </div>

        <div className="space-y-2">
          <label htmlFor="attachment" className="text-sm font-medium text-foreground">
            Attach photos or documents (optional)
          </label>
          <input
            id="attachment"
            name="attachment"
            type="file"
            accept="image/*,application/pdf"
            onChange={(event) => {
              const file = event.target.files?.[0] ?? null;
              setAttachment(file);
            }}
            className="block w-full text-sm text-foreground file:mr-4 file:rounded-md file:border-0 file:bg-secondary file:px-3 file:py-2 file:text-sm file:font-medium file:text-secondary-foreground hover:file:bg-secondary/80"
          />
          <p className="text-xs text-muted-foreground">Accepted formats: photos and PDF documents up to 10MB.</p>
        </div>

        <button
          type="submit"
          className="inline-flex w-full items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition hover:bg-primary/90 disabled:opacity-50"
          disabled={submitMutation.isLoading}
        >
          {submitMutation.isLoading ? "Submitting…" : "Submit claim"}
        </button>

        {submitMutation.isError && (
          <p className="text-sm text-destructive">We couldn’t submit your claim. Please try again.</p>
        )}
      </form>
    </div>
  );
}
