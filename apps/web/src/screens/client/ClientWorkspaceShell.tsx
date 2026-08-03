import { useEffect, useRef, useState } from "react";
import { Spinner, Text, Title } from "@telegram-apps/telegram-ui";
import { AnimatedLogo } from "../../components/nodo/AnimatedLogo";
import { AttentionBadge, AttentionBanner } from "../../components/nodo/SurfaceAttention";
import type { ClientView } from "../../constants/clientViews";
import type { ClientWorkspaceModel } from "../../hooks/useClientWorkspaceModel";
import { useMobileKeyboardViewport } from "../../hooks/useMobileKeyboardViewport";
import { elapsedMs, recordScreenView, recordSlowScreenTransition } from "../../observability/clientTelemetry";
import { ClientScreens } from "./ClientScreens";

const TITLE_BY_VIEW: Partial<Record<ClientView, string>> = {
  welcome: "Bienvenido",
  terms: "Términos",
  "client-profile-setup": "Tus datos",
  profile: "Perfil",
  "marketplace-search": "Marketplace",
  "marketplace-list": "Negocios",
  "marketplace-detail": "Perfil registrado",
  "create-order": "Crear orden",
  "order-summary": "Resumen de orden",
  "report-payment": "Reportar pago",
  "my-orders": "Mis órdenes",
  messages: "Mensajes",
  support: "Soporte",
  "order-chat": "Tracking y chat"
};

function NavIcon({ name }: { name: "home" | "search" | "orders" | "messages" | "profile" }) {
  if (name === "home") {
    return (
      <svg aria-hidden="true" className="nav-icon" viewBox="0 0 24 24">
        <path d="M4.5 10.8 12 4.6l7.5 6.2" />
        <path d="M6.8 10.2v8.4h10.4v-8.4" />
        <path d="M10 18.6v-4.4h4v4.4" />
      </svg>
    );
  }
  if (name === "search") {
    return (
      <svg aria-hidden="true" className="nav-icon" viewBox="0 0 24 24">
        <circle cx="10.8" cy="10.8" r="5.8" />
        <path d="m15.2 15.2 4.3 4.3" />
      </svg>
    );
  }
  if (name === "orders") {
    return (
      <svg aria-hidden="true" className="nav-icon" viewBox="0 0 24 24">
        <rect x="6.2" y="4.4" width="11.6" height="15.2" rx="2" />
        <path d="M9.2 8.2h5.6" />
        <path d="M9.2 12h5.6" />
        <path d="M9.2 15.8h4" />
      </svg>
    );
  }
  if (name === "messages") {
    return (
      <svg aria-hidden="true" className="nav-icon" viewBox="0 0 24 24">
        <path d="M5.2 6.2h13.6v9.2H10l-4.8 3.2v-3.2z" />
      </svg>
    );
  }
  return (
    <svg aria-hidden="true" className="nav-icon" viewBox="0 0 24 24">
      <circle cx="12" cy="8.2" r="3.6" />
      <path d="M5.8 19.2c.8-3.4 3-5.2 6.2-5.2s5.4 1.8 6.2 5.2" />
    </svg>
  );
}

export function ClientWorkspaceShell({ model }: { model: ClientWorkspaceModel }) {
  const {
    attentionAlert,
    attentionCounts,
    attentionStale,
    attentionTruncated,
    busy,
    canGoBack,
    dismissAttention,
    goBack,
    loadActiveMarketplace,
    loadMyOrders,
    loadSupportTickets,
    notice,
    openAttentionAlert,
    selectedSupportTicket,
    setSelectedSupportTicket,
    setSupportReply,
    setView,
    user,
    view
  } = model;
  const [activeNav, setActiveNav] = useState<"home" | "businesses" | "orders" | "messages" | "profile">("home");
  const keyboardActive = useMobileKeyboardViewport();
  const previousViewRef = useRef<ClientView | null>(null);
  const viewStartedAtRef = useRef<number | null>(null);
  const isOnboardingView = view === "welcome" || view === "terms" || view === "client-profile-setup";
  const isNativeChatSurface = view === "order-chat" || (view === "support" && Boolean(selectedSupportTicket));
  const shouldShowNotice = Boolean(notice) && !isNativeChatSurface && !["welcome", "terms", "client-profile-setup", "marketplace-search", "create-order", "marketplace-detail"].includes(view);
  const attentionBannerItem = isNativeChatSurface ? null : attentionAlert;
  const shellClassName = [
    "business-shell",
    keyboardActive ? "business-shell--keyboard-active" : "",
    isNativeChatSurface ? "business-shell--native-chat" : ""
  ].filter(Boolean).join(" ");

  useEffect(() => {
    const previousView = previousViewRef.current;
    if (viewStartedAtRef.current !== null) {
      recordSlowScreenTransition(view, previousView, elapsedMs(viewStartedAtRef.current));
    }
    recordScreenView(view, previousView);
    previousViewRef.current = view;
    viewStartedAtRef.current = typeof performance !== "undefined" && typeof performance.now === "function" ? performance.now() : Date.now();
  }, [view]);

  const handleClientBack = () => {
    if (view === "support" && selectedSupportTicket) {
      setSelectedSupportTicket(null);
      setSupportReply("");
      void loadSupportTickets("active");
      return;
    }
    goBack();
  };

  useEffect(() => {
    if (view === "profile") {
      setActiveNav("profile");
      return;
    }
    if (view === "my-orders" || view === "order-summary" || view === "report-payment") {
      setActiveNav("orders");
      return;
    }
    if (view === "messages" || view === "order-chat" || view === "support") {
      setActiveNav("messages");
      return;
    }
    if (view === "marketplace-search") {
      setActiveNav("home");
      return;
    }
    if (view === "marketplace-list" || view === "marketplace-detail" || view === "create-order") {
      setActiveNav("businesses");
    }
  }, [view]);

  return (
    <section className={shellClassName} aria-live="polite">
      {!isNativeChatSurface ? <div className="business-shell__header app-topbar">
        <div className="topbar-brand">
          <AnimatedLogo />
          <div className="topbar-wordmark">
            <strong>NODO</strong>
          </div>
        </div>
        <div className="topbar-user">
          <span className="topbar-avatar" aria-hidden="true">
            {(user.first_name || user.username || "U").slice(0, 1).toUpperCase()}
          </span>
          <div>
            <span>Hola, {user.first_name || user.username || "Usuario"}</span>
          </div>
        </div>
      </div> : null}

      {canGoBack && isNativeChatSurface ? (
        <button className="topbar-back native-chat-back" type="button" aria-label="Volver" onClick={handleClientBack}>
          <span aria-hidden="true" />
        </button>
      ) : null}

      {canGoBack && !isNativeChatSurface ? (
        <div className="screen-heading">
          <button className="topbar-back" type="button" aria-label="Volver" onClick={handleClientBack}>
            <span aria-hidden="true" />
          </button>
          <Title level="2" className="business-shell__title">
            {TITLE_BY_VIEW[view] || "NODO"}
          </Title>
        </div>
      ) : null}

      {!isOnboardingView && !isNativeChatSurface ? (
        <div className={keyboardActive ? "primary-nav primary-nav--hidden" : "primary-nav"}>
          <button className={activeNav === "home" ? "nav-button is-active" : "nav-button"} type="button" onClick={() => {
            setActiveNav("home");
            setView("marketplace-search");
          }}>
            <NavIcon name="home" />
            <span>Inicio</span>
          </button>
          <button className={activeNav === "businesses" ? "nav-button is-active" : "nav-button"} type="button" onClick={() => {
            setActiveNav("businesses");
            void loadActiveMarketplace();
          }}>
            <NavIcon name="search" />
            <span>Negocios</span>
          </button>
          <button className={activeNav === "orders" ? "nav-button is-active" : "nav-button"} type="button" onClick={() => {
            setActiveNav("orders");
            void loadMyOrders("my-orders");
          }}>
            <NavIcon name="orders" />
            <span>Órdenes</span>
            <AttentionBadge
              count={attentionCounts.orders}
              label="ordenes pendientes"
              truncated={attentionTruncated.orders}
            />
          </button>
          <button className={activeNav === "messages" ? "nav-button is-active" : "nav-button"} type="button" onClick={() => {
            setActiveNav("messages");
            void loadMyOrders("messages");
          }}>
            <NavIcon name="messages" />
            <span>Mensajes</span>
            <AttentionBadge
              count={attentionCounts.support}
              label="respuestas de soporte pendientes"
              truncated={attentionTruncated.support}
            />
          </button>
          <button className={activeNav === "profile" ? "nav-button is-active" : "nav-button"} type="button" onClick={() => {
            setActiveNav("profile");
            setView("profile");
          }}>
            <NavIcon name="profile" />
            <span>Perfil</span>
          </button>
        </div>
      ) : null}

      {busy && !isNativeChatSurface ? (
        <div className="shell-loading-pill">
          <Spinner size="s" />
          <Text>Cargando</Text>
        </div>
      ) : null}

      {shouldShowNotice ? <Text className="auth-entry__message">{notice}</Text> : null}

      <AttentionBanner
        item={attentionBannerItem}
        stale={attentionStale}
        onDismiss={dismissAttention}
        onOpen={() => void openAttentionAlert()}
      />

      <ClientScreens model={model} />
    </section>
  );
}
