import type { ResponseCookie } from "next/dist/compiled/@edge-runtime/cookies";

export const AUTH_COOKIE_NAME = "repairshop.session";

export const authCookieOptions: Partial<ResponseCookie> = {
  httpOnly: true,
  secure: true,
  sameSite: "lax",
  path: "/",
  maxAge: 60 * 60,
};

export const expiredAuthCookie: Partial<ResponseCookie> = {
  ...authCookieOptions,
  maxAge: 0,
};
