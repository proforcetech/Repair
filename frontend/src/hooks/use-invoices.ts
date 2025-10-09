"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  InvoiceDetail,
  InvoiceMargin,
  InvoiceMarginAnalytics,
  InvoiceSummary,
  ManualPaymentInput,
  createStripeCheckout,
  finalizeInvoice,
  getInvoice,
  getInvoiceMargin,
  getInvoiceMarginAnalytics,
  listInvoices,
  recordManualPayment,
} from "@/services/invoices";
import { showToast } from "@/stores/toast-store";

export function useInvoices() {
  return useQuery<InvoiceSummary[]>({
    queryKey: ["invoices"],
    queryFn: listInvoices,
  });
}

export function useInvoice(invoiceId: string) {
  return useQuery<InvoiceDetail>({
    queryKey: ["invoices", invoiceId],
    queryFn: () => getInvoice(invoiceId),
    enabled: Boolean(invoiceId),
  });
}

export function useInvoiceMargin(invoiceId: string) {
  return useQuery<InvoiceMargin>({
    queryKey: ["invoices", invoiceId, "margin"],
    queryFn: () => getInvoiceMargin(invoiceId),
    enabled: Boolean(invoiceId),
  });
}

export function useInvoiceMarginAnalytics() {
  return useQuery<InvoiceMarginAnalytics>({
    queryKey: ["invoices", "analytics", "margin"],
    queryFn: getInvoiceMarginAnalytics,
  });
}

export function useFinalizeInvoice(invoiceId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => finalizeInvoice(invoiceId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["invoices"] });
      queryClient.invalidateQueries({ queryKey: ["invoices", invoiceId] });
      showToast({
        title: "Invoice finalized",
        description: "The invoice is now locked for billing",
        variant: "success",
      });
    },
    onError: (error: unknown) => {
      showToast({
        title: "Unable to finalize invoice",
        description:
          typeof error === "object" && error !== null && "message" in error
            ? String((error as { message?: unknown }).message)
            : "Unexpected error",
        variant: "destructive",
      });
    },
  });
}

export function useManualPayment(invoiceId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: ManualPaymentInput) => recordManualPayment(invoiceId, input),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["invoices"] });
      queryClient.invalidateQueries({ queryKey: ["invoices", invoiceId] });
      showToast({
        title: "Payment recorded",
        description: "Balances updated with the new payment",
        variant: "success",
      });
    },
    onError: (error: unknown) => {
      showToast({
        title: "Unable to record payment",
        description:
          typeof error === "object" && error !== null && "message" in error
            ? String((error as { message?: unknown }).message)
            : "Unexpected error",
        variant: "destructive",
      });
    },
  });
}

export function useStripeCheckout(invoiceId: string) {
  return useMutation({
    mutationFn: () => createStripeCheckout(invoiceId),
    onSuccess: ({ checkout_url: checkoutUrl }) => {
      if (checkoutUrl) {
        window.location.href = checkoutUrl;
      }
    },
    onError: (error: unknown) => {
      showToast({
        title: "Unable to start checkout",
        description:
          typeof error === "object" && error !== null && "message" in error
            ? String((error as { message?: unknown }).message)
            : "Unexpected error",
        variant: "destructive",
      });
    },
  });
}
