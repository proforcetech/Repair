"use client";

import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";

import {
  fetchAdminSummary,
  fetchBayOverloadAlerts,
  fetchHighSubstitutionAlerts,
  fetchLowStockCandidates,
  fetchOverdueInvoiceCount,
  fetchOverdueInvoices,
  fetchTechnicianDashboard,
  fetchTechnicianOverlapAlerts,
  fetchTechnicianPartsSummary,
  fetchTechnicians,
} from "@/services/dashboard";
import type { AdminSummaryFilters } from "@/services/dashboard";
import {
  buildSummaryCsv,
  mapAdminSummary,
  mapLowStockParts,
  mapOverdueInvoices,
  mapTechnicianDashboard,
  mapTechnicianPartsSummary,
} from "@/services/dashboard-mappers";
import type {
  AdminSummaryMetric,
  DashboardNotification,
  LowStockPartRow,
  OverdueInvoiceRow,
  TechnicianDashboardView,
} from "@/services/dashboard-mappers";

export function useTechnicianDashboard(enabled = true) {
  return useQuery<TechnicianDashboardView>({
    queryKey: ["dashboard", "technician"],
    queryFn: async () => {
      const response = await fetchTechnicianDashboard();
      return mapTechnicianDashboard(response);
    },
    enabled,
  });
}

export function useAdminSummary(filters: AdminSummaryFilters, enabled = true) {
  return useQuery<AdminSummaryMetric[]>({
    queryKey: ["dashboard", "admin-summary", filters],
    queryFn: async () => {
      const response = await fetchAdminSummary(filters);
      return mapAdminSummary(response);
    },
    enabled,
    staleTime: 60_000,
  });
}

export function useOverdueInvoices(enabled = true) {
  return useQuery<OverdueInvoiceRow[]>({
    queryKey: ["dashboard", "overdue-invoices"],
    queryFn: async () => {
      const response = await fetchOverdueInvoices();
      return mapOverdueInvoices(response);
    },
    enabled,
    staleTime: 30_000,
  });
}

export function useLowStockParts(enabled = true) {
  return useQuery<LowStockPartRow[]>({
    queryKey: ["dashboard", "low-stock-parts"],
    queryFn: async () => {
      const parts = await fetchLowStockCandidates();
      return mapLowStockParts(parts);
    },
    enabled,
    staleTime: 60_000,
  });
}

export function useTechnicianOptions() {
  return useQuery({
    queryKey: ["dashboard", "technicians"],
    queryFn: async () => {
      const technicians = await fetchTechnicians();
      return technicians.map((tech) => ({ value: tech.id, label: tech.email }));
    },
    staleTime: 5 * 60_000,
  });
}

export function useDashboardNotifications(role: string | null) {
  return useQuery<DashboardNotification[]>({
    queryKey: ["dashboard", "notifications", role],
    queryFn: async () => {
      if (!role) {
        return [];
      }

      if (role === "TECHNICIAN") {
        const summary = await fetchTechnicianPartsSummary();
        return mapTechnicianPartsSummary(summary);
      }

      const [subs, bays, overlap, overdue] = await Promise.allSettled([
        fetchHighSubstitutionAlerts(),
        fetchBayOverloadAlerts(),
        fetchTechnicianOverlapAlerts(),
        fetchOverdueInvoiceCount(),
      ]);

      const notifications: DashboardNotification[] = [];

      if (subs.status === "fulfilled" && subs.value.alerted_skus.length > 0) {
        notifications.push({
          id: "substitution-alert",
          title: "High substitution volume",
          description: `${subs.value.alerted_skus.length} SKUs need review`,
          severity: "warning",
        });
      }

      if (bays.status === "fulfilled" && bays.value.alerts.length > 0) {
        const latest = bays.value.alerts[0];
        notifications.push({
          id: "bay-overload",
          title: "Bay capacity warning",
          description: `${latest.bay} handled ${latest.job_count} jobs on ${latest.date}`,
          severity: "info",
        });
      }

      if (overlap.status === "fulfilled" && overlap.value.overlap_alerts.length > 0) {
        notifications.push({
          id: "tech-overlap",
          title: "Technician double-booked",
          description: `${overlap.value.overlap_alerts.length} technicians need schedule review`,
          severity: "warning",
        });
      }

      if (
        overdue.status === "fulfilled" &&
        (overdue.value.overdue_invoices ?? 0) > 0
      ) {
        notifications.push({
          id: "overdue-invoices",
          title: "Overdue invoices",
          description: `${overdue.value.overdue_invoices} receivables require follow-up`,
          severity: "info",
        });
      }

      return notifications;
    },
    staleTime: 5 * 60_000,
  });
}

export function useSummaryCsv(metrics: AdminSummaryMetric[], filters: AdminSummaryFilters) {
  return useMemo(() => buildSummaryCsv(metrics, filters), [metrics, filters]);
}
