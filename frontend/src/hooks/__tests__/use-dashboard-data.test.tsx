import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import {
  useAdminSummary,
  useDashboardNotifications,
  useTechnicianDashboard,
} from "@/hooks/use-dashboard-data";
import {
  fetchAdminSummary,
  fetchBayOverloadAlerts,
  fetchHighSubstitutionAlerts,
  fetchOverdueInvoiceCount,
  fetchTechnicianDashboard,
  fetchTechnicianOverlapAlerts,
  fetchTechnicianPartsSummary,
} from "@/services/dashboard";

vi.mock("@/services/dashboard", () => ({
  fetchTechnicianDashboard: vi.fn().mockResolvedValue({
    active_timers: [
      {
        jobId: "job-1",
        startedAt: "2024-01-10T10:00:00Z",
        elapsedSeconds: 1200,
        jobTitle: "Oil change",
      },
    ],
    assigned_jobs: [
      { id: "job-1", title: "Oil change", status: "IN_PROGRESS", dueDate: "2024-01-10T13:00:00Z" },
    ],
  }),
  fetchAdminSummary: vi.fn().mockResolvedValue({
    open_jobs: 4,
    overdue_invoices: 2,
    parts_to_reorder: 3,
  }),
  fetchOverdueInvoices: vi.fn().mockResolvedValue([]),
  fetchLowStockCandidates: vi.fn().mockResolvedValue([]),
  fetchTechnicians: vi.fn().mockResolvedValue([{ id: "tech-1", email: "tech@example.com", role: "TECHNICIAN" }]),
  fetchTechnicianPartsSummary: vi.fn().mockResolvedValue({
    parts_received_today: 1,
    parts_received_week: 5,
    events_today: 2,
    events_week: 6,
  }),
  fetchHighSubstitutionAlerts: vi.fn().mockResolvedValue({ alerted_skus: ["SKU-1"] }),
  fetchBayOverloadAlerts: vi.fn().mockResolvedValue({ alerts: [{ bay: "A1", date: "2024-01-09", job_count: 12 }] }),
  fetchTechnicianOverlapAlerts: vi.fn().mockResolvedValue({ overlap_alerts: [{ technician_id: "t1", date: "2024-01-09", bays: ["A1"] }] }),
  fetchOverdueInvoiceCount: vi.fn().mockResolvedValue({
    open_jobs: 0,
    overdue_invoices: 5,
    parts_to_reorder: 0,
  }),
}));

afterEach(() => {
  vi.clearAllMocks();
});

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });

  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}

describe("useTechnicianDashboard", () => {
  it("returns mapped technician data", async () => {
    const wrapper = createWrapper();
    const { result } = renderHook(() => useTechnicianDashboard(), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.activeTimers).toHaveLength(1);
    expect(fetchTechnicianDashboard).toHaveBeenCalled();
  });
});

describe("useAdminSummary", () => {
  it("requests data with provided filters", async () => {
    const wrapper = createWrapper();
    const filters = { status: "IN_PROGRESS", overdueOnly: true, technicianId: "tech-1" };
    const { result } = renderHook(() => useAdminSummary(filters), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(fetchAdminSummary).toHaveBeenCalledWith(filters);
    expect(result.current.data?.[0].value).toBe(4);
  });
});

describe("useDashboardNotifications", () => {
  it("maps technician notifications", async () => {
    const wrapper = createWrapper();
    const { result } = renderHook(() => useDashboardNotifications("TECHNICIAN"), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(fetchTechnicianPartsSummary).toHaveBeenCalled();
    expect(result.current.data?.[0].title).toContain("Parts");
  });

  it("aggregates admin notifications", async () => {
    const wrapper = createWrapper();
    const { result } = renderHook(() => useDashboardNotifications("ADMIN"), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(fetchHighSubstitutionAlerts).toHaveBeenCalled();
    expect(fetchBayOverloadAlerts).toHaveBeenCalled();
    expect(fetchTechnicianOverlapAlerts).toHaveBeenCalled();
    expect(fetchOverdueInvoiceCount).toHaveBeenCalled();
    expect(result.current.data?.length).toBeGreaterThan(0);
  });
});
