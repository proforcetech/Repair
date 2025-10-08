import { NextResponse } from "next/server";
import { cookies } from "next/headers";

import { AUTH_COOKIE_NAME, expiredAuthCookie } from "@/lib/auth/cookies";
import { logout } from "@/services/auth";

export async function POST() {
  const cookieStore = cookies();
  const token = cookieStore.get(AUTH_COOKIE_NAME)?.value;

  if (token) {
    try {
      await logout(token);
    } catch (error) {
      // Ignore backend logout errors so the client is always signed out locally.
    }
  }

  const response = NextResponse.json({ success: true });
  response.cookies.set({
    name: AUTH_COOKIE_NAME,
    value: "",
    ...expiredAuthCookie,
  });

  return response;
}
