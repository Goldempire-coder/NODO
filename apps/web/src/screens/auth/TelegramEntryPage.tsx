"use client";

import dynamic from "next/dynamic";
import { AppRoot, Text, Title } from "@telegram-apps/telegram-ui";
import { AnimatedLogo } from "../../components/nodo/AnimatedLogo";
import { StatusPanel } from "../../components/feedback/StatusPanel";
import { useTelegramAuth } from "../../hooks/useTelegramAuth";
import type { PublicUser } from "../../types/auth";

const BusinessMiniAppWorkspace = dynamic(() => import("../business-app/BusinessMiniAppWorkspace").then((mod) => mod.BusinessMiniAppWorkspace), { ssr: false });
const ClientWorkspace = dynamic(() => import("../client/ClientWorkspace").then((mod) => mod.ClientWorkspace), { ssr: false });

type WorkspaceProps = {
  user: PublicUser;
  token: string;
  loggingOut?: boolean;
  onLogout: () => Promise<void> | void;
};

export function TelegramEntryPage({ surface }: { surface: string }) {
  const authSurface = surface === "business" ? "business_mini_app" : "client_mini_app";
  const { accessToken, authenticate, displayName, loggingOut, logout, message, state, user } = useTelegramAuth(authSurface);

  if (state === "authenticated" && user && accessToken) {
    const workspaceProps: WorkspaceProps = { user, token: accessToken, loggingOut, onLogout: logout };
    return (
      <AppRoot appearance="dark">
        <main className="app-shell">
          {surface === "business" ? <BusinessMiniAppWorkspace {...workspaceProps} /> : <ClientWorkspace {...workspaceProps} />}
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
              Directorio NODO
            </Title>
            {state === "authenticated" ? <Text className="auth-entry__message">Hola, {displayName}. Listo para usar NODO.</Text> : null}
          </div>

          <StatusPanel state={state} message={message} onRetry={() => void authenticate()} />
        </section>
      </main>
    </AppRoot>
  );
}
