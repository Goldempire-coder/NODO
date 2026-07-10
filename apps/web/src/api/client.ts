import { resolveApiUrl } from "../lib/env";

export class ApiClientError extends Error {
  code: string;

  constructor(message: string, code: string) {
    super(message);
    this.name = "ApiClientError";
    this.code = code;
  }
}

export async function apiRequest<T = unknown>(path: string, token: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(resolveApiUrl(path), {
    ...options,
    headers: {
      Authorization: `Bearer ${token}`,
      "X-Request-Id": `web_${Date.now()}`,
      ...(options.headers || {})
    }
  });
  const payload = await response.json();
  if (!response.ok) {
    throw new ApiClientError(payload.error?.message || "No logramos completar la accion. Intenta de nuevo.", payload.error?.code || "UNKNOWN_ERROR");
  }
  return payload.data;
}

export type AuthenticatedRequest = <T = unknown>(path: string, options?: RequestInit) => Promise<T>;
