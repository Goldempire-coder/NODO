"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { authenticateWithTelegram, logoutSession } from "../api/auth";
import { readAuthSession, refreshAuthSession, type StoredAuthSession, writeAuthSession } from "../api/session";
import { notifyTelegram, readTelegramInitData, setupTelegramViewport } from "../theme/telegramTheme";
import type { PublicUser, SessionState } from "../types/auth";

const AUTH_BUILD_LABEL = "auth-20260812-rc1";

function wait(ms: number) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

function canUseStoredSession(session: StoredAuthSession | null) {
  return Boolean(session?.accessToken && session.user && (!session.expiresAt || session.expiresAt > Date.now() + 30_000));
}

export function useTelegramAuth(surface?: string) {
  const [state, setState] = useState<SessionState>("loading");
  const [message, setMessage] = useState("Preparando NODO en Telegram");
  const [user, setUser] = useState<PublicUser | null>(null);
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [loggingOut, setLoggingOut] = useState(false);

  const applyStoredSession = useCallback((session: StoredAuthSession, messageText = "Listo para usar NODO") => {
    if (!session.user) {
      return false;
    }
    setUser(session.user);
    setAccessToken(session.accessToken);
    setState("authenticated");
    setMessage(messageText);
    notifyTelegram("success");
    return true;
  }, []);

  const authenticate = useCallback(async () => {
    setState("loading");
    setMessage(`Preparando NODO en Telegram (${AUTH_BUILD_LABEL})`);
    setupTelegramViewport();

    const storedSession = readAuthSession("telegram");
    if (canUseStoredSession(storedSession) && storedSession) {
      applyStoredSession(storedSession);
      return;
    }

    if (storedSession?.refreshToken) {
      const refreshedSession = await refreshAuthSession("telegram").catch(() => null);
      if (canUseStoredSession(refreshedSession) && refreshedSession) {
        applyStoredSession(refreshedSession);
        return;
      }
    }

    const initData = await readTelegramInitData();

    if (!initData) {
      if (canUseStoredSession(storedSession) && storedSession) {
        applyStoredSession(storedSession, "Listo para usar NODO. Telegram no envio sesion nueva.");
        return;
      }
      setState("error");
      setMessage(`Abre NODO desde Telegram para iniciar sesion. ${AUTH_BUILD_LABEL}`);
      notifyTelegram("warning");
      return;
    }

    try {
      let payload = null;
      let lastError: unknown = null;
      for (let attempt = 1; attempt <= 3; attempt += 1) {
        try {
          payload = await authenticateWithTelegram(initData, surface);
          break;
        } catch (error) {
          lastError = error;
          if (attempt < 3) {
            setMessage("Conectando con NODO...");
            await wait(350 * attempt);
          }
        }
      }

      if (!payload) {
        throw lastError instanceof Error ? lastError : new Error("AUTH_CONNECT_FAILED");
      }

      if (!payload.data) {
        const code = payload.error?.code;
        setState(code === "SESSION_EXPIRED" || code === "TELEGRAM_INIT_DATA_EXPIRED" ? "expired" : "error");
        setMessage(payload.error?.message || "No logramos iniciar. Intenta de nuevo.");
        notifyTelegram("error");
        return;
      }

      writeAuthSession("telegram", {
        accessToken: payload.data.access_token,
        refreshToken: payload.data.refresh_token,
        expiresAt: Date.now() + payload.data.expires_in * 1000,
        user: payload.data.user
      });
      setUser(payload.data.user);
      setAccessToken(payload.data.access_token);
      setState("authenticated");
      setMessage("Listo para usar NODO");
      notifyTelegram("success");
    } catch (error) {
      const fallbackSession = readAuthSession("telegram");
      if (canUseStoredSession(fallbackSession) && fallbackSession) {
        applyStoredSession(fallbackSession, "Listo para usar NODO. Usamos tu sesion guardada.");
        return;
      }
      setState("error");
      const code = error instanceof Error ? error.name || "AUTH_ERROR" : "AUTH_ERROR";
      setMessage(`Estamos ajustando la conexion. Codigo ${code}. Version ${AUTH_BUILD_LABEL}. Cierra y abre desde el boton nuevo.`);
      notifyTelegram("error");
    }
  }, [applyStoredSession, surface]);

  useEffect(() => {
    void authenticate();
  }, [authenticate]);

  const logout = useCallback(async () => {
    const storedSession = readAuthSession("telegram");
    setLoggingOut(true);
    setMessage("Cerrando sesion en este dispositivo...");
    try {
      await logoutSession("telegram", storedSession?.refreshToken ?? null, storedSession?.accessToken ?? accessToken);
      notifyTelegram("success");
    } catch {
      notifyTelegram("warning");
    } finally {
      setUser(null);
      setAccessToken(null);
      setState("error");
      setMessage("Sesion cerrada en este dispositivo. Abre NODO desde Telegram para entrar de nuevo.");
      setLoggingOut(false);
    }
  }, [accessToken]);

  const displayName = useMemo(() => {
    if (!user) {
      return "Usuario";
    }
    return user.first_name || user.username || "Usuario";
  }, [user]);

  return { accessToken, authenticate, displayName, loggingOut, logout, message, state, user };
}
