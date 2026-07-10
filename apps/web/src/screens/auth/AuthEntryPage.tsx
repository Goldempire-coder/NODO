"use client";

import { AppRoot, Text, Title } from "@telegram-apps/telegram-ui";
import { AnimatedLogo } from "../../components/nodo/AnimatedLogo";
import { StatusPanel } from "../../components/feedback/StatusPanel";
import { AdminWebWorkspace } from "../admin-web/AdminWebWorkspace";
import { BusinessMiniAppWorkspace } from "../business-app/BusinessMiniAppWorkspace";
import { ClientWorkspace } from "../client/ClientWorkspace";
import { useTelegramAuth } from "../../hooks/useTelegramAuth";

export function AuthEntryPage() {
  const { accessToken, authenticate, displayName, message, state, user } = useTelegramAuth();
  const surface = typeof window !== "undefined" ? new URLSearchParams(window.location.search).get("surface") : null;

  if (state === "authenticated" && user && accessToken) {
    if (surface === "admin") {
      return <AdminWebWorkspace user={user} token={accessToken} />;
    }

    return (
      <AppRoot appearance="dark">
        <main className="app-shell">
          {surface === "business" ? <BusinessMiniAppWorkspace user={user} token={accessToken} /> : <ClientWorkspace user={user} token={accessToken} />}
        </main>
      </AppRoot>
    );
  }

  return (
    <AppRoot appearance="dark">
      <main className="auth-entry">
        <section className="auth-entry__panel" aria-live="polite">
          <AnimatedLogo />
          <div className="auth-entry__copy">
            <Text className="auth-entry__eyebrow">NODO</Text>
            <Title level="2" className="auth-entry__title">
              Cambio verificado
            </Title>
            {state === "authenticated" ? <Text className="auth-entry__message">Hola, {displayName}. Listo para cambiar.</Text> : null}
          </div>

          <StatusPanel state={state} message={message} onRetry={() => void authenticate()} />
        </section>
      </main>
    </AppRoot>
  );
}
