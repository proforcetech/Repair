import type { LowStockPartRow } from "@/services/dashboard-mappers";

type LowStockPartsTableProps = {
  parts: LowStockPartRow[];
};

export function LowStockPartsTable({ parts }: LowStockPartsTableProps) {
  return (
    <div className="rounded-xl border border-border/60 bg-background/80">
      <div className="border-b border-border/60 px-4 py-3">
        <h3 className="text-sm font-semibold text-foreground">Low stock parts</h3>
        <p className="text-xs text-muted-foreground">Parts below reorder minimum based on current inventory.</p>
      </div>
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-border/60 text-sm">
          <thead className="bg-muted/40 text-xs uppercase tracking-wide text-muted-foreground">
            <tr>
              <th scope="col" className="px-4 py-2 text-left">SKU</th>
              <th scope="col" className="px-4 py-2 text-left">Description</th>
              <th scope="col" className="px-4 py-2 text-right">On Hand</th>
              <th scope="col" className="px-4 py-2 text-right">Min</th>
              <th scope="col" className="px-4 py-2 text-right">Suggested Order</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border/60">
            {parts.length === 0 ? (
              <tr>
                <td colSpan={5} className="px-4 py-6 text-center text-xs text-muted-foreground">
                  All parts are currently above threshold.
                </td>
              </tr>
            ) : (
              parts.map((part) => (
                <tr key={part.id} className="hover:bg-accent/50">
                  <td className="px-4 py-3 font-mono text-xs">{part.sku}</td>
                  <td className="px-4 py-3 text-xs text-foreground">{part.description}</td>
                  <td className="px-4 py-3 text-right text-sm font-medium">{part.quantity}</td>
                  <td className="px-4 py-3 text-right text-xs text-muted-foreground">{part.reorderMin}</td>
                  <td className="px-4 py-3 text-right text-sm font-semibold text-primary">
                    {part.suggestedOrder}
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
