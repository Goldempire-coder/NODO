import { resolveApiUrl } from "../lib/env";
import type { PublicUser } from "../types/auth";

export type AuthSurface = "telegram" | "admin";

export type StoredAuthSession = {
  accessToken: string;
  refreshToken: string | null;
  expiresAt: number | null;
  user?: PublicUser | null;
};

const SESSION_KEYS: Record<AuthSurface, string> = {
  telegram: "nodo_auth_session",
  admin: "nodo_admin_auth_session"
};

export const LEGACY_ADMIN_TOKEN_STORAGE_KEY = "nodo_admin_access_token";

const refreshPromises: Partial<Record<AuthSurface, Promise<StoredAuthSession | null>>> = {};

function canUseSessionStorage() {
  try {
    return typeof window !== "undefined" && Boolean(window.sessionStorage);
  } catch {
    return false;
  }
}

function normalizeSession(payload: unknown): StoredAuthSession | null {
  if (!payload || typeof payload !== "object") {
    return null;
  }
  const value = payload as Partial<StoredAuthSession> & {
    access_token?: string;
    refresh_token?: string;
    expires_in?: number;
    expires_at?: number;
  };
  const accessToken = value.accessToken || value.access_token;
  if (!accessToken) {
    return null;
  }
  const now = Date.now();
  const expiresAt = value.expiresAt ?? value.expires_at ?? (value.expires_in ? now + value.expires_in * 1000 : null);
  return {
    accessToken,
    refreshToken: value.refreshToken || value.refresh_token || null,
    expiresAt,
    user: value.user || null
  };
}

export function readAuthSession(surface: AuthSurface): StoredAuthSession | null {
  if (!canUseSessionStorage()) {
    return null;
  }
  try {
    const raw = window.sessionStorage.getItem(SESSION_KEYS[surface]);
    if (raw) {
      return normalizeSession(JSON.parse(raw));
    }
    if (surface === "admin") {
      const legacyToken = window.sessionStorage.getItem(LEGACY_ADMIN_TOKEN_STORAGE_KEY);
      return legacyToken ? { accessToken: legacyToken, refreshToken: null, expiresAt: null } : null;
    }
  } catch {
    clearAuthSession(surface);
  }
  return null;
}

export function writeAuthSession(surface: AuthSurface, session: StoredAuthSession) {
  if (!canUseSessionStorage()) {
    return;
  }
  const normalized = normalizeSession(session);
  if (!normalized) {
    return;
  }
  try {
    window.sessionStorage.setItem(SESSION_KEYS[surface], JSON.stringify(normalized));
    if (surface === "admin") {
      window.sessionStorage.removeItem(LEGACY_ADMIN_TOKEN_STORAGE_KEY);
    }
  } catch {
    return;
  }
}

export function updateAuthSessionUser(surface: AuthSurface, user: PublicUser) {
  const current = readAuthSession(surface);
  if (!current) {
    return;
  }
  writeAuthSession(surface, { ...current, user });
}

export function clearAuthSession(surface: AuthSurface) {
  if (!canUseSessionStorage()) {
    return;
  }
  try {
    window.sessionStorage.removeItem(SESSION_KEYS[surface]);
    if (surface === "admin") {
      window.sessionStorage.removeItem(LEGACY_ADMIN_TOKEN_STORAGE_KEY);
    }
  } catch {
    return;
  }
}

export function clearAllAuthSessions() {
  clearAuthSession("telegram");
  clearAuthSession("admin");
}

export function inferAuthSurface(path: string, options: RequestInit = {}): AuthSurface {
  const headers = new Headers(options.headers || {});
  const surface = headers.get("X-NODO-Surface");
  if (surface === "admin_web" || path.startsWith("/api/v1/admin/")) {
    return "admin";
  }
  return "telegram";
}

export function currentAccessToken(surface: AuthSurface, fallbackToken: string): string {
  return readAuthSession(surface)?.accessToken || fallbackToken;
}

export async function refreshAuthSession(surface: AuthSurface): Promise<StoredAuthSession | null> {
  const current = readAuthSession(surface);
  if (!current?.refreshToken) {
    clearAuthSession(surface);
    return null;
  }
  if (refreshPromises[surface]) {
    return refreshPromises[surface] || null;
  }
  refreshPromises[surface] = (async () => {
    const response = await fetch(resolveApiUrl("/api/v1/auth/refresh"), {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Request-Id": `web_refresh_${Date.now()}`
      },
      body: JSON.stringify({ refresh_token: current.refreshToken })
    });
    const payload = await response.json().catch(() => null);
    if (!response.ok || !payload?.data?.access_token || !payload?.data?.refresh_token) {
      clearAuthSession(surface);
      return null;
    }
    const refreshed: StoredAuthSession = {
      accessToken: payload.data.access_token,
      refreshToken: payload.data.refresh_token,
      expiresAt: Date.now() + (payload.data.expires_in || 0) * 1000,
      user: current.user || null
    };
    writeAuthSession(surface, refreshed);
    return refreshed;
  })().finally(() => {
    refreshPromises[surface] = undefined;
  });
  return refreshPromises[surface] || null;
}
