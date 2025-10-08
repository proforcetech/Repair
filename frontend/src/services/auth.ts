import type { AxiosRequestConfig } from "axios";

import { NormalizedApiError, normalizeApiError, request } from "@/lib/api/client";

export interface LoginRequestDto {
  email: string;
  password: string;
  twoFactorToken?: string;
}

export interface LoginResponseDto {
  accessToken: string;
  tokenType: string;
}

export interface TwoFactorSetupResponse {
  image: ArrayBuffer;
}

export interface PasswordResetRequestDto {
  email: string;
}

export interface ResetPasswordDto {
  token: string;
  password: string;
}

export interface AuthMessageResponse {
  message: string;
}

export interface UserSessionDto {
  id: string;
  email: string;
  role: string;
  createdAt?: string;
  lastLogin?: string | null;
  lastLoginLocation?: string | null;
}

function withAuth(token: string): AxiosRequestConfig {
  return {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  } satisfies AxiosRequestConfig;
}

export async function login(credentials: LoginRequestDto): Promise<LoginResponseDto> {
  const body = new URLSearchParams();
  body.append("username", credentials.email);
  body.append("password", credentials.password);
  if (credentials.twoFactorToken) {
    body.append("two_factor_token", credentials.twoFactorToken);
  }

  try {
    const data = await request<{ access_token: string; token_type: string }>({
      url: "/auth/login",
      method: "POST",
      data: body,
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
      },
    });

    return { accessToken: data.access_token, tokenType: data.token_type };
  } catch (error) {
    throw normalizeApiError(error);
  }
}

export async function fetchTwoFactorSetup(token: string): Promise<TwoFactorSetupResponse> {
  try {
    const image = await request<ArrayBuffer>({
      url: "/auth/2fa/setup",
      method: "GET",
      responseType: "arraybuffer",
      ...withAuth(token),
    });

    return { image };
  } catch (error) {
    throw normalizeApiError(error);
  }
}

export async function requestPasswordReset(
  payload: PasswordResetRequestDto,
): Promise<AuthMessageResponse> {
  try {
    return await request<AuthMessageResponse>({
      url: "/auth/request-password-reset",
      method: "POST",
      data: payload,
    });
  } catch (error) {
    throw normalizeApiError(error);
  }
}

export async function resetPassword(payload: ResetPasswordDto): Promise<AuthMessageResponse> {
  try {
    return await request<AuthMessageResponse>({
      url: "/auth/reset-password",
      method: "POST",
      data: payload,
    });
  } catch (error) {
    throw normalizeApiError(error);
  }
}

export async function logout(token: string): Promise<AuthMessageResponse> {
  try {
    return await request<AuthMessageResponse>({
      url: "/auth/logout",
      method: "POST",
      ...withAuth(token),
    });
  } catch (error) {
    throw normalizeApiError(error);
  }
}

export async function fetchCurrentUser(token: string): Promise<UserSessionDto> {
  try {
    return await request<UserSessionDto>({
      url: "/auth/me",
      method: "GET",
      ...withAuth(token),
    });
  } catch (error) {
    const normalized = normalizeApiError(error);
    if (normalized.status === 401 || normalized.status === 403) {
      throw normalized;
    }

    throw normalized;
  }
}

export type AuthServiceError = NormalizedApiError;
