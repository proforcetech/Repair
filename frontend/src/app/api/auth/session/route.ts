import { NextResponse } from "next/server";
import { cookies } from "next/headers";

import { AUTH_COOKIE_NAME, expiredAuthCookie } from "@/lib/auth/cookies";
import { fetchCurrentUser } from "@/services/auth";

export async function GET() {
  const cookieStore = cookies();
  const token = cookieStore.get(AUTH_COOKIE_NAME)?.value;

  if (!token) {
    return NextResponse.json({ user: null }, { status: 200 });
  }

  try {
    const user = await fetchCurrentUser(token);
    return NextResponse.json({ user }, { status: 200 });
  } catch (error) {
    const response = NextResponse.json({ user: null }, { status: 401 });
    response.cookies.set({
      name: AUTH_COOKIE_NAME,
      value: "",
      ...expiredAuthCookie,
    });
    return response;
  }
}
