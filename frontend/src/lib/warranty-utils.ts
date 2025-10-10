export type WarrantySlaTone = "success" | "warning" | "destructive" | "muted";

export type WarrantySlaBadge = {
  label: string;
  tone: WarrantySlaTone;
};

export type WarrantyTimelineLike = {
  createdAt?: string | null;
  firstResponseAt?: string | null;
};

export type WarrantyCommentLike = {
  id: string;
  createdAt: string;
};

const SLA_HOURS = 48;

export function computeSlaBadge(claim: WarrantyTimelineLike, referenceDate: Date = new Date()): WarrantySlaBadge | null {
  if (!claim.createdAt) {
    return null;
  }

  const createdAt = new Date(claim.createdAt);
  if (Number.isNaN(createdAt.getTime())) {
    return null;
  }

  if (claim.firstResponseAt) {
    const firstResponse = new Date(claim.firstResponseAt);
    const diffHours = (firstResponse.getTime() - createdAt.getTime()) / 3_600_000;
    if (Number.isFinite(diffHours) && diffHours > SLA_HOURS) {
      return { label: `First response after SLA (${diffHours.toFixed(1)}h)`, tone: "destructive" };
    }
    if (Number.isFinite(diffHours) && diffHours >= 0) {
      return { label: `Responded in ${diffHours.toFixed(1)}h`, tone: "success" };
    }
  }

  const hoursOpen = (referenceDate.getTime() - createdAt.getTime()) / 3_600_000;
  if (!Number.isFinite(hoursOpen)) {
    return null;
  }

  if (hoursOpen > SLA_HOURS) {
    return { label: "SLA breached", tone: "destructive" };
  }

  if (hoursOpen > SLA_HOURS - 12) {
    return { label: "At risk", tone: "warning" };
  }

  return { label: "Within SLA", tone: "muted" };
}

export function mergeWarrantyComments<T extends WarrantyCommentLike>(existing: T[], incoming: T[]): T[] {
  if (incoming.length === 0) {
    return existing;
  }

  const seen = new Set(existing.map((comment) => comment.id));
  const merged = [...existing];

  for (const comment of incoming) {
    if (seen.has(comment.id)) {
      continue;
    }
    seen.add(comment.id);
    merged.push(comment);
  }

  return merged.sort(
    (a, b) => new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime(),
  );
}

export function getNextWarrantyStatus(current: string, desired: string): string {
  const normalized = desired.toUpperCase();
  const allowed = new Set(["APPROVED", "DENIED", "NEEDS_MORE_INFO", "OPEN", "PENDING"]);
  if (!allowed.has(normalized)) {
    return current;
  }

  if (current === "APPROVED" && normalized === "DENIED") {
    return current;
  }

  if (current === "DENIED" && normalized === "APPROVED") {
    return current;
  }

  return normalized;
}
