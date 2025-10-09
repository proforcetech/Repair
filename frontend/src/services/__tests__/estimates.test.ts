import { describe, expect, it } from "vitest";

import {
  EstimateStatus,
  calculateDraftCost,
  calculateEstimateTotals,
  draftToEstimateItem,
  transitionEstimateStatus,
} from "@/services/estimates";

describe("estimate draft calculations", () => {
  it("calculates cost for labor items", () => {
    const cost = calculateDraftCost({
      kind: "labor",
      description: "Brake inspection",
      hours: 2,
      rate: 110,
    });

    expect(cost).toBe(220);
  });

  it("treats negative values as zero for labor", () => {
    const cost = calculateDraftCost({
      kind: "labor",
      description: "Adjustment",
      hours: -2,
      rate: 100,
    });

    expect(cost).toBe(0);
  });

  it("calculates cost for part items", () => {
    const cost = calculateDraftCost({
      kind: "part",
      description: "Brake pad set",
      unitPrice: 45,
      quantity: 2,
    });

    expect(cost).toBe(90);
  });

  it("provides totals grouped by type", () => {
    const totals = calculateEstimateTotals([
      {
        kind: "labor",
        description: "Diagnostics",
        hours: 1.5,
        rate: 120,
      },
      {
        kind: "part",
        description: "Sensor",
        unitPrice: 80,
        quantity: 1,
      },
    ]);

    expect(totals).toEqual({ laborTotal: 180, partsTotal: 80, total: 260 });
  });

  it("produces estimate item payloads from drafts", () => {
    const laborPayload = draftToEstimateItem({
      kind: "labor",
      description: "Alignment",
      hours: 1,
      rate: 95,
    });

    expect(laborPayload).toEqual({
      description: "Alignment",
      cost: 95,
    });

    const partPayload = draftToEstimateItem({
      kind: "part",
      description: "Oil filter",
      unitPrice: 12,
      quantity: 2,
      partNumber: "OF-123",
    });

    expect(partPayload).toEqual({
      description: "Oil filter",
      cost: 24,
      part_id: "OF-123",
      qty: 2,
    });
  });
});

describe("estimate status transitions", () => {
  const statuses: EstimateStatus[] = [
    "DRAFT",
    "PENDING_CUSTOMER_APPROVAL",
    "APPROVED",
    "REJECTED",
  ];

  it("moves estimates to the appropriate state", () => {
    expect(transitionEstimateStatus("DRAFT", "approve")).toBe("APPROVED");
    expect(transitionEstimateStatus("DRAFT", "reject")).toBe("REJECTED");
    expect(
      transitionEstimateStatus("DRAFT", "request_customer_approval"),
    ).toBe("PENDING_CUSTOMER_APPROVAL");
  });

  it("resets estimates to draft", () => {
    statuses.forEach((status) => {
      expect(transitionEstimateStatus(status, "reset")).toBe("DRAFT");
    });
  });

  it("returns current state for unknown actions", () => {
    expect(
      transitionEstimateStatus("APPROVED", "unknown" as never),
    ).toBe("APPROVED");
  });
});
