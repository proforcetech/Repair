"use client";

import { useMemo, useState } from "react";

import { PurchaseOrderSummary } from "@/components/inventory/purchase-order-summary";
import { RestockRecommendationsCard } from "@/components/inventory/restock-recommendations-card";
import {
  useGeneratePurchaseOrders,
  useGeneratedPurchaseOrders,
  useInventorySummary,
  useRestockByVendor,
  useRestockRecommendations,
} from "@/hooks/use-inventory";
import { downloadPurchaseOrderPdf } from "@/services/inventory";
import { showToast } from "@/stores/toast-store";

export default function InventoryPurchaseOrdersPage() {
  const [exportingId, setExportingId] = useState<string | null>(null);
  const restockQuery = useRestockRecommendations();
  const summaryQuery = useInventorySummary();
  const purchaseOrdersQuery = useGeneratedPurchaseOrders();
  const generateMutation = useGeneratePurchaseOrders();

  const vendorGroups = useRestockByVendor(restockQuery.data);

  const totalVendors = useMemo(() => vendorGroups.length, [vendorGroups]);

  const handleGenerate = async () => {
    await generateMutation.mutateAsync();
  };

  const handleExport = async (poId: string) => {
    setExportingId(poId);
    try {
      const blob = await downloadPurchaseOrderPdf(poId);
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `purchase-order-${poId}.pdf`;
      anchor.click();
      URL.revokeObjectURL(url);
      showToast({
        title: "Export ready",
        description: "Purchase order PDF downloaded",
        variant: "success",
      });
    } catch (error) {
      const message =
        typeof error === "object" && error !== null && "message" in error
          ? String((error as { message?: unknown }).message ?? "Unable to export PDF")
          : "Unable to export PDF";
      showToast({
        title: "Export failed",
        description: message,
        variant: "destructive",
      });
    } finally {
      setExportingId(null);
    }
  };

  return (
    <div className="space-y-6">
      <header className="space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight text-foreground">Purchase order generation</h1>
        <p className="text-sm text-muted-foreground">
          Build vendor-ready purchase orders from low stock signals, then export PDFs or trigger downstream workflows.
        </p>
      </header>

      <section className="rounded-xl border border-border/60 bg-background/80 p-4 shadow-sm">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 className="text-lg font-semibold text-foreground">Restock vendor summary</h2>
            <p className="text-xs text-muted-foreground">
              {restockQuery.isLoading
                ? "Compiling vendor recommendations…"
                : totalVendors === 0
                  ? "All vendors are stocked above reorder thresholds."
                  : `${totalVendors} vendors require replenishment.`}
            </p>
          </div>
          <button
            type="button"
            onClick={handleGenerate}
            className="inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
            disabled={generateMutation.isPending}
          >
            {generateMutation.isPending ? "Generating…" : "Generate purchase orders"}
          </button>
        </div>
        {vendorGroups.length > 0 && (
          <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {vendorGroups.map((group) => (
              <div key={group.vendor} className="rounded-lg border border-border/60 bg-muted/20 p-4">
                <h3 className="text-sm font-semibold text-foreground">{group.vendor}</h3>
                <p className="text-xs text-muted-foreground">{group.totalQuantity} total units suggested</p>
                <ul className="mt-3 space-y-2 text-xs text-muted-foreground">
                  {group.items.slice(0, 4).map((item) => (
                    <li key={`${item.sku}-${item.quantity_to_order}`} className="flex justify-between gap-2">
                      <span className="truncate">{item.name ?? item.sku}</span>
                      <span className="font-medium text-foreground">×{item.quantity_to_order}</span>
                    </li>
                  ))}
                </ul>
                {group.items.length > 4 && (
                  <p className="mt-2 text-[11px] text-muted-foreground">+{group.items.length - 4} more lines</p>
                )}
              </div>
            ))}
          </div>
        )}
      </section>

      <div className="grid gap-6 lg:grid-cols-2">
        <RestockRecommendationsCard items={restockQuery.data} isLoading={restockQuery.isLoading} />
        <PurchaseOrderSummary
          purchaseOrders={purchaseOrdersQuery.data}
          onExport={handleExport}
          exportingId={exportingId}
        />
      </div>

      {summaryQuery.data?.incoming_pos && summaryQuery.data.incoming_pos.length > 0 && (
        <section className="space-y-3">
          <h2 className="text-lg font-semibold text-foreground">Incoming deliveries</h2>
          <p className="text-xs text-muted-foreground">
            Monitor expected arrivals to coordinate receiving and technician scheduling.
          </p>
          <div className="overflow-hidden rounded-lg border border-border/60">
            <table className="min-w-full divide-y divide-border/60 text-sm">
              <thead className="bg-muted/40 text-xs uppercase tracking-wide text-muted-foreground">
                <tr>
                  <th className="px-4 py-2 text-left">SKU</th>
                  <th className="px-4 py-2 text-left">Description</th>
                  <th className="px-4 py-2 text-left">Expected arrival</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/60">
                {summaryQuery.data.incoming_pos.map((item) => (
                  <tr key={`${item.sku}-${item.expectedArrival ?? "unknown"}`} className="hover:bg-muted/30">
                    <td className="px-4 py-3 font-mono text-xs text-muted-foreground">{item.sku}</td>
                    <td className="px-4 py-3 text-sm text-foreground">{item.description ?? "—"}</td>
                    <td className="px-4 py-3 text-sm text-muted-foreground">{item.expectedArrival ?? "TBD"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </div>
  );
}
