"use client";

import { useEffect, useRef } from "react";
import { useQuery } from "@tanstack/react-query";

import type { DashboardNotification } from "@/services/dashboard-mappers";
import { fetchWarrantyAwaitingResponse } from "@/services/warranty";
import { showToast } from "@/stores/toast-store";

export function useWarrantyCommentNotifications(enabled: boolean) {
  const query = useQuery({
    queryKey: ["warranty", "notifications"],
    queryFn: async () => {
      const claims = await fetchWarrantyAwaitingResponse();
      return claims.map<DashboardNotification>((claim) => ({
        id: `warranty-${claim.id}`,
        title: `Awaiting response (#${claim.id})`,
        description: claim.customer?.email
          ? `Customer ${claim.customer.email} is waiting for a reply`
          : "Customer is awaiting a reply",
        severity: "warning",
      }));
    },
    enabled,
    refetchInterval: 30_000,
  });

  const previousCount = useRef(0);
  const currentCount = query.data?.length ?? 0;

  useEffect(() => {
    if (!enabled) {
      previousCount.current = 0;
      return;
    }

    if (currentCount > previousCount.current) {
      showToast({
        title: "New warranty replies awaiting",
        description: `${currentCount} claim${currentCount === 1 ? "" : "s"} need attention`,
        variant: "warning",
      });
    }

    previousCount.current = currentCount;
  }, [currentCount, enabled]);

  return { ...query, data: query.data ?? [] } as typeof query & { data: DashboardNotification[] };
}
