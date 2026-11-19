"use client";

import type { ApiErrorBody } from "./types";

export class ApiError extends Error {
  constructor(
    message: string,
    public code: string,
    public status: number,
    public fields: Record<string, unknown> = {},
  ) {
    super(message);
  }
}

let csrfReady: Promise<void> | null = null;

function readCookie(name: string): string | null {
  const match = document.cookie.split("; ").find((part) => part.startsWith(`${name}=`));
  return match ? decodeURIComponent(match.slice(name.length + 1)) : null;
}

async function ensureCsrf(): Promise<string> {
  let token = readCookie("csrftoken");
  if (!token) {
    csrfReady ??= fetch("/api/v1/csrf/", { credentials: "same-origin" }).then(() => undefined);
    await csrfReady;
    csrfReady = null;
    token = readCookie("csrftoken");
  }
  return token ?? "";
}

const NETWORK_MESSAGE = "ارتباط با فروشگاه برقرار نشد. اتصال اینترنت را بررسی و دوباره تلاش کنید.";

export async function api<T>(
  path: string,
  options: { method?: "GET" | "POST" | "PATCH" | "DELETE"; body?: unknown; retryCsrf?: boolean } = {},
): Promise<T> {
  const method = options.method ?? "GET";
  const headers: Record<string, string> = { Accept: "application/json" };
  if (method !== "GET") {
    headers["Content-Type"] = "application/json";
    headers["X-CSRFToken"] = await ensureCsrf();
  }
  let response: Response;
  try {
    response = await fetch(`/api/v1${path}`, {
      method,
      headers,
      credentials: "same-origin",
      cache: "no-store",
      body: options.body === undefined ? undefined : JSON.stringify(options.body),
    });
  } catch {
    throw new ApiError(NETWORK_MESSAGE, "network", 0);
  }
  if (response.status === 204) return undefined as T;
  let data: unknown = null;
  try {
    data = await response.json();
  } catch {
    data = null;
  }
  if (!response.ok) {
    const error = (data as ApiErrorBody | null)?.error;
    if (error?.code === "csrf_failed" && options.retryCsrf !== false) {
      document.cookie = "csrftoken=; Max-Age=0; path=/";
      return api<T>(path, { ...options, retryCsrf: false });
    }
    throw new ApiError(
      error?.message ?? "خطای غیرمنتظره‌ای رخ داد. کمی بعد دوباره تلاش کنید.",
      error?.code ?? "error",
      response.status,
      (error?.fields as Record<string, unknown>) ?? {},
    );
  }
  return data as T;
}

export function fieldError(error: unknown, field: string): string | undefined {
  if (!(error instanceof ApiError)) return undefined;
  const value = error.fields[field];
  if (Array.isArray(value)) return String(value[0]);
  return value ? String(value) : undefined;
}
