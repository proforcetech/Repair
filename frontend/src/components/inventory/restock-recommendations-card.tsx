import type { RestockSuggestion } from "@/services/inventory";

type RestockRecommendationsCardProps = {
  items: RestockSuggestion[] | undefined;
  isLoading?: boolean;
};

export function RestockRecommendationsCard({ items, isLoading = false }: RestockRecommendationsCardProps) {
  return (
    <div className="rounded-xl border border-border/60 bg-background/80">
      <div className="border-b border-border/60 px-4 py-3">
        <h3 className="text-sm font-semibold text-foreground">Restock recommendations</h3>
        <p className="text-xs text-muted-foreground">
          Suggested replenishment quantities grouped by vendor priority.
        </p>
      </div>
      <div className="divide-y divide-border/60">
        {isLoading && (
          <div className="px-4 py-6 text-sm text-muted-foreground">Calculating reorder suggestions…</div>
        )}
        {!isLoading && (items?.length ?? 0) === 0 && (
          <div className="px-4 py-6 text-sm text-muted-foreground">All parts are within healthy stock ranges.</div>
        )}
        {!isLoading &&
          items?.map((item) => (
            <div key={`${item.sku}-${item.vendor ?? "unknown"}`} className="px-4 py-3">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <p className="text-sm font-medium text-foreground">{item.name ?? item.sku}</p>
                  <p className="text-xs text-muted-foreground">Vendor: {item.vendor ?? "Unassigned"}</p>
                </div>
                <span className="inline-flex h-8 min-w-[3.5rem] items-center justify-center rounded-md bg-primary/10 px-3 text-sm font-semibold text-primary">
                  {item.quantity_to_order}
                </span>
              </div>
            </div>
          ))}
      </div>
    </div>
  );
}
