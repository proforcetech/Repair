import { get } from "@/lib/api/client";

export interface Bay {
  id: string;
  name?: string | null;
  isOccupied?: boolean | null;
}

export async function fetchBays() {
  return get<Bay[]>("/bays");
}
