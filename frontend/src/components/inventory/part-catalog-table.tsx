import type { InventoryPart } from "@/services/inventory";

type PartCatalogTableProps = {
  parts: InventoryPart[] | undefined;
  isLoading?: boolean;
  error?: string | null;
  onTransfer?: (part: InventoryPart) => void;
  onConsume?: (part: InventoryPart) => void;
};

export function PartCatalogTable({
  parts,
  isLoading = false,
  error,
  onTransfer,
  onConsume,
}: PartCatalogTableProps) {
  const hasActions = Boolean(onTransfer || onConsume);

  return (
    <div className="overflow-hidden rounded-lg border border-border/70 bg-background shadow-sm">
      <table className="min-w-full divide-y divide-border/70 text-sm">
        <thead className="bg-muted/50 text-xs uppercase tracking-wide text-muted-foreground">
          <tr>
            <th scope="col" className="px-4 py-2 text-left">
              SKU
            </th>
            <th scope="col" className="px-4 py-2 text-left">
              Description
            </th>
            <th scope="col" className="px-4 py-2 text-left">
              Location
            </th>
            <th scope="col" className="px-4 py-2 text-right">
              On hand
            </th>
            <th scope="col" className="px-4 py-2 text-right">
              Min
            </th>
            <th scope="col" className="px-4 py-2 text-left">
              Vendor
            </th>
            {hasActions && (
              <th scope="col" className="px-4 py-2 text-right">
                Actions
              </th>
            )}
          </tr>
        </thead>
        <tbody className="divide-y divide-border/70">
          {isLoading && (
            <tr>
              <td colSpan={hasActions ? 7 : 6} className="px-4 py-6 text-center text-sm text-muted-foreground">
                Loading parts…
              </td>
            </tr>
          )}
          {error && !isLoading && (
            <tr>
              <td colSpan={hasActions ? 7 : 6} className="px-4 py-6 text-center text-sm text-destructive">
                {error}
              </td>
            </tr>
          )}
          {!isLoading && !error && (parts?.length ?? 0) === 0 && (
            <tr>
              <td colSpan={hasActions ? 7 : 6} className="px-4 py-6 text-center text-sm text-muted-foreground">
                No parts found. Adjust filters or sync your catalog.
              </td>
            </tr>
          )}
          {!isLoading && !error &&
            parts?.map((part) => {
              const belowMin =
                typeof part.reorderMin === "number" && part.reorderMin !== null && part.quantity < part.reorderMin;
              return (
                <tr key={`${part.id}-${part.location ?? "default"}`} className="hover:bg-muted/30">
                  <td className="px-4 py-3 font-mono text-xs text-muted-foreground">{part.sku}</td>
                  <td className="px-4 py-3 text-sm text-foreground">
                    {part.description || part.name || "Unlabeled part"}
                  </td>
                  <td className="px-4 py-3 text-sm text-muted-foreground">{part.location ?? "Default"}</td>
                  <td className="px-4 py-3 text-right text-sm font-semibold text-foreground">
                    {part.quantity}
                  </td>
                  <td className="px-4 py-3 text-right text-xs text-muted-foreground">
                    {typeof part.reorderMin === "number" && part.reorderMin !== null ? part.reorderMin : "—"}
                  </td>
                  <td className="px-4 py-3 text-sm text-muted-foreground">{part.vendor ?? "—"}</td>
                  {hasActions && (
                    <td className="px-4 py-3">
                      <div className="flex justify-end gap-2">
                        {onTransfer && (
                          <button
                            type="button"
                            onClick={() => onTransfer(part)}
                            className="inline-flex items-center rounded-md border border-border/70 px-3 py-1 text-xs font-medium text-foreground transition-colors hover:bg-accent"
                          >
                            Transfer
                          </button>
                        )}
                        {onConsume && (
                          <button
                            type="button"
                            onClick={() => onConsume(part)}
                            className="inline-flex items-center rounded-md border border-border/70 px-3 py-1 text-xs font-medium text-foreground transition-colors hover:bg-accent"
                          >
                            Consume
                          </button>
                        )}
                      </div>
                      {belowMin && (
                        <p className="mt-2 text-right text-[11px] text-amber-600">
                          Below minimum threshold
                        </p>
                      )}
                    </td>
                  )}
                </tr>
              );
            })}
        </tbody>
      </table>
    </div>
  );
}
