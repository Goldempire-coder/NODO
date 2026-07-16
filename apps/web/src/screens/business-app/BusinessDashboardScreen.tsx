import { Button, Text, Title } from "@telegram-apps/telegram-ui";
import type { BusinessMiniAppModel } from "../../hooks/useBusinessMiniAppModel";
import { paymentMethodCanReceive } from "./ads/businessAdViewHelpers";

function countActionableOrders(model: BusinessMiniAppModel) {
  return model.businessOrders.filter((order) => (
    order.capabilities.can_confirm_payment
    || order.capabilities.can_reject_payment_report
    || order.capabilities.can_mark_delivered
    || order.status === "disputed"
  )).length;
}

export function BusinessDashboardScreen({ model }: { model: BusinessMiniAppModel }) {
  const { business, businessOrders, creditWallet, homeSummaryState, loadBusinessOrders, loadCreditDashboard, loadMyAds, ownAds, paymentMethods, setBusinessAvailability, setView, updatingAvailability } = model;
  const hasPaymentMethods = paymentMethods.length > 0;
  const isApproved = business?.verification_status === "approved";
  const isAcceptingOrders = business?.is_accepting_orders !== false;
  const actionableOrders = countActionableOrders(model);
  const visibleAds = isAcceptingOrders
    ? ownAds.filter((ad) => (ad.effective_status || ad.status) === "active" && paymentMethodCanReceive(ad, paymentMethods)).length
    : 0;
  const occupiedAds = ownAds.filter((ad) => ad.status === "in_order").length;
  const availableCredits = creditWallet?.available_credits;
  const blockedCredits = creditWallet?.blocked_credits;
  const consumedCredits = creditWallet?.consumed_credits;
  const isRefreshing = homeSummaryState === "loading";

  return (
    <div className="business-card">
      <Text className="business-card__label">Resumen</Text>
      <Title level="3" className="business-shell__title">
        {business?.business_name || "NODO Negocio"}
      </Title>
      {homeSummaryState === "loading" ? (
        <Text className="business-card__label">Actualizando resumen...</Text>
      ) : homeSummaryState === "error" ? (
        <Text className="business-card__label">No se pudo actualizar todo el resumen. Abre cada seccion para refrescar.</Text>
      ) : null}
      <div className="business-status-panel business-status-panel--compact">
        <div>
          <span className={hasPaymentMethods && isAcceptingOrders ? "status-dot" : "status-dot status-dot--muted"} aria-hidden="true" />
          <div>
            <strong>{!hasPaymentMethods ? "Agrega un metodo de cobro" : isAcceptingOrders ? "Online: listo para recibir ordenes" : "Offline: no recibes nuevas ordenes"}</strong>
            <small>{isAcceptingOrders ? "Anuncios activos visibles." : "Tus anuncios activos quedan ocultos hasta volver online."}</small>
            <small>Rango autorizado: {business?.min_order_amount_usd || "20.00"} - {business?.max_order_amount_usd || "100.00"} USD</small>
          </div>
        </div>
        <Button
          mode={isAcceptingOrders ? "outline" : "filled"}
          size="s"
          disabled={!isApproved || updatingAvailability}
          onClick={() => void setBusinessAvailability(!isAcceptingOrders)}
        >
          {updatingAvailability ? "Guardando..." : isAcceptingOrders ? "Poner offline" : "Poner online"}
        </Button>
      </div>
      <div className="business-priority-list">
        <button type="button" onClick={() => void loadBusinessOrders("payment_reported")}>
          <span>Requieren accion</span>
          <strong>{actionableOrders || businessOrders.filter((order) => order.status === "payment_reported").length}</strong>
        </button>
        <button type="button" onClick={() => void loadMyAds()}>
          <span>Anuncios visibles</span>
          <strong>{visibleAds}</strong>
        </button>
        <button type="button" onClick={() => void loadMyAds()}>
          <span>Anuncios ocupados</span>
          <strong>{occupiedAds}</strong>
        </button>
        <button type="button" onClick={() => void loadCreditDashboard()}>
          <span>Creditos disponibles</span>
          <strong>{isRefreshing ? "..." : availableCredits ?? "-"}</strong>
          <small>Bloq. {isRefreshing ? "..." : blockedCredits ?? "-"} / Cons. {isRefreshing ? "..." : consumedCredits ?? "-"}</small>
        </button>
      </div>
      <div className="business-grid">
        <Button mode="filled" size="s" onClick={() => setView("create-ad")}>
          Crear anuncio
        </Button>
        <Button mode="outline" size="s" onClick={() => void loadMyAds()}>
          Mis anuncios
        </Button>
        <Button mode="outline" size="s" onClick={() => void loadBusinessOrders("payment_reported")}>
          Ordenes por revisar
        </Button>
        <Button mode="outline" size="s" onClick={() => void loadCreditDashboard()}>
          Creditos
        </Button>
        <Button mode="outline" size="s" onClick={() => setView("business-support")}>
          Soporte NODO
        </Button>
        {!hasPaymentMethods ? (
          <Button mode="outline" size="s" onClick={() => setView("payment-methods")}>
            Metodos
          </Button>
        ) : null}
      </div>
    </div>
  );
}
