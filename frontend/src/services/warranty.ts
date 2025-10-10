import { AxiosRequestConfig } from "axios";

import { apiClient, get, post, put } from "@/lib/api/client";

export type WarrantyClaimSummary = {
  id: string;
  status: string;
  description?: string | null;
  resolutionNotes?: string | null;
  workOrderId?: string | null;
  createdAt?: string | null;
  updatedAt?: string | null;
  firstResponseAt?: string | null;
  attachmentUrl?: string | null;
  customer?: {
    id: string;
    email?: string | null;
    firstName?: string | null;
    lastName?: string | null;
  } | null;
  assignedTo?: {
    id: string;
    email?: string | null;
    firstName?: string | null;
    lastName?: string | null;
  } | null;
};

export type WarrantyComment = {
  id: string;
  claimId: string;
  message: string;
  sender: "CUSTOMER" | "STAFF";
  createdAt: string;
};

export type WarrantyAuditLog = {
  id: string;
  claimId?: string | null;
  actorId?: string | null;
  action: string;
  detail?: string | null;
  timestamp: string;
};

export type WarrantyClaimDetail = {
  claim: WarrantyClaimSummary;
  comments: WarrantyComment[];
  audit_log: WarrantyAuditLog[];
};

export type WarrantyClaimFilters = {
  assigned_to_me?: boolean;
  unassigned?: boolean;
  awaiting_response?: boolean;
};

export type SubmitWarrantyClaimInput = {
  workOrderId: string;
  description: string;
  attachment?: File | null;
};

export type WarrantyStatus = "APPROVED" | "DENIED" | "PENDING" | "OPEN" | "NEEDS_MORE_INFO";

export type UpdateWarrantyStatusInput = {
  status: WarrantyStatus;
  resolutionNotes?: string;
};

export type AssignWarrantyClaimInput = {
  userId: string;
};

export async function submitWarrantyClaim(payload: SubmitWarrantyClaimInput) {
  const formData = new FormData();
  formData.append("work_order_id", payload.workOrderId);
  formData.append("description", payload.description);

  if (payload.attachment) {
    formData.append("file", payload.attachment);
  }

  const config: AxiosRequestConfig = {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  };

  const response = await apiClient.post<{ message: string; claim?: WarrantyClaimSummary }>(
    "/warranty/warranty",
    formData,
    config,
  );
  return response.data;
}

export async function fetchWarrantyClaims(filters: WarrantyClaimFilters = {}) {
  const params = new URLSearchParams();
  if (filters.assigned_to_me) {
    params.set("assigned_to_me", "true");
  }
  if (filters.unassigned) {
    params.set("unassigned", "true");
  }
  if (filters.awaiting_response) {
    params.set("awaiting_response", "true");
  }

  const query = params.toString();
  const url = query ? `/warranty/warranty?${query}` : "/warranty/warranty";
  return get<WarrantyClaimSummary[]>(url);
}

export async function fetchWarrantyClaim(claimId: string) {
  return get<WarrantyClaimDetail>(`/warranty/warranty/${claimId}`);
}

export async function updateWarrantyClaimStatus(claimId: string, input: UpdateWarrantyStatusInput) {
  return put(`/warranty/warranty/${claimId}/status`, {
    status: input.status,
    resolution_notes: input.resolutionNotes ?? null,
  });
}

export async function assignWarrantyClaim(claimId: string, input: AssignWarrantyClaimInput) {
  return put(`/warranty/warranty/${claimId}/assign`, {
    user_id: input.userId,
  });
}

export async function postWarrantyComment(claimId: string, message: string) {
  return post(`/warranty/warranty/${claimId}/comment`, {
    message,
  });
}

export async function fetchWarrantyCommentsAfter(claimId: string, since: string) {
  const params = new URLSearchParams({ since });
  return get<WarrantyComment[]>(`/warranty/warranty/${claimId}/comments/after?${params.toString()}`);
}

export async function fetchWarrantyUnreadCount(claimId: string, lastViewed: string) {
  const params = new URLSearchParams({ last_viewed: lastViewed });
  return get<{ unread_count: number }>(`/warranty/warranty/${claimId}/unread?${params.toString()}`);
}

export async function fetchWarrantyAwaitingResponse() {
  return fetchWarrantyClaims({ awaiting_response: true });
}
