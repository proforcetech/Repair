"use client";

import { RestockRecommendationsCard } from "@/components/inventory/restock-recommendations-card";
import { useInventorySummary, useRestockRecommendations } from "@/hooks/use-inventory";

export default function InventoryRestockPage() {
  const restockQuery = useRestockRecommendations();
  const summaryQuery = useInventorySummary();

  return (
    <div className="space-y-6">
      <header className="space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight text-foreground">Restock recommendations</h1>
        <p className="text-sm text-muted-foreground">
          Review projected shortages, plan replenishment, and surface low-stock alerts for the team.
        </p>
      </header>

      <RestockRecommendationsCard items={restockQuery.data} isLoading={restockQuery.isLoading} />

      {summaryQuery.data && (
        <section className="rounded-xl border border-border/60 bg-background/80 p-4">
          <h2 className="text-lg font-semibold text-foreground">Inventory health overview</h2>
          <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <HealthStat label="Total tracked parts" value={summaryQuery.data.total_parts} />
            <HealthStat label="Expired parts" value={summaryQuery.data.expired_parts} />
            <HealthStat
              label="Percent expired"
              value={`${summaryQuery.data.expired_pct.toFixed(1)}%`}
            />
            <HealthStat
              label="Stock value"
              value={new Intl.NumberFormat("en-US", {
                style: "currency",
                currency: "USD",
              }).format(summaryQuery.data.stock_value)}
            />
          </div>
          {summaryQuery.data.reorder_frequency.length > 0 && (
            <div className="mt-6">
              <h3 className="text-sm font-semibold text-foreground">Frequent reorders</h3>
              <p className="text-xs text-muted-foreground">
                Identify SKUs that repeatedly trigger replenishment to negotiate vendor programs.
              </p>
              <div className="mt-3 overflow-hidden rounded-lg border border-border/60">
                <table className="min-w-full divide-y divide-border/60 text-sm">
                  <thead className="bg-muted/40 text-xs uppercase tracking-wide text-muted-foreground">
                    <tr>
                      <th className="px-4 py-2 text-left">SKU</th>
                      <th className="px-4 py-2 text-right">Reorder count</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border/60">
                    {summaryQuery.data.reorder_frequency.slice(0, 10).map((item) => (
                      <tr key={item.sku} className="hover:bg-muted/30">
                        <td className="px-4 py-3 font-mono text-xs text-muted-foreground">{item.sku}</td>
                        <td className="px-4 py-3 text-right text-sm text-foreground">{item.reorderCount}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </section>
      )}
    </div>
  );
}

type HealthStatProps = {
  label: string;
  value: number | string;
};

function HealthStat({ label, value }: HealthStatProps) {
  return (
    <div className="rounded-lg border border-border/60 bg-muted/20 p-4">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="mt-2 text-lg font-semibold text-foreground">{value}</p>
    </div>
  );
}
