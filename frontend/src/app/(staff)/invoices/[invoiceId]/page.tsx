"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";

import { useFinalizeInvoice, useInvoice, useInvoiceMargin, useManualPayment } from "@/hooks/use-invoices";
import type { InvoiceLineItem, InvoicePayment } from "@/services/invoices";

const paymentMethods = ["CASH", "CHECK", "CARD", "BANK_TRANSFER", "LOYALTY"];

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

export default function InvoiceDetailPage() {
  const params = useParams<{ invoiceId: string }>();
  const invoiceId = Array.isArray(params?.invoiceId) ? params?.invoiceId[0] : params?.invoiceId;
  const { data: invoice, isLoading } = useInvoice(invoiceId ?? "");
  const { data: margin } = useInvoiceMargin(invoiceId ?? "");
  const finalizeMutation = useFinalizeInvoice(invoiceId ?? "");
  const paymentMutation = useManualPayment(invoiceId ?? "");

  const [amount, setAmount] = useState("");
  const [method, setMethod] = useState(paymentMethods[0]);

  const outstandingBalance = useMemo(() => formatCurrency(invoice?.balanceDue ?? null), [invoice?.balanceDue]);

  if (!invoiceId) {
    return (
      <div className="space-y-2 text-sm text-destructive">
        <p>Invoice id missing from the route.</p>
        <Link href="/invoices" className="text-primary underline">
          Back to invoices
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <header className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="space-y-1">
          <Link href="/invoices" className="text-xs text-muted-foreground hover:text-foreground">
            ← Back to invoices
          </Link>
          <h1 className="text-2xl font-semibold text-foreground">Invoice #{invoice?.number ?? invoiceId}</h1>
          <p className="text-sm text-muted-foreground">
            {invoice?.customer?.name ?? "Unassigned"} • Status {invoice ? formatStatus(invoice.status) : "Loading"}
          </p>
        </div>
        <button
          type="button"
          onClick={() => finalizeMutation.mutate()}
          disabled={finalizeMutation.isPending || invoice?.status === "FINALIZED"}
          className="inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground shadow transition hover:bg-primary/90 disabled:cursor-not-allowed disabled:bg-muted"
        >
          {finalizeMutation.isPending ? "Finalizing…" : invoice?.status === "FINALIZED" ? "Finalized" : "Finalize invoice"}
        </button>
      </header>

      {isLoading || !invoice ? (
        <div className="grid gap-4 lg:grid-cols-2">
          {Array.from({ length: 2 }).map((_, index) => (
            <div key={index} className="h-40 animate-pulse rounded-xl bg-muted/40" />
          ))}
        </div>
      ) : (
        <div className="grid gap-6 lg:grid-cols-[2fr_1fr]">
          <section className="space-y-6">
            <div className="grid gap-4 sm:grid-cols-3">
              <DataCard label="Issued" value={formatDate(invoice.issuedDate)} />
              <DataCard label="Due" value={formatDate(invoice.dueDate)} />
              <DataCard label="Outstanding" value={outstandingBalance} highlight />
            </div>

            <div>
              <h2 className="text-lg font-semibold text-foreground">Line items</h2>
              <div className="mt-3 overflow-hidden rounded-md border border-border/60">
                <table className="min-w-full divide-y divide-border/70 text-sm">
                  <thead className="bg-muted/40">
                    <tr>
                      <th className="px-4 py-2 text-left font-medium text-muted-foreground">Description</th>
                      <th className="px-4 py-2 text-right font-medium text-muted-foreground">Qty</th>
                      <th className="px-4 py-2 text-right font-medium text-muted-foreground">Unit Price</th>
                      <th className="px-4 py-2 text-right font-medium text-muted-foreground">Cost</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border/70">
                    {invoice.items.length === 0 ? (
                      <tr>
                        <td colSpan={4} className="px-4 py-4 text-center text-muted-foreground">
                          No items on this invoice.
                        </td>
                      </tr>
                    ) : (
                      invoice.items.map((item) => <LineItemRow key={item.id} item={item} />)
                    )}
                  </tbody>
                </table>
              </div>
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <div className="rounded-md border border-border/60 p-4">
                <h3 className="text-sm font-semibold text-foreground">Totals</h3>
                <dl className="mt-3 space-y-2 text-sm">
                  <div className="flex items-center justify-between">
                    <dt className="text-muted-foreground">Subtotal</dt>
                    <dd className="font-medium text-foreground">{formatCurrency(invoice.subtotal)}</dd>
                  </div>
                  <div className="flex items-center justify-between">
                    <dt className="text-muted-foreground">Tax</dt>
                    <dd className="font-medium text-foreground">{formatCurrency(invoice.tax)}</dd>
                  </div>
                  <div className="flex items-center justify-between">
                    <dt className="text-muted-foreground">Discounts</dt>
                    <dd className="font-medium text-foreground">{formatCurrency(invoice.discountTotal)}</dd>
                  </div>
                  <div className="flex items-center justify-between">
                    <dt className="text-muted-foreground">Late fee</dt>
                    <dd className="font-medium text-foreground">{formatCurrency(invoice.lateFee)}</dd>
                  </div>
                  <div className="flex items-center justify-between border-t border-dashed border-border/60 pt-2">
                    <dt className="text-sm font-semibold text-foreground">Total due</dt>
                    <dd className="text-base font-semibold text-foreground">{formatCurrency(invoice.total + invoice.lateFee)}</dd>
                  </div>
                </dl>
              </div>

              <div className="rounded-md border border-border/60 p-4">
                <h3 className="text-sm font-semibold text-foreground">Loyalty summary</h3>
                <dl className="mt-3 space-y-2 text-sm">
                  <div className="flex items-center justify-between">
                    <dt className="text-muted-foreground">Points earned</dt>
                    <dd className="font-medium text-foreground">{invoice.loyalty.pointsEarned}</dd>
                  </div>
                  <div className="flex items-center justify-between">
                    <dt className="text-muted-foreground">Customer balance</dt>
                    <dd className="font-medium text-foreground">{invoice.loyalty.customerBalance}</dd>
                  </div>
                </dl>
              </div>
            </div>

            <div>
              <h2 className="text-lg font-semibold text-foreground">Payments</h2>
              <div className="mt-3 overflow-hidden rounded-md border border-border/60">
                <table className="min-w-full divide-y divide-border/70 text-sm">
                  <thead className="bg-muted/40">
                    <tr>
                      <th className="px-4 py-2 text-left font-medium text-muted-foreground">Received</th>
                      <th className="px-4 py-2 text-left font-medium text-muted-foreground">Method</th>
                      <th className="px-4 py-2 text-right font-medium text-muted-foreground">Amount</th>
                      <th className="px-4 py-2 text-right font-medium text-muted-foreground">Balance</th>
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
            </div>
          </section>

          <aside className="space-y-6">
            <div className="rounded-md border border-border/60 p-4">
              <h2 className="text-lg font-semibold text-foreground">Margin analysis</h2>
              <p className="mt-1 text-xs text-muted-foreground">
                Gross margin calculated from itemized costs. Threshold {margin?.threshold ?? "—"}%.
              </p>
              <div className="mt-4 space-y-3 text-sm">
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">Parts & labor cost</span>
                  <span className="font-medium text-foreground">{formatCurrency(margin?.total_cost ?? null)}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">Billed amount</span>
                  <span className="font-medium text-foreground">{formatCurrency(margin?.total_price ?? null)}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">Gross margin</span>
                  <span
                    className={`font-semibold ${
                      margin?.is_below_threshold ? "text-red-600" : "text-emerald-600"
                    }`}
                  >
                    {typeof margin?.gross_margin_percent === "number"
                      ? `${margin.gross_margin_percent.toFixed(2)}%`
                      : "—"}
                  </span>
                </div>
              </div>
            </div>

            <div className="rounded-md border border-border/60 p-4">
              <h2 className="text-lg font-semibold text-foreground">Record payment</h2>
              <form
                className="mt-4 space-y-4"
                onSubmit={(event) => {
                  event.preventDefault();
                  const amountValue = Number.parseFloat(amount);
                  if (Number.isNaN(amountValue) || amountValue <= 0) {
                    return;
                  }
                  paymentMutation.mutate({ amount: amountValue, method });
                  setAmount("");
                }}
              >
                <div className="space-y-1">
                  <label htmlFor="amount" className="text-xs font-medium uppercase text-muted-foreground">
                    Amount
                  </label>
                  <input
                    id="amount"
                    name="amount"
                    type="number"
                    step="0.01"
                    min="0"
                    value={amount}
                    onChange={(event) => setAmount(event.target.value)}
                    className="w-full rounded-md border border-border/60 bg-background px-3 py-2 text-sm shadow-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
                    placeholder="0.00"
                    required
                  />
                </div>
                <div className="space-y-1">
                  <label htmlFor="method" className="text-xs font-medium uppercase text-muted-foreground">
                    Method
                  </label>
                  <select
                    id="method"
                    name="method"
                    value={method}
                    onChange={(event) => setMethod(event.target.value)}
                    className="w-full rounded-md border border-border/60 bg-background px-3 py-2 text-sm shadow-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
                  >
                    {paymentMethods.map((value) => (
                      <option key={value} value={value}>
                        {value.replace(/_/g, " ")}
                      </option>
                    ))}
                  </select>
                </div>
                <button
                  type="submit"
                  className="inline-flex w-full items-center justify-center rounded-md bg-primary px-3 py-2 text-sm font-medium text-primary-foreground shadow hover:bg-primary/90 disabled:cursor-not-allowed disabled:bg-muted"
                  disabled={paymentMutation.isPending}
                >
                  {paymentMutation.isPending ? "Saving…" : "Apply payment"}
                </button>
              </form>
            </div>
          </aside>
        </div>
      )}
    </div>
  );
}

function DataCard({ label, value, highlight = false }: { label: string; value: string; highlight?: boolean }) {
  return (
    <div
      className={`rounded-md border border-border/60 p-4 ${
        highlight ? "bg-emerald-500/5 text-emerald-700 dark:text-emerald-300" : "bg-background"
      }`}
    >
      <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">{label}</p>
      <p className="mt-1 text-lg font-semibold text-foreground">{value}</p>
    </div>
  );
}

function LineItemRow({ item }: { item: InvoiceLineItem }) {
  return (
    <tr>
      <td className="px-4 py-2 text-sm text-foreground">{item.description ?? "Line item"}</td>
      <td className="px-4 py-2 text-right text-muted-foreground">{item.quantity}</td>
      <td className="px-4 py-2 text-right text-muted-foreground">{formatCurrency(item.unitPrice)}</td>
      <td className="px-4 py-2 text-right text-muted-foreground">{formatCurrency(item.cost)}</td>
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
