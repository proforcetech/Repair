import { get, post, put } from "@/lib/api/client";

export type EstimateStatus =
  | "DRAFT"
  | "PENDING_CUSTOMER_APPROVAL"
  | "APPROVED"
  | "REJECTED";

export type EstimateItem = {
  id: string;
  description: string;
  cost: number;
  partId?: string | null;
  qty?: number | null;
  createdAt?: string;
  updatedAt?: string;
};

export type Estimate = {
  id: string;
  customerId: string;
  vehicleId: string;
  status: EstimateStatus;
  total: number;
  createdAt: string;
  updatedAt?: string;
  expiresAt?: string | null;
  items: EstimateItem[];
};

export type EstimateSummary = Pick<Estimate, "id" | "status" | "total" | "createdAt"> & {
  customerName?: string | null;
  vehicleLabel?: string | null;
};

export type EstimateItemCreate = {
  description: string;
  cost: number;
  part_id?: string | null;
  qty?: number | null;
};

export type EstimateCreateInput = {
  vehicle_id: string;
  items: EstimateItemCreate[];
};

export type LaborItemDraft = {
  kind: "labor";
  description: string;
  hours: number;
  rate: number;
};

export type PartItemDraft = {
  kind: "part";
  description: string;
  unitPrice: number;
  quantity: number;
  partNumber?: string;
};

export type EstimateItemDraft = LaborItemDraft | PartItemDraft;

export type EstimateTotals = {
  laborTotal: number;
  partsTotal: number;
  total: number;
};

export type EstimateAction =
  | "request_customer_approval"
  | "approve"
  | "reject"
  | "reset";

export function calculateDraftCost(item: EstimateItemDraft): number {
  if (item.kind === "labor") {
    return Number.isFinite(item.hours) && Number.isFinite(item.rate)
      ? Math.max(0, item.hours) * Math.max(0, item.rate)
      : 0;
  }

  return Number.isFinite(item.unitPrice) && Number.isFinite(item.quantity)
    ? Math.max(0, item.unitPrice) * Math.max(0, item.quantity)
    : 0;
}

export function draftToEstimateItem(item: EstimateItemDraft): EstimateItemCreate {
  if (item.kind === "labor") {
    return {
      description: item.description,
      cost: calculateDraftCost(item),
    };
  }

  return {
    description: item.description,
    cost: calculateDraftCost(item),
    part_id: item.partNumber?.trim() ? item.partNumber.trim() : undefined,
    qty: item.quantity,
  };
}

export function calculateEstimateTotals(items: EstimateItemDraft[]): EstimateTotals {
  return items.reduce<EstimateTotals>(
    (totals, item) => {
      const cost = calculateDraftCost(item);
      if (item.kind === "labor") {
        const laborTotal = totals.laborTotal + cost;
        return {
          laborTotal,
          partsTotal: totals.partsTotal,
          total: laborTotal + totals.partsTotal,
        };
      }

      const partsTotal = totals.partsTotal + cost;
      return {
        laborTotal: totals.laborTotal,
        partsTotal,
        total: totals.laborTotal + partsTotal,
      };
    },
    { laborTotal: 0, partsTotal: 0, total: 0 },
  );
}

export function transitionEstimateStatus(
  current: EstimateStatus,
  action: EstimateAction,
): EstimateStatus {
  switch (action) {
    case "approve":
      return "APPROVED";
    case "reject":
      return "REJECTED";
    case "request_customer_approval":
      return "PENDING_CUSTOMER_APPROVAL";
    case "reset":
      return "DRAFT";
    default:
      return current;
  }
}

export async function listEstimates() {
  return get<EstimateSummary[]>("/estimates");
}

export async function getEstimate(estimateId: string) {
  return get<Estimate>(`/estimates/${estimateId}`);
}

export async function createEstimate(input: EstimateCreateInput) {
  return post<Estimate>("/estimates", input);
}

export async function addEstimateItem(
  estimateId: string,
  item: EstimateItemCreate,
) {
  return post<EstimateItem>(`/estimates/${estimateId}/items`, item);
}

export async function updateEstimateStatus(
  estimateId: string,
  status: EstimateStatus,
) {
  return put<{ message: string; estimate: Estimate }>(
    `/estimates/${estimateId}/status`,
    undefined,
    { params: { status } },
  );
}

export async function approveEstimate(estimateId: string) {
  return put<{ message: string; estimate: Estimate }>(
    `/estimates/${estimateId}/approve`,
  );
}

export async function rejectEstimate(estimateId: string) {
  return put<{ message: string; estimate: Estimate }>(
    `/estimates/${estimateId}/reject`,
  );
}

export async function duplicateEstimate(estimateId: string) {
  return post<{ message: string; estimate: Estimate }>(
    `/estimates/${estimateId}/duplicate`,
  );
}

export async function applyTemplateToEstimate(
  estimateId: string,
  templateId: string,
) {
  return post<{ message: string }>(
    `/estimates/${estimateId}/apply-template/${templateId}`,
  );
}
