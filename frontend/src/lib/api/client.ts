import axios, { AxiosError, AxiosRequestConfig, AxiosResponse } from "axios";

import { clearAuthTokens, getAccessToken } from "@/stores/auth-store";

const DEFAULT_API_BASE_URL = "http://localhost:8000";

const apiBaseUrl =
  process.env.NEXT_PUBLIC_FASTAPI_URL ??
  process.env.NEXT_PUBLIC_API_BASE_URL ??
  DEFAULT_API_BASE_URL;

export interface NormalizedApiError {
  status?: number;
  code?: string;
  message: string;
  details?: Array<string | Record<string, unknown>> | Record<string, unknown> | null;
  original?: unknown;
}

export const apiClient = axios.create({
  baseURL: apiBaseUrl,
  withCredentials: true,
  headers: {
    "Content-Type": "application/json",
    Accept: "application/json",
  },
});

apiClient.interceptors.request.use((config) => {
  const token = getAccessToken();
  if (token) {
    config.headers = config.headers ?? {};
    config.headers.Authorization = `Bearer ${token}`;
  }

  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (axios.isAxiosError(error)) {
      const normalized = normalizeApiError(error);

      if (normalized.status === 401) {
        clearAuthTokens();
      }

      return Promise.reject(normalized);
    }

    return Promise.reject<NormalizedApiError>({
      message: "Unexpected error",
      original: error,
    });
  },
);

export function normalizeApiError(error: AxiosError | unknown): NormalizedApiError {
  if (!axios.isAxiosError(error)) {
    if (error instanceof Error) {
      return {
        message: error.message,
        original: error,
      };
    }

    return {
      message: "Unknown error",
      original: error,
    };
  }

  const { response } = error;
  const status = response?.status;
  const data = response?.data as Record<string, unknown> | undefined;

  let message = error.message;
  let code: string | undefined;
  let details: NormalizedApiError["details"];

  if (data) {
    if (typeof data === "string") {
      message = data;
    } else {
      const detail = (data.detail ?? data.message ?? data.error) as unknown;

      if (typeof detail === "string") {
        message = detail;
      } else if (Array.isArray(detail)) {
        const firstDetail = detail[0];
        if (typeof firstDetail === "object" && firstDetail !== null && "msg" in firstDetail) {
          const msg = (firstDetail as { msg?: unknown }).msg;
          if (typeof msg === "string") {
            message = msg;
          }
        }

        details = detail.map((item) => {
          if (typeof item === "string") {
            return item;
          }

          if (typeof item === "object" && item !== null) {
            const locationValue =
              "loc" in item && Array.isArray(item.loc)
                ? item.loc.map((segment: unknown) => String(segment)).join(" → ")
                : undefined;

            return {
              location: locationValue,
              message:
                "msg" in item && typeof item.msg === "string"
                  ? item.msg
                  : "message" in item && typeof item.message === "string"
                    ? item.message
                    : undefined,
              type: "type" in item && typeof item.type === "string" ? item.type : undefined,
            };
          }

          return { message: String(item) };
        });
      } else if (typeof detail === "object" && detail !== null) {
        const detailRecord = detail as Record<string, unknown>;
        if (typeof detailRecord.msg === "string") {
          message = detailRecord.msg;
        } else if (typeof detailRecord.message === "string") {
          message = detailRecord.message;
        }

        details = detailRecord;
        if (typeof detailRecord.code === "string") {
          code = detailRecord.code;
        } else if (typeof detailRecord.errorCode === "string") {
          code = detailRecord.errorCode;
        }
      }

      if (typeof data.code === "string") {
        code = data.code;
      } else if (typeof data.errorCode === "string") {
        code = data.errorCode;
      }
    }
  }

  return {
    status,
    code,
    message,
    details: details ?? null,
    original: error,
  };
}

export async function request<T = unknown>(config: AxiosRequestConfig): Promise<T> {
  const response: AxiosResponse<T> = await apiClient.request<T>(config);
  return response.data;
}

export async function get<T = unknown>(url: string, config?: AxiosRequestConfig): Promise<T> {
  return request<T>({ ...config, method: "GET", url });
}

export async function post<T = unknown>(
  url: string,
  data?: unknown,
  config?: AxiosRequestConfig,
): Promise<T> {
  return request<T>({ ...config, method: "POST", url, data });
}

export async function put<T = unknown>(
  url: string,
  data?: unknown,
  config?: AxiosRequestConfig,
): Promise<T> {
  return request<T>({ ...config, method: "PUT", url, data });
}

export async function del<T = unknown>(url: string, config?: AxiosRequestConfig): Promise<T> {
  return request<T>({ ...config, method: "DELETE", url });
}