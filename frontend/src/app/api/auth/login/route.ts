import { NextRequest, NextResponse } from "next/server";

import { AUTH_COOKIE_NAME, authCookieOptions } from "@/lib/auth/cookies";
import { type AuthServiceError, login } from "@/services/auth";

interface LoginRequestBody {
  email?: string;
  password?: string;
  twoFactorToken?: string;
}

export async function POST(request: NextRequest) {
  const body = (await request.json()) as LoginRequestBody;

  if (!body.email || !body.password) {
    return NextResponse.json(
      { success: false, message: "Email and password are required" },
      { status: 400 },
    );
  }

  try {
    const result = await login({
      email: body.email,
      password: body.password,
      twoFactorToken: body.twoFactorToken,
    });

    const response = NextResponse.json({ success: true });
    response.cookies.set({
      name: AUTH_COOKIE_NAME,
      value: result.accessToken,
      ...authCookieOptions,
    });
    return response;
  } catch (error) {
    const normalized = error as AuthServiceError;
    const requiresTwoFactor =
      !body.twoFactorToken && normalized.message.toLowerCase().includes("two-factor");

    const status = normalized.status ?? (requiresTwoFactor ? 401 : 500);

    return NextResponse.json(
      {
        success: false,
        code: normalized.code,
        message: normalized.message,
        details: normalized.details,
        requiresTwoFactor,
        lockoutUntil:
          typeof normalized.details === "object" && normalized.details !== null && "lockedUntil" in normalized.details
            ? (normalized.details as { lockedUntil?: string }).lockedUntil ?? null
            : null,
      },
      { status },
    );
  }
}
