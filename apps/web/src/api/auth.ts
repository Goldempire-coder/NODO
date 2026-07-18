import type { AuthResponse } from "../types/auth";
import { resolveApiUrl } from "../lib/env";
import { clearAuthSession, type AuthSurface } from "./session";

export async function authenticateWithTelegram(initData: string, surface?: string): Promise<AuthResponse> {
  const response = await fetch(resolveApiUrl("/api/v1/auth/telegram"), {
    method: "POST",
    headers: {
      "Content-Type": "text/plain;charset=UTF-8"
    },
    body: JSON.stringify({ init_data: initData, surface })
  });
  return (await response.json()) as AuthResponse;
}

export async function authenticateAdminCredentials(username: string, password: string): Promise<AuthResponse> {
  const response = await fetch(resolveApiUrl("/api/v1/auth/admin/login"), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-NODO-Surface": "admin_web",
      "X-Request-Id": `admin_login_${Date.now()}`
    },
    body: JSON.stringify({ username, password })
  });
  return (await response.json()) as AuthResponse;
}

export async function logoutSession(surface: AuthSurface, refreshToken: string | null, accessToken: string | null): Promise<void> {
  try {
    if (refreshToken && accessToken) {
      await fetch(resolveApiUrl("/api/v1/auth/logout"), {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${accessToken}`,
          "X-Request-Id": `web_logout_${Date.now()}`
        },
        body: JSON.stringify({ refresh_token: refreshToken })
      });
    }
  } finally {
    clearAuthSession(surface);
  }
}
