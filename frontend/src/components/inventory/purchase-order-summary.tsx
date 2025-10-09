import { formatDistanceToNow } from "date-fns";

import type { PurchaseOrderRecord } from "@/services/inventory";

type PurchaseOrderSummaryProps = {
  purchaseOrders: PurchaseOrderRecord[] | undefined;
  onExport: (purchaseOrderId: string) => void;
  exportingId?: string | null;
};

function formatStatus(status?: string | null) {
  if (!status) return "DRAFT";
  return status
    .toLowerCase()
    .split("_")
    .map((segment) => segment.charAt(0).toUpperCase() + segment.slice(1))
    .join(" ");
}

export function PurchaseOrderSummary({
  purchaseOrders,
  onExport,
  exportingId,
}: PurchaseOrderSummaryProps) {
  return (
    <div className="rounded-xl border border-border/60 bg-background/80">
      <div className="border-b border-border/60 px-4 py-3">
        <h3 className="text-sm font-semibold text-foreground">Generated purchase orders</h3>
        <p className="text-xs text-muted-foreground">
          Track approval status, export PDFs, and monitor vendor notifications.
        </p>
      </div>
      <div className="divide-y divide-border/60">
        {(purchaseOrders?.length ?? 0) === 0 ? (
          <div className="px-4 py-6 text-sm text-muted-foreground">
            Generate purchase orders to see vendor summaries here.
          </div>
        ) : (
          purchaseOrders?.map((po) => {
            const createdAt = po.createdAt ? new Date(po.createdAt) : null;
            const relative = createdAt ? formatDistanceToNow(createdAt, { addSuffix: true }) : "Recently";
            return (
              <div key={po.id} className="px-4 py-3">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <p className="text-sm font-semibold text-foreground">PO #{po.id.slice(0, 8)}</p>
                    <p className="text-xs text-muted-foreground">Vendor: {po.vendor ?? "Unassigned"}</p>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="inline-flex items-center rounded-full bg-primary/10 px-3 py-1 text-xs font-medium text-primary">
                      {formatStatus(po.status)}
                    </span>
                    <span className="text-xs text-muted-foreground">{relative}</span>
                  </div>
                </div>
                <div className="mt-3 flex flex-wrap items-center justify-between gap-3 text-xs text-muted-foreground">
                  <p>{po.items?.length ?? 0} line items</p>
                  {po.emailSent && <p className="text-emerald-600">Vendor email sent</p>}
                  <button
                    type="button"
                    onClick={() => onExport(po.id)}
                    className="inline-flex items-center rounded-md border border-border px-3 py-1 text-xs font-medium text-foreground transition-colors hover:bg-accent"
                    disabled={exportingId === po.id}
                  >
                    {exportingId === po.id ? "Preparing…" : "Export PDF"}
                  </button>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
