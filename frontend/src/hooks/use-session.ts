"use client";

import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";

interface SessionUser {
  id: string;
  email: string;
  role: string;
  createdAt?: string;
  lastLogin?: string | null;
  lastLoginLocation?: string | null;
}

interface SessionResponse {
  user: SessionUser | null;
}

async function fetchSession(): Promise<SessionResponse> {
  const response = await fetch("/api/auth/session", {
    method: "GET",
    credentials: "include",
  });

  if (!response.ok && response.status !== 401) {
    throw new Error("Unable to load session");
  }

  return (await response.json()) as SessionResponse;
}

export function useSession() {
  const query = useQuery<SessionResponse, Error>({
    queryKey: ["session"],
    queryFn: fetchSession,
    staleTime: 60_000,
    refetchInterval: 60_000,
    retry: false,
  });

  return useMemo(
    () => ({
      ...query,
      user: query.data?.user ?? null,
      isAuthenticated: Boolean(query.data?.user),
      role: query.data?.user?.role ?? null,
    }),
    [query],
  );
}
