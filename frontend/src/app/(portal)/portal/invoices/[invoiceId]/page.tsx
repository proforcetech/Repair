"use client";

import { useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";

import { useInvoice, useStripeCheckout } from "@/hooks/use-invoices";
import { downloadInvoicePdf } from "@/services/invoices";
import type { InvoiceLineItem, InvoicePayment } from "@/services/invoices";
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

export default function PortalInvoiceDetailPage() {
  const params = useParams<{ invoiceId: string }>();
  const invoiceId = Array.isArray(params?.invoiceId) ? params?.invoiceId[0] : params?.invoiceId;
  const { data: invoice, isLoading } = useInvoice(invoiceId ?? "");
  const checkoutMutation = useStripeCheckout(invoiceId ?? "");
  const [isDownloading, setIsDownloading] = useState(false);

  const handleDownload = async () => {
    if (!invoiceId || !invoice) {
      return;
    }
    try {
      setIsDownloading(true);
      const blob = await downloadInvoicePdf(invoiceId);
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `invoice-${invoice.number}.pdf`;
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
      setIsDownloading(false);
    }
  };

  if (!invoiceId) {
    return (
      <div className="space-y-2 text-sm text-destructive">
        <p>Invoice id missing from URL.</p>
        <Link href="/portal/invoices" className="text-primary underline">
          Back to invoices
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <header className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="space-y-1">
          <Link href="/portal/invoices" className="text-xs text-muted-foreground hover:text-foreground">
            ← Back to invoices
          </Link>
          <h1 className="text-2xl font-semibold text-foreground">Invoice #{invoice?.number ?? invoiceId}</h1>
          <p className="text-sm text-muted-foreground">
            {invoice ? formatStatus(invoice.status) : "Loading status"} • Due {formatDate(invoice?.dueDate ?? null)}
          </p>
        </div>
        <div className="flex flex-col gap-2 sm:flex-row">
          <button
            type="button"
            onClick={handleDownload}
            className="inline-flex items-center justify-center rounded-md border border-border/60 px-4 py-2 text-sm font-medium text-foreground transition hover:bg-accent"
            disabled={isDownloading || isLoading}
          >
            {isDownloading ? "Preparing…" : "Download PDF"}
          </button>
          <button
            type="button"
            onClick={() => invoiceId && checkoutMutation.mutate()}
            className="inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground shadow transition hover:bg-primary/90"
            disabled={!invoiceId || checkoutMutation.isPending || isLoading}
          >
            {checkoutMutation.isPending ? "Redirecting…" : "Pay online"}
          </button>
        </div>
      </header>

      {isLoading || !invoice ? (
        <div className="grid gap-4 sm:grid-cols-2">
          {Array.from({ length: 2 }).map((_, index) => (
            <div key={index} className="h-36 animate-pulse rounded-lg bg-muted/40" />
          ))}
        </div>
      ) : (
        <div className="space-y-6">
          <section className="rounded-lg border border-border/60 p-4">
            <h2 className="text-lg font-semibold text-foreground">Summary</h2>
            <dl className="mt-3 grid gap-3 text-sm sm:grid-cols-2">
              <div className="flex items-center justify-between">
                <dt className="text-muted-foreground">Issued</dt>
                <dd className="font-medium text-foreground">{formatDate(invoice.issuedDate)}</dd>
              </div>
              <div className="flex items-center justify-between">
                <dt className="text-muted-foreground">Due</dt>
                <dd className="font-medium text-foreground">{formatDate(invoice.dueDate)}</dd>
              </div>
              <div className="flex items-center justify-between">
                <dt className="text-muted-foreground">Total</dt>
                <dd className="font-semibold text-foreground">{formatCurrency(invoice.total)}</dd>
              </div>
              <div className="flex items-center justify-between">
                <dt className="text-muted-foreground">Balance</dt>
                <dd className="font-semibold text-foreground">{formatCurrency(invoice.balanceDue)}</dd>
              </div>
            </dl>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-foreground">Line items</h2>
            <div className="mt-3 overflow-hidden rounded-lg border border-border/60">
              <table className="min-w-full divide-y divide-border/70 text-sm">
                <thead className="bg-muted/40">
                  <tr>
                    <th className="px-4 py-2 text-left font-medium text-muted-foreground">Description</th>
                    <th className="px-4 py-2 text-right font-medium text-muted-foreground">Qty</th>
                    <th className="px-4 py-2 text-right font-medium text-muted-foreground">Unit price</th>
                    <th className="px-4 py-2 text-right font-medium text-muted-foreground">Line total</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/70">
                  {invoice.items.length === 0 ? (
                    <tr>
                      <td colSpan={4} className="px-4 py-4 text-center text-muted-foreground">
                        No line items recorded.
                      </td>
                    </tr>
                  ) : (
                    invoice.items.map((item) => <LineItemRow key={item.id} item={item} />)
                  )}
                </tbody>
              </table>
            </div>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-foreground">Payments</h2>
            <div className="mt-3 overflow-hidden rounded-lg border border-border/60">
              <table className="min-w-full divide-y divide-border/70 text-sm">
                <thead className="bg-muted/40">
                  <tr>
                    <th className="px-4 py-2 text-left font-medium text-muted-foreground">Received</th>
                    <th className="px-4 py-2 text-left font-medium text-muted-foreground">Method</th>
                    <th className="px-4 py-2 text-right font-medium text-muted-foreground">Amount</th>
                    <th className="px-4 py-2 text-right font-medium text-muted-foreground">Remaining</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/70">
                  {invoice.payments.length === 0 ? (
                    <tr>
                      <td colSpan={4} className="px-4 py-4 text-center text-muted-foreground">
                        No payments recorded yet.
                      </td>
                    </tr>
                  ) : (
                    invoice.payments.map((payment) => <PaymentRow key={payment.id} payment={payment} />)
                  )}
                </tbody>
              </table>
            </div>
          </section>
        </div>
      )}
    </div>
  );
}

function LineItemRow({ item }: { item: InvoiceLineItem }) {
  return (
    <tr>
      <td className="px-4 py-2 text-foreground">{item.description ?? "Line item"}</td>
      <td className="px-4 py-2 text-right text-muted-foreground">{item.quantity}</td>
      <td className="px-4 py-2 text-right text-muted-foreground">{formatCurrency(item.unitPrice)}</td>
      <td className="px-4 py-2 text-right text-muted-foreground">
        {formatCurrency(item.unitPrice * item.quantity)}
      </td>
    </tr>
  );
}

function PaymentRow({ payment }: { payment: InvoicePayment }) {
  return (
    <tr>
      <td className="px-4 py-2 text-muted-foreground">{formatDate(payment.receivedAt)}</td>
      <td className="px-4 py-2 text-muted-foreground">{payment.method}</td>
      <td className="px-4 py-2 text-right text-foreground">{formatCurrency(payment.amount)}</td>
      <td className="px-4 py-2 text-right text-muted-foreground">
        {typeof payment.runningBalance === "number" ? formatCurrency(payment.runningBalance) : "—"}
      </td>
    </tr>
  );
}
