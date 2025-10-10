"use client";

import { useMemo } from "react";
import {
  QueryClient,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import {
  consumePart as consumePartRequest,
  fetchInventoryParts,
  fetchInventorySummary,
  fetchPurchaseOrders,
  fetchRestockSuggestions,
  generatePurchaseOrders,
  transferStock as transferStockRequest,
  type FetchInventoryPartsParams,
  type InventoryPart,
  type InventorySummary,
  type PartConsumptionPayload,
  type PurchaseOrderGenerationResponse,
  type PurchaseOrderRecord,
  type RestockSuggestion,
  type StockTransferPayload,
} from "@/services/inventory";
import { showToast } from "@/stores/toast-store";

export const inventoryKeys = {
  parts: (filters: FetchInventoryPartsParams = {}) =>
    ["inventory", "parts", filters] as const,
  restock: () => ["inventory", "restock", "recommendations"] as const,
  summary: () => ["inventory", "summary"] as const,
  purchaseOrders: () => ["inventory", "purchase-orders"] as const,
};

function clampQuantity(quantity: number) {
  if (!Number.isFinite(quantity)) {
    return 0;
  }
  return Math.max(0, Math.floor(quantity));
}

export function validateTransferQuantity(
  quantity: number,
  available: number,
): string | null {
  const normalized = clampQuantity(quantity);
  if (normalized <= 0) {
    return "Quantity must be at least 1";
  }
  if (normalized > available) {
    return `Cannot transfer more than ${available} units`;
  }
  return null;
}

export function validateConsumptionQuantity(
  quantity: number,
  available: number,
): string | null {
  const normalized = clampQuantity(quantity);
  if (normalized <= 0) {
    return "Quantity must be at least 1";
  }
  if (normalized > available) {
    return `Only ${available} units available`; 
  }
  return null;
}

function updatePartQuantityCache(
  queryClient: QueryClient,
  updater: (part: InventoryPart) => InventoryPart,
) {
  const queries = queryClient.getQueryCache().findAll({
    queryKey: ["inventory", "parts"],
  });

  for (const query of queries) {
    const key = query.queryKey as ReturnType<typeof inventoryKeys.parts>;
    queryClient.setQueryData<InventoryPart[] | undefined>(key, (previous) => {
      if (!previous) {
        return previous;
      }
      return previous.map((part) => updater(part));
    });
  }
}

export function useInventoryParts(filters: FetchInventoryPartsParams = {}) {
  return useQuery<InventoryPart[]>({
    queryKey: inventoryKeys.parts(filters),
    queryFn: () => fetchInventoryParts(filters),
    staleTime: 60_000,
  });
}

export function useRestockRecommendations() {
  return useQuery<RestockSuggestion[]>({
    queryKey: inventoryKeys.restock(),
    queryFn: async () => {
      const response = await fetchRestockSuggestions();
      return response.items ?? [];
    },
    staleTime: 60_000,
  });
}

export function useInventorySummary() {
  return useQuery<InventorySummary>({
    queryKey: inventoryKeys.summary(),
    queryFn: fetchInventorySummary,
    staleTime: 5 * 60_000,
  });
}

export function useGeneratedPurchaseOrders() {
  return useQuery<PurchaseOrderRecord[]>({
    queryKey: inventoryKeys.purchaseOrders(),
    queryFn: fetchPurchaseOrders,
    initialData: [],
    staleTime: 2 * 60_000,
  });
}

export function useTransferStock() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: transferStockRequest,
    onSuccess: (response, variables) => {
      updatePartQuantityCache(queryClient, (part) => {
        if (part.id !== variables.partId) {
          return part;
        }
        return {
          ...part,
          quantity: Math.max(part.quantity - variables.quantity, 0),
        };
      });
      queryClient.invalidateQueries({ queryKey: inventoryKeys.summary() });
      showToast({
        title: "Transfer complete",
        description: response.message ?? "Stock transfer recorded",
        variant: "success",
      });
    },
    onError: (error: unknown) => {
      const message =
        typeof error === "object" && error !== null && "message" in error
          ? String((error as { message?: unknown }).message ?? "Unable to transfer stock")
          : "Unable to transfer stock";
      showToast({
        title: "Transfer failed",
        description: message,
        variant: "destructive",
      });
    },
  });
}

export function useConsumePart() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: consumePartRequest,
    onSuccess: (_response, variables) => {
      updatePartQuantityCache(queryClient, (part) => {
        if (part.id !== variables.partId) {
          return part;
        }
        return {
          ...part,
          quantity: Math.max(part.quantity - variables.quantity, 0),
        };
      });
      queryClient.invalidateQueries({ queryKey: inventoryKeys.summary() });
      showToast({
        title: "Part consumed",
        description: "Usage recorded against the job",
        variant: "success",
      });
    },
    onError: (error: unknown) => {
      const message =
        typeof error === "object" && error !== null && "message" in error
          ? String((error as { message?: unknown }).message ?? "Unable to record usage")
          : "Unable to record usage";
      showToast({
        title: "Usage failed",
        description: message,
        variant: "destructive",
      });
    },
  });
}

export function useGeneratePurchaseOrders() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: generatePurchaseOrders,
    onSuccess: (response: PurchaseOrderGenerationResponse) => {
      const created = response.created ?? [];
      queryClient.setQueryData<PurchaseOrderRecord[]>(
        inventoryKeys.purchaseOrders(),
        (existing) => {
          const previous = existing ?? [];
          if (created.length === 0) {
            return previous;
          }

          const next: PurchaseOrderRecord[] = [...created];
          const seen = new Set(created.map((po) => po.id));
          for (const record of previous) {
            if (!seen.has(record.id)) {
              next.push(record);
            }
          }
          return next;
        },
      );
      queryClient.invalidateQueries({ queryKey: inventoryKeys.purchaseOrders() });
      queryClient.invalidateQueries({ queryKey: inventoryKeys.summary() });
      showToast({
        title: "Purchase orders generated",
        description: created.length
          ? `${created.length} vendor orders queued and email notifications sent`
          : "No purchase orders were required",
        variant: created.length ? "success" : "warning",
      });
    },
    onError: (error: unknown) => {
      const message =
        typeof error === "object" && error !== null && "message" in error
          ? String((error as { message?: unknown }).message ?? "Unable to generate purchase orders")
          : "Unable to generate purchase orders";
      showToast({
        title: "Generation failed",
        description: message,
        variant: "destructive",
      });
    },
  });
}

export function useRestockByVendor(recommendations: RestockSuggestion[] | undefined) {
  return useMemo(() => {
    const groups = new Map<string, RestockSuggestion[]>();
    for (const item of recommendations ?? []) {
      const vendor = item.vendor ?? "Unassigned";
      const current = groups.get(vendor) ?? [];
      current.push(item);
      groups.set(vendor, current);
    }
    return Array.from(groups.entries()).map(([vendor, items]) => ({
      vendor,
      items,
      totalQuantity: items.reduce((total, entry) => total + (entry.quantity_to_order ?? 0), 0),
    }));
  }, [recommendations]);
}
