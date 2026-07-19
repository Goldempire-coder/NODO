import { Spinner, Text, Title } from "@telegram-apps/telegram-ui";
import { useEffect, useRef, useState } from "react";
import { AnimatedLogo } from "../../components/nodo/AnimatedLogo";
import type { BusinessMiniAppModel } from "../../hooks/useBusinessMiniAppModel";
import type { BusinessMiniAppView } from "../../constants/businessViews";
import { elapsedMs, recordScreenView, recordSlowScreenTransition } from "../../observability/clientTelemetry";
import { BusinessMiniAppScreens } from "./BusinessMiniAppScreens";

const TITLE_BY_VIEW: Partial<Record<BusinessMiniAppView, string>> = {
  "business-dashboard": "Negocio",
  "credits-dashboard": "Creditos",
  "buy-credits": "Comprar creditos",
  "credit-payment-pending": "Pago de creditos",
  "create-ad": "Publicar anuncio",
  "my-ads": "Mis anuncios",
  "archived-ads": "Historial",
  "business-orders": "Ordenes entrantes",
  "business-order-detail": "Detalle de orden",
  "business-chat": "Chat de orden",
  "business-support": "Soporte",
  referrals: "Referidos",
  "payment-methods": "Zelle / USDT",
  "business-settings": "Perfil negocio",
  "business-terms": "Terminos",
  "business-pin": "PIN de seguridad",
  "business-rules": "Reglas"
};

function NavIcon({ name }: { name: "home" | "ads" | "orders" | "credits" | "profile" }) {
  if (name === "ads") {
    return (
      <svg aria-hidden="true" className="nav-icon" viewBox="0 0 24 24">
        <path d="M5.2 7.2h13.6v9.6H5.2z" />
        <path d="M8.2 10.2h7.6" />
        <path d="M8.2 13.8h4.8" />
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
  if (name === "credits") {
    return (
      <svg aria-hidden="true" className="nav-icon" viewBox="0 0 24 24">
        <circle cx="12" cy="12" r="7.2" />
        <path d="M9 12.8c.8.9 1.9 1.3 3.2 1.3 1.5 0 2.8-.6 2.8-1.8 0-1.1-1-1.5-2.8-1.8-1.8-.3-2.8-.7-2.8-1.8S10.6 7 12 7c1.2 0 2.1.3 2.8 1" />
      </svg>
    );
  }
  if (name === "profile") {
    return (
      <svg aria-hidden="true" className="nav-icon" viewBox="0 0 24 24">
        <circle cx="12" cy="8.2" r="3.6" />
        <path d="M5.8 19.2c.8-3.4 3-5.2 6.2-5.2s5.4 1.8 6.2 5.2" />
      </svg>
    );
  }
  return (
    <svg aria-hidden="true" className="nav-icon" viewBox="0 0 24 24">
      <path d="M4.5 10.8 12 4.6l7.5 6.2" />
      <path d="M6.8 10.2v8.4h10.4v-8.4" />
      <path d="M10 18.6v-4.4h4v4.4" />
    </svg>
  );
}

export function BusinessMiniAppShell({ model }: { model: BusinessMiniAppModel }) {
  const { accessState, busy, business, canGoBack, goBack, loadBusinessOrders, loadCreditDashboard, loadHomeSummary, loadMyAds, notice, setView, user, view } = model;
  const [activeNav, setActiveNav] = useState<"home" | "ads" | "orders" | "credits" | "profile">("home");
  const previousViewRef = useRef<BusinessMiniAppView | null>(null);
  const viewStartedAtRef = useRef<number | null>(null);
  const termsRequired = view === "business-terms";
  const canUseBusinessNav = accessState === "ready" && !termsRequired;

  const openHome = () => {
    void loadHomeSummary();
  };

  const openAds = () => {
    if (view === "my-ads") {
      return;
    }
    void loadMyAds();
  };

  const openOrders = () => {
    if (view === "business-orders") {
      return;
    }
    void loadBusinessOrders();
  };

  const openCredits = () => {
    if (view === "credits-dashboard") {
      return;
    }
    void loadCreditDashboard();
  };

  const openProfile = () => {
    if (view === "business-settings") {
      return;
    }
    setView("business-settings");
  };

  useEffect(() => {
    const previousView = previousViewRef.current;
    if (viewStartedAtRef.current !== null) {
      recordSlowScreenTransition(view, previousView, elapsedMs(viewStartedAtRef.current));
    }
    recordScreenView(view, previousView);
    previousViewRef.current = view;
    viewStartedAtRef.current = typeof performance !== "undefined" && typeof performance.now === "function" ? performance.now() : Date.now();
  }, [view]);

  useEffect(() => {
    if (view === "credits-dashboard" || view === "buy-credits" || view === "credit-payment-pending" || view === "referrals") {
      setActiveNav("credits");
      return;
    }
    if (view === "create-ad" || view === "my-ads" || view === "archived-ads" || view === "payment-methods") {
      setActiveNav("ads");
      return;
    }
    if (view === "business-orders" || view === "business-order-detail" || view === "business-chat" || view === "business-support") {
      setActiveNav("orders");
      return;
    }
    if (view === "business-settings" || view === "business-pin" || view === "business-rules" || view === "business-terms") {
      setActiveNav("profile");
      return;
    }
    setActiveNav("home");
  }, [view]);

  return (
    <section className="business-shell" aria-live="polite">
      <div className="business-shell__header app-topbar">
        <div className="topbar-brand">
          <AnimatedLogo />
          <div className="topbar-wordmark">
            <strong>NODO</strong>
            <span>Negocio</span>
          </div>
        </div>
        <div className="topbar-user">
          <span className="topbar-avatar" aria-hidden="true">
            {(business?.business_name || user.first_name || user.username || "N").slice(0, 1).toUpperCase()}
          </span>
          <div>
            <span>{business?.business_name || user.first_name || user.username || "Negocio"}</span>
          </div>
        </div>
      </div>

      {canGoBack && canUseBusinessNav ? (
        <div className="screen-heading">
          <button className="topbar-back" type="button" aria-label="Volver" onClick={goBack}>
            <span aria-hidden="true" />
          </button>
          <Title level="2" className="business-shell__title">
            {TITLE_BY_VIEW[view] || "NODO Negocio"}
          </Title>
        </div>
      ) : null}

      {canUseBusinessNav ? (
        <div className="primary-nav">
          <button className={activeNav === "home" ? "nav-button is-active" : "nav-button"} type="button" onClick={openHome}>
            <NavIcon name="home" />
            <span>Inicio</span>
          </button>
          <button className={activeNav === "ads" ? "nav-button is-active" : "nav-button"} type="button" onClick={openAds}>
            <NavIcon name="ads" />
            <span>Anuncios</span>
          </button>
          <button className={activeNav === "orders" ? "nav-button is-active" : "nav-button"} type="button" onClick={openOrders}>
            <NavIcon name="orders" />
            <span>Ordenes</span>
          </button>
          <button className={activeNav === "credits" ? "nav-button is-active" : "nav-button"} type="button" onClick={openCredits}>
            <NavIcon name="credits" />
            <span>Creditos</span>
          </button>
          <button className={activeNav === "profile" ? "nav-button is-active" : "nav-button"} type="button" onClick={openProfile}>
            <NavIcon name="profile" />
            <span>Perfil</span>
          </button>
        </div>
      ) : null}

      {accessState === "loading" ? (
        <div className="shell-loading-pill">
          <Spinner size="s" />
          <Text>Cargando</Text>
        </div>
      ) : null}

      {notice ? <Text className="auth-entry__message">{notice}</Text> : null}

      <BusinessMiniAppScreens model={model} />
    </section>
  );
}
