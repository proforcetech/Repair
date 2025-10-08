import { get } from "@/lib/api/client";
import type { NormalizedApiError } from "@/lib/api/client";

export interface TechnicianDashboardResponse {
  assigned_jobs: TechnicianJob[];
  active_timers: RawJobTimer[];
}

export interface TechnicianJob {
  id: string;
  title?: string | null;
  status?: string | null;
  promiseDate?: string | null;
  dueDate?: string | null;
  startedAt?: string | null;
}

export interface RawJobTimer {
  jobId: string;
  startedAt: string;
  elapsedSeconds: number;
  jobTitle?: string | null;
}

export interface AdminSummaryResponse {
  open_jobs: number;
  overdue_invoices: number;
  parts_to_reorder: number;
}

export interface TechnicianUser {
  id: string;
  email: string;
  role: string;
}

export interface PaymentInvoiceSummary {
  id: string;
  status: string;
  total: number;
}

export interface InventoryPart {
  id: string;
  sku: string;
  description?: string | null;
  quantity: number;
  reorderMin?: number | null;
  maxQty?: number | null;
  vendor?: string | null;
}

export interface TechnicianPartsSummaryResponse {
  parts_received_today: number;
  parts_received_week: number;
  events_today: number;
  events_week: number;
}

export interface HighSubstitutionResponse {
  alerted_skus: string[];
}

export interface BayOverloadResponse {
  alerts: Array<{ bay: string; date: string; job_count: number }>;
}

export interface TechnicianOverlapResponse {
  overlap_alerts: Array<{ technician_id: string; date: string; bays: string[] }>;
}

export type AdminSummaryFilters = {
  status?: string;
  technicianId?: string;
  overdueOnly?: boolean;
};

export async function fetchTechnicianDashboard() {
  return get<TechnicianDashboardResponse>("/dashboard");
}

export async function fetchAdminSummary(filters: AdminSummaryFilters) {
  return get<AdminSummaryResponse>("/dashboard/admin/summary", {
    params: {
      job_status: filters.status || undefined,
      overdue_only: filters.overdueOnly ? true : undefined,
      technician_id: filters.technicianId || undefined,
    },
  });
}

export async function fetchOverdueInvoices() {
  return get<PaymentInvoiceSummary[]>("/payment/invoices", {
    params: { status: "overdue" },
  });
}

export async function fetchTechnicians(): Promise<TechnicianUser[]> {
  try {
    return await get<TechnicianUser[]>("/users", {
      params: {
        role: "TECHNICIAN",
        limit: 100,
      },
    });
  } catch (error) {
    const normalized = error as NormalizedApiError;
    if (normalized?.status === 403) {
      return [];
    }
    throw error;
  }
}

export async function fetchLowStockCandidates() {
  return get<InventoryPart[]>("/inventory/parts");
}

export async function fetchTechnicianPartsSummary() {
  return get<TechnicianPartsSummaryResponse>("/dashboard/tech/parts-summary");
}

export async function fetchHighSubstitutionAlerts() {
  return get<HighSubstitutionResponse>("/alerts/alerts/high-substitution-parts");
}

export async function fetchBayOverloadAlerts() {
  return get<BayOverloadResponse>("/alerts/alerts/overutilized-bays");
}

export async function fetchTechnicianOverlapAlerts() {
  return get<TechnicianOverlapResponse>("/alerts/alerts/tech-overlap");
}

export async function fetchOverdueInvoiceCount() {
  return get<AdminSummaryResponse>("/dashboard/admin/summary", {
    params: { overdue_only: true },
  });
}
