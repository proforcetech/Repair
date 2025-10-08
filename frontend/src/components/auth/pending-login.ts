export const PENDING_LOGIN_KEY = "repairshop.pendingLogin";

export interface PendingLoginPayload {
  email: string;
  password: string;
}

export function savePendingLogin(payload: PendingLoginPayload) {
  if (typeof window === "undefined") return;
  sessionStorage.setItem(PENDING_LOGIN_KEY, JSON.stringify(payload));
}

export function clearPendingLogin() {
  if (typeof window === "undefined") return;
  sessionStorage.removeItem(PENDING_LOGIN_KEY);
}

export function readPendingLogin(): PendingLoginPayload | null {
  if (typeof window === "undefined") {
    return null;
  }

  const raw = sessionStorage.getItem(PENDING_LOGIN_KEY);
  if (!raw) return null;

  try {
    const parsed = JSON.parse(raw) as PendingLoginPayload;
    if (typeof parsed.email === "string" && typeof parsed.password === "string") {
      return parsed;
    }
  } catch (error) {
    sessionStorage.removeItem(PENDING_LOGIN_KEY);
  }

  return null;
}
