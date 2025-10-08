import type { OverdueInvoiceRow } from "@/services/dashboard-mappers";

type OverdueInvoicesTableProps = {
  invoices: OverdueInvoiceRow[];
};

export function OverdueInvoicesTable({ invoices }: OverdueInvoicesTableProps) {
  return (
    <div className="rounded-xl border border-border/60 bg-background/80">
      <div className="border-b border-border/60 px-4 py-3">
        <h3 className="text-sm font-semibold text-foreground">Overdue invoices</h3>
        <p className="text-xs text-muted-foreground">Receivables flagged by the accounting service.</p>
      </div>
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-border/60 text-sm">
          <thead className="bg-muted/40 text-xs uppercase tracking-wide text-muted-foreground">
            <tr>
              <th scope="col" className="px-4 py-2 text-left">Invoice ID</th>
              <th scope="col" className="px-4 py-2 text-left">Status</th>
              <th scope="col" className="px-4 py-2 text-right">Total</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border/60">
            {invoices.length === 0 ? (
              <tr>
                <td colSpan={3} className="px-4 py-6 text-center text-xs text-muted-foreground">
                  All invoices are current. Nice work!
                </td>
              </tr>
            ) : (
              invoices.map((invoice) => (
                <tr key={invoice.id} className="hover:bg-accent/50">
                  <td className="px-4 py-3 font-mono text-xs text-foreground">{invoice.id}</td>
                  <td className="px-4 py-3 text-xs font-medium uppercase text-amber-600 dark:text-amber-400">
                    {invoice.status}
                  </td>
                  <td className="px-4 py-3 text-right text-sm font-semibold text-foreground">
                    ${invoice.total.toFixed(2)}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
