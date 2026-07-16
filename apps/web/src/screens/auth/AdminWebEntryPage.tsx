"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { apiRequest, ApiClientError } from "../../api/client";
import { clearAuthSession, LEGACY_ADMIN_TOKEN_STORAGE_KEY, readAuthSession, writeAuthSession } from "../../api/session";
import { canReadAdmin } from "../../hooks/admin-web/adminWebAccess";
import type { PublicUser } from "../../types/auth";
import { AdminWebWorkspace } from "../admin-web/AdminWebWorkspace";

type SubmittedAdminSession = {
  accessToken: string;
  refreshToken: string | null;
};

function readStoredAdminSession(): SubmittedAdminSession | null {
  const stored = readAuthSession("admin");
  return stored ? { accessToken: stored.accessToken, refreshToken: stored.refreshToken } : null;
}

function parseSubmittedAdminSession(value: string): SubmittedAdminSession | null {
  const trimmed = value.trim();
  if (!trimmed) {
    return null;
  }
  if (!trimmed.startsWith("{")) {
    return { accessToken: trimmed, refreshToken: null };
  }
  try {
    const parsed = JSON.parse(trimmed);
    const data = parsed.data || parsed;
    const accessToken = data.access_token || data.accessToken;
    const refreshToken = data.refresh_token || data.refreshToken || null;
    return accessToken ? { accessToken, refreshToken } : null;
  } catch {
    return null;
  }
}

export function AdminWebEntryPage() {
  const [tokenInput, setTokenInput] = useState("");
  const [session, setSession] = useState<{ token: string; user: PublicUser } | null>(null);
  const [message, setMessage] = useState("Ingresa una sesion admin emitida por backend.");
  const [busy, setBusy] = useState(false);

  const validateToken = useCallback(async (submittedSession: SubmittedAdminSession) => {
    setBusy(true);
    setMessage("Validando sesion admin...");
    try {
      if (submittedSession.refreshToken) {
        writeAuthSession("admin", {
          accessToken: submittedSession.accessToken,
          refreshToken: submittedSession.refreshToken,
          expiresAt: null,
          user: null
        });
      }
      const user = await apiRequest<PublicUser>("/api/v1/users/me", submittedSession.accessToken, {
        headers: {
          "X-NODO-Surface": "admin_web"
        }
      });
      if (!canReadAdmin(user)) {
        clearAuthSession("admin");
        setMessage("Esta sesion no tiene acceso al Admin Web.");
        setBusy(false);
        return;
      }
      const validatedSession = readAuthSession("admin") || {
        accessToken: submittedSession.accessToken,
        refreshToken: submittedSession.refreshToken,
        expiresAt: null
      };
      if (validatedSession.refreshToken) {
        writeAuthSession("admin", {
          accessToken: validatedSession.accessToken,
          refreshToken: validatedSession.refreshToken,
          expiresAt: validatedSession.expiresAt,
          user
        });
      } else {
        window.sessionStorage.setItem(LEGACY_ADMIN_TOKEN_STORAGE_KEY, validatedSession.accessToken);
      }
      setSession({ token: validatedSession.accessToken, user });
      setMessage("Sesion admin validada.");
    } catch (error) {
      clearAuthSession("admin");
      const safeMessage = error instanceof ApiClientError ? error.message : "No pudimos validar la sesion admin.";
      setMessage(safeMessage);
    } finally {
      setBusy(false);
    }
  }, []);

  useEffect(() => {
    const storedSession = readStoredAdminSession();
    if (storedSession) {
      void validateToken(storedSession);
    }
  }, [validateToken]);

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const submittedSession = parseSubmittedAdminSession(tokenInput);
    if (!submittedSession) {
      setMessage("La sesion admin es requerida.");
      return;
    }
    void validateToken(submittedSession);
  };

  if (session) {
    return <AdminWebWorkspace user={session.user} token={session.token} />;
  }

  return (
    <main className="admin-web-auth">
      <section className="admin-web-auth__panel" aria-live="polite">
        <div className="admin-web-brand">
          <span>NODO</span>
          <small>Admin Web</small>
        </div>
        <div>
          <p className="admin-web-auth__eyebrow">Acceso operativo</p>
          <h1>Panel Admin Web</h1>
          <p>Esta superficie no inicia Telegram ni usa Mini App shell. El backend valida la sesion y RBAC.</p>
        </div>
        <form className="admin-web-auth__form" onSubmit={handleSubmit}>
          <label htmlFor="admin-session-token">Sesion admin</label>
          <textarea
            id="admin-session-token"
            value={tokenInput}
            onChange={(event) => setTokenInput(event.target.value)}
            placeholder="Pega un JWT admin o un payload de sesion emitido por backend"
            rows={4}
            spellCheck={false}
          />
          <button type="submit" disabled={busy}>
            {busy ? "Validando..." : "Entrar al Admin Web"}
          </button>
        </form>
        <p className="admin-web-auth__message">{message}</p>
      </section>
    </main>
  );
}
