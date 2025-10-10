import { describe, expect, it } from "vitest";

import {
  computeSlaBadge,
  getNextWarrantyStatus,
  mergeWarrantyComments,
} from "@/lib/warranty-utils";

describe("computeSlaBadge", () => {
  it("returns null when createdAt missing", () => {
    expect(computeSlaBadge({})).toBeNull();
  });

  it("flags breached SLA when no response for over 48h", () => {
    const createdAt = new Date("2024-01-01T00:00:00Z");
    const now = new Date(createdAt.getTime() + 49 * 3_600_000);
    const badge = computeSlaBadge({ createdAt: createdAt.toISOString() }, now);
    expect(badge).toEqual({ label: "SLA breached", tone: "destructive" });
  });

  it("computes response time when firstResponseAt is provided", () => {
    const createdAt = new Date("2024-01-01T00:00:00Z");
    const firstResponse = new Date(createdAt.getTime() + 3.5 * 3_600_000);
    const badge = computeSlaBadge({
      createdAt: createdAt.toISOString(),
      firstResponseAt: firstResponse.toISOString(),
    });
    expect(badge).toEqual({ label: "Responded in 3.5h", tone: "success" });
  });
});

describe("mergeWarrantyComments", () => {
  it("deduplicates comments and keeps chronological order", () => {
    const existing = [
      { id: "a", createdAt: "2024-01-01T00:00:00Z" },
      { id: "b", createdAt: "2024-01-01T01:00:00Z" },
    ];
    const incoming = [
      { id: "b", createdAt: "2024-01-01T01:00:00Z" },
      { id: "c", createdAt: "2024-01-01T00:30:00Z" },
    ];
    const merged = mergeWarrantyComments(existing, incoming);
    expect(merged.map((item) => item.id)).toEqual(["a", "c", "b"]);
  });
});

describe("getNextWarrantyStatus", () => {
  it("prevents flipping directly between approved and denied", () => {
    expect(getNextWarrantyStatus("APPROVED", "DENIED")).toBe("APPROVED");
    expect(getNextWarrantyStatus("DENIED", "APPROVED")).toBe("DENIED");
  });

  it("allows transitions to valid targets", () => {
    expect(getNextWarrantyStatus("OPEN", "NEEDS_MORE_INFO")).toBe("NEEDS_MORE_INFO");
  });

  it("ignores invalid statuses", () => {
    expect(getNextWarrantyStatus("OPEN", "custom" as unknown as string)).toBe("OPEN");
  });
});
