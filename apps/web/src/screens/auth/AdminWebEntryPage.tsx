"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { authenticateAdminCredentials, logoutSession } from "../../api/auth";
import { apiRequest, ApiClientError } from "../../api/client";
import { clearAuthSession, readAuthSession, writeAuthSession } from "../../api/session";
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

export function AdminWebEntryPage() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [session, setSession] = useState<{ token: string; user: PublicUser } | null>(null);
  const [message, setMessage] = useState("Entra con tu usuario admin.");
  const [busy, setBusy] = useState(false);
  const [loggingOut, setLoggingOut] = useState(false);

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
      writeAuthSession("admin", {
        accessToken: validatedSession.accessToken,
        refreshToken: validatedSession.refreshToken,
        expiresAt: validatedSession.expiresAt,
        user
      });
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
    const cleanUsername = username.trim();
    if (!cleanUsername || !password) {
      setMessage("Usuario y clave son requeridos.");
      return;
    }
    setBusy(true);
    setMessage("Validando usuario admin...");
    void authenticateAdminCredentials(cleanUsername, password)
      .then((payload) => {
        if (!payload.data?.access_token || !payload.data.refresh_token || !payload.data.user) {
          setMessage(payload.error?.message || "No pudimos iniciar sesion admin.");
          return;
        }
        if (!canReadAdmin(payload.data.user)) {
          clearAuthSession("admin");
          setMessage("Este usuario no tiene acceso al Admin Web.");
          return;
        }
        writeAuthSession("admin", {
          accessToken: payload.data.access_token,
          refreshToken: payload.data.refresh_token,
          expiresAt: Date.now() + payload.data.expires_in * 1000,
          user: payload.data.user
        });
        setPassword("");
        setSession({ token: payload.data.access_token, user: payload.data.user });
        setMessage("Sesion admin iniciada.");
      })
      .catch(() => {
        clearAuthSession("admin");
        setMessage("No pudimos iniciar sesion admin.");
      })
      .finally(() => setBusy(false));
  };

  const handleLogout = useCallback(async () => {
    const storedSession = readStoredAdminSession();
    setLoggingOut(true);
    setMessage("Cerrando sesion admin...");
    try {
      await logoutSession("admin", storedSession?.refreshToken ?? null, storedSession?.accessToken ?? session?.token ?? null);
      setMessage("Sesion admin cerrada.");
    } catch {
      setMessage("Sesion admin cerrada en este navegador.");
    } finally {
      setPassword("");
      setSession(null);
      setBusy(false);
      setLoggingOut(false);
    }
  }, [session?.token]);

  if (session) {
    return <AdminWebWorkspace user={session.user} token={session.token} loggingOut={loggingOut} onLogout={handleLogout} />;
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
          <p>Esta superficie usa usuario y clave. El backend valida la sesion y permisos.</p>
        </div>
        <form className="admin-web-auth__form" onSubmit={handleSubmit}>
          <label htmlFor="admin-username">Usuario</label>
          <input
            id="admin-username"
            autoComplete="username"
            value={username}
            onChange={(event) => setUsername(event.target.value)}
            placeholder="admin@nodo.local"
            type="text"
          />
          <label htmlFor="admin-password">Clave</label>
          <input
            id="admin-password"
            autoComplete="current-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            placeholder="Tu clave admin"
            type="password"
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
