"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { authenticateWithTelegram } from "../api/auth";
import { getTelegramWebApp, readTelegramInitData, setupTelegramViewport } from "../theme/telegramTheme";
import type { PublicUser, SessionState } from "../types/auth";

export function useTelegramAuth() {
  const [state, setState] = useState<SessionState>("loading");
  const [message, setMessage] = useState("Preparando NODO en Telegram");
  const [user, setUser] = useState<PublicUser | null>(null);
  const [accessToken, setAccessToken] = useState<string | null>(null);

  const authenticate = useCallback(async () => {
    setState("loading");
    setMessage("Preparando NODO en Telegram");
    const initData = await readTelegramInitData();
    setupTelegramViewport();

    if (!initData) {
      setState("error");
      setMessage("Abre NODO desde Telegram para iniciar de forma segura.");
      getTelegramWebApp()?.HapticFeedback?.notificationOccurred?.("warning");
      return;
    }

    try {
      const payload = await authenticateWithTelegram(initData);

      if (!payload.data) {
        const code = payload.error?.code;
        setState(code === "SESSION_EXPIRED" || code === "TELEGRAM_INIT_DATA_EXPIRED" ? "expired" : "error");
        setMessage(payload.error?.message || "No logramos iniciar. Intenta de nuevo.");
        getTelegramWebApp()?.HapticFeedback?.notificationOccurred?.("error");
        return;
      }

      setUser(payload.data.user);
      setAccessToken(payload.data.access_token);
      setState("authenticated");
      setMessage("Listo para cambiar");
      getTelegramWebApp()?.HapticFeedback?.notificationOccurred?.("success");
    } catch {
      setState("error");
      setMessage("Estamos ajustando la conexion. Intenta de nuevo en unos segundos.");
      getTelegramWebApp()?.HapticFeedback?.notificationOccurred?.("error");
    }
  }, []);

  useEffect(() => {
    void authenticate();
  }, [authenticate]);

  const displayName = useMemo(() => {
    if (!user) {
      return "Usuario";
    }
    return user.first_name || user.username || "Usuario";
  }, [user]);

  return { accessToken, authenticate, displayName, message, state, user };
}
