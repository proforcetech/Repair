import { get, post } from "@/lib/api/client";

export interface InventoryPart {
  id: string;
  sku: string;
  name?: string | null;
  description?: string | null;
  quantity: number;
  reorderMin?: number | null;
  reorderMax?: number | null;
  location?: string | null;
  vendor?: string | null;
  cost?: number | null;
}

export interface FetchInventoryPartsParams {
  location?: string;
}

export interface StockTransferPayload {
  partId: string;
  fromLocation: string;
  toLocation: string;
  quantity: number;
  note?: string | null;
}

export interface StockTransferResponse {
  message: string;
}

export interface PartConsumptionPayload {
  jobId: string;
  partId: string;
  quantity: number;
}

export interface PartConsumptionResponse {
  id: string;
  jobId: string;
  partId: string;
  quantity: number;
}

export interface RestockSuggestion {
  sku: string;
  name?: string | null;
  vendor?: string | null;
  quantity_to_order: number;
}

export interface RestockSuggestionsResponse {
  items: RestockSuggestion[];
}

export interface PurchaseOrderRecord {
  id: string;
  vendor?: string | null;
  status?: string | null;
  createdAt?: string | null;
  updatedAt?: string | null;
  emailSent?: boolean;
  items?: Array<{ partId: string; quantity: number; cost?: number | null }>;
}

export interface PurchaseOrderGenerationResponse {
  created: PurchaseOrderRecord[];
}

export interface InventorySummary {
  total_parts: number;
  expired_parts: number;
  expired_pct: number;
  stock_value: number;
  reorder_frequency: Array<{ sku: string; reorderCount: number }>;
  incoming_pos: Array<{
    sku: string;
    description?: string | null;
    expectedArrival?: string | null;
  }>;
}

export async function fetchInventoryParts(params: FetchInventoryPartsParams = {}) {
  return get<InventoryPart[]>("/inventory/parts", {
    params: {
      location: params.location || undefined,
    },
  });
}

export async function transferStock(payload: StockTransferPayload) {
  return post<StockTransferResponse>("/inventory/stock/transfer", payload);
}

export async function consumePart(payload: PartConsumptionPayload) {
  return post<PartConsumptionResponse>("/inventory/consume", payload);
}

export async function fetchRestockSuggestions() {
  return post<RestockSuggestionsResponse>("/inventory/restock-orders/generate");
}

export async function generatePurchaseOrders() {
  return post<PurchaseOrderGenerationResponse>("/inventory/purchase-orders/create");
}

export async function fetchInventorySummary() {
  return get<InventorySummary>("/inventory/summary");
}

export async function downloadPurchaseOrderPdf(poId: string) {
  return get<Blob>(`/inventory/purchase-orders/${poId}/pdf`, {
    responseType: "blob",
  });
}
