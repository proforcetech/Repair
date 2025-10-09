"use client";

import Link from "next/link";

import { useInvoices } from "@/hooks/use-invoices";
import type { InvoiceSummary } from "@/services/invoices";

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

const statusClasses: Record<string, string> = {
  DRAFT: "bg-slate-200 text-slate-700",
  SENT: "bg-blue-100 text-blue-700",
  FINALIZED: "bg-violet-100 text-violet-700",
  PARTIALLY_PAID: "bg-amber-100 text-amber-700",
  PAID: "bg-emerald-100 text-emerald-700",
  VOID: "bg-red-100 text-red-700",
};

function StatusBadge({ status }: { status: string }) {
  const classes = statusClasses[status] ?? "bg-slate-200 text-slate-700";
  return (
    <span className={`inline-flex items-center rounded-full px-2 py-1 text-xs font-medium ${classes}`}>
      {formatStatus(status)}
    </span>
  );
}

export default function InvoicesPage() {
  const { data: invoices, isLoading, isError } = useInvoices();

  return (
    <div className="space-y-6">
      <header className="space-y-1">
        <h1 className="text-2xl font-semibold text-foreground">Invoices</h1>
        <p className="text-sm text-muted-foreground">
          Monitor billing statuses, outstanding balances, and follow-up needs in one place.
        </p>
      </header>

      <div className="overflow-hidden rounded-md border border-border/70 bg-background shadow-sm">
        <table className="min-w-full divide-y divide-border/70 text-sm">
          <thead className="bg-muted/50">
            <tr>
              <th className="px-4 py-3 text-left font-medium text-muted-foreground">Invoice</th>
              <th className="px-4 py-3 text-left font-medium text-muted-foreground">Customer</th>
              <th className="px-4 py-3 text-left font-medium text-muted-foreground">Issued</th>
              <th className="px-4 py-3 text-left font-medium text-muted-foreground">Due</th>
              <th className="px-4 py-3 text-left font-medium text-muted-foreground">Status</th>
              <th className="px-4 py-3 text-right font-medium text-muted-foreground">Total</th>
              <th className="px-4 py-3 text-right font-medium text-muted-foreground">Balance</th>
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
                  Unable to load invoices. Please try again shortly.
                </td>
              </tr>
            )}
            {!isLoading && !isError && invoices && invoices.length === 0 && (
              <tr>
                <td colSpan={7} className="px-4 py-6 text-center text-muted-foreground">
                  No invoices yet. Finalize jobs to begin billing customers.
                </td>
              </tr>
            )}
            {!isLoading && !isError &&
              invoices?.map((invoice) => <InvoiceRow key={invoice.id} invoice={invoice} />)}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function InvoiceRow({ invoice }: { invoice: InvoiceSummary }) {
  return (
    <tr className="hover:bg-muted/30">
      <td className="px-4 py-3">
        <Link href={`/invoices/${invoice.id}`} className="font-semibold text-primary hover:underline">
          #{invoice.number}
        </Link>
      </td>
      <td className="px-4 py-3 text-muted-foreground">{invoice.customer?.name ?? "—"}</td>
      <td className="px-4 py-3 text-muted-foreground">{formatDate(invoice.issuedDate)}</td>
      <td className="px-4 py-3 text-muted-foreground">{formatDate(invoice.dueDate)}</td>
      <td className="px-4 py-3">
        <StatusBadge status={invoice.status} />
      </td>
      <td className="px-4 py-3 text-right font-medium text-foreground">{formatCurrency(invoice.total)}</td>
      <td className="px-4 py-3 text-right font-medium text-foreground">
        {formatCurrency(invoice.balanceDue)}
      </td>
    </tr>
  );
}
