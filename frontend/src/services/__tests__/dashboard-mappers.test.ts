import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  buildSummaryCsv,
  mapAdminSummary,
  mapLowStockParts,
  mapOverdueInvoices,
  mapTechnicianDashboard,
  mapTechnicianPartsSummary,
} from "@/services/dashboard-mappers";
import type { TechnicianDashboardResponse } from "@/services/dashboard";

describe("dashboard mappers", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2024-01-10T12:00:00Z"));
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("maps technician dashboard data", () => {
    const payload: TechnicianDashboardResponse = {
      active_timers: [
        {
          jobId: "job-123",
          startedAt: "2024-01-10T10:00:00Z",
          elapsedSeconds: 3600,
          jobTitle: "Brake replacement",
        },
      ],
      assigned_jobs: [
        {
          id: "job-123",
          title: "Brake replacement",
          status: "IN_PROGRESS",
          dueDate: "2024-01-10T17:00:00Z",
        },
      ],
    };

    const mapped = mapTechnicianDashboard(payload);
    expect(mapped.activeTimers).toHaveLength(1);
    expect(mapped.activeTimers[0]).toMatchObject({
      jobId: "job-123",
      progressPercent: 13,
    });
    expect(mapped.assignedJobs[0].dueDateLabel).toContain("Due");
  });

  it("maps admin summary metrics", () => {
    const metrics = mapAdminSummary({
      open_jobs: 5,
      overdue_invoices: 2,
      parts_to_reorder: 7,
    });
    expect(metrics.map((metric) => metric.value)).toEqual([5, 2, 7]);
  });

  it("maps overdue invoices", () => {
    const invoices = mapOverdueInvoices([
      { id: "INV-1", status: "OVERDUE", total: 123.45 },
    ]);
    expect(invoices[0]).toEqual({ id: "INV-1", status: "OVERDUE", total: 123.45 });
  });

  it("filters and enriches low stock parts", () => {
    const parts = mapLowStockParts([
      {
        id: "part-1",
        sku: "ABC",
        description: "Filter",
        quantity: 2,
        reorderMin: 5,
      },
      {
        id: "part-2",
        sku: "DEF",
        description: "Ignore",
        quantity: 10,
        reorderMin: 2,
      },
    ]);

    expect(parts).toHaveLength(1);
    expect(parts[0].suggestedOrder).toBe(8);
  });

  it("builds CSV with filters", () => {
    const csv = buildSummaryCsv(
      mapAdminSummary({ open_jobs: 1, overdue_invoices: 2, parts_to_reorder: 3 }),
      { status: "IN_PROGRESS", overdueOnly: true },
    );
    expect(csv).toContain("Filter: status");
    expect(csv).toContain("IN_PROGRESS");
  });

  it("maps technician parts summary into notifications", () => {
    const notifications = mapTechnicianPartsSummary({
      parts_received_today: 4,
      parts_received_week: 12,
      events_today: 6,
      events_week: 14,
    });
    expect(notifications).toHaveLength(3);
    expect(notifications[0].severity).toBe("success");
  });
});
