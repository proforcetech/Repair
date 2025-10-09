"use client";

import { useState } from "react";
import Link from "next/link";

import { useInvoices, useStripeCheckout } from "@/hooks/use-invoices";
import { downloadInvoicePdf } from "@/services/invoices";
import type { InvoiceSummary } from "@/services/invoices";
import { showToast } from "@/stores/toast-store";

function formatCurrency(value: number | null | undefined) {
  if (typeof value !== "number" || Number.isNaN(value)) {
    return "—";
  }
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(value);
}

function formatDate(value: string | null | undefined) {
  if (!value) {
    return "—";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "—";
  }
  return date.toLocaleDateString();
}

function formatStatus(status: string) {
  return status
    .toLowerCase()
    .split("_")
    .map((segment) => segment.charAt(0).toUpperCase() + segment.slice(1))
    .join(" ");
}

export default function PortalInvoicesPage() {
  const { data: invoices, isLoading, isError } = useInvoices();
  const [downloadingId, setDownloadingId] = useState<string | null>(null);

  const handleDownload = async (invoiceId: string, invoiceNumber: string) => {
    try {
      setDownloadingId(invoiceId);
      const blob = await downloadInvoicePdf(invoiceId);
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `invoice-${invoiceNumber}.pdf`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    } catch (error) {
      showToast({
        title: "Unable to download invoice",
        description:
          typeof error === "object" && error !== null && "message" in error
            ? String((error as { message?: unknown }).message)
            : "Unexpected error",
        variant: "destructive",
      });
    } finally {
      setDownloadingId(null);
    }
  };

  return (
    <div className="space-y-6">
      <header className="space-y-1">
        <h1 className="text-2xl font-semibold text-foreground">My invoices</h1>
        <p className="text-sm text-muted-foreground">
          Review open balances, download statements, and pay securely online.
        </p>
      </header>

      <div className="overflow-hidden rounded-md border border-border/70 bg-background shadow-sm">
        <table className="min-w-full divide-y divide-border/70 text-sm">
          <thead className="bg-muted/40">
            <tr>
              <th className="px-4 py-3 text-left font-medium text-muted-foreground">Invoice</th>
              <th className="px-4 py-3 text-left font-medium text-muted-foreground">Issued</th>
              <th className="px-4 py-3 text-left font-medium text-muted-foreground">Due</th>
              <th className="px-4 py-3 text-left font-medium text-muted-foreground">Status</th>
              <th className="px-4 py-3 text-right font-medium text-muted-foreground">Total</th>
              <th className="px-4 py-3 text-right font-medium text-muted-foreground">Balance</th>
              <th className="px-4 py-3 text-right font-medium text-muted-foreground">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border/70">
            {isLoading && (
              <tr>
                <td colSpan={7} className="px-4 py-6 text-center text-muted-foreground">
                  Loading invoices…
                </td>
              </tr>
            )}
            {isError && (
              <tr>
                <td colSpan={7} className="px-4 py-6 text-center text-destructive">
                  Unable to load invoices. Please try again later.
                </td>
              </tr>
            )}
            {!isLoading && !isError && invoices && invoices.length === 0 && (
              <tr>
                <td colSpan={7} className="px-4 py-6 text-center text-muted-foreground">
                  You have no invoices yet.
                </td>
              </tr>
            )}
            {!isLoading && !isError &&
              invoices?.map((invoice) => (
                <InvoiceRow
                  key={invoice.id}
                  invoice={invoice}
                  isDownloading={downloadingId === invoice.id}
                  onDownload={() => handleDownload(invoice.id, invoice.number)}
                />
              ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

type InvoiceRowProps = {
  invoice: InvoiceSummary;
  isDownloading: boolean;
  onDownload: () => void;
};

function InvoiceRow({ invoice, isDownloading, onDownload }: InvoiceRowProps) {
  const checkoutMutation = useStripeCheckout(invoice.id);

  return (
    <tr className="hover:bg-muted/30">
      <td className="px-4 py-3">
        <Link href={`/portal/invoices/${invoice.id}`} className="font-semibold text-primary hover:underline">
          #{invoice.number}
        </Link>
      </td>
      <td className="px-4 py-3 text-muted-foreground">{formatDate(invoice.issuedDate)}</td>
      <td className="px-4 py-3 text-muted-foreground">{formatDate(invoice.dueDate)}</td>
      <td className="px-4 py-3 text-muted-foreground">{formatStatus(invoice.status)}</td>
      <td className="px-4 py-3 text-right font-medium text-foreground">{formatCurrency(invoice.total)}</td>
      <td className="px-4 py-3 text-right font-medium text-foreground">{formatCurrency(invoice.balanceDue)}</td>
      <td className="px-4 py-3 text-right">
        <div className="flex justify-end gap-2">
          <button
            type="button"
            onClick={onDownload}
            className="inline-flex items-center rounded-md border border-border/60 px-3 py-1.5 text-xs font-medium text-foreground transition hover:bg-accent"
            disabled={isDownloading}
          >
            {isDownloading ? "Preparing…" : "Download"}
          </button>
          <button
            type="button"
            onClick={() => checkoutMutation.mutate()}
            className="inline-flex items-center rounded-md bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground shadow transition hover:bg-primary/90"
            disabled={checkoutMutation.isPending}
          >
            {checkoutMutation.isPending ? "Redirecting…" : "Pay online"}
          </button>
        </div>
      </td>
    </tr>
  );
}
