import { Button, Text, Title } from "@telegram-apps/telegram-ui";
import { AttentionBadge } from "../../components/nodo/SurfaceAttention";
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
  const {
    attentionCounts,
    attentionTruncated,
    business,
    businessCapacity,
    businessCapacityDraft,
    businessCapacityRefreshState,
    businessOrders,
    creditWallet,
    creditWalletRefreshState,
    homeSummaryState,
    loadBusinessOrders,
    loadCreditDashboard,
    loadMyAds,
    openBusinessSupport,
    ownAds,
    paymentMethods,
    saveBusinessCapacity,
    savingBusinessCapacity,
    setBusinessAvailability,
    setBusinessCapacityDraft,
    setView,
    updatingAvailability
  } = model;
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
  const effectiveCapacity = Number(businessCapacity?.effective_available_capacity_usd || 0);

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
        <button type="button" onClick={() => void loadBusinessOrders("open")}>
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
          {creditWalletRefreshState === "stale" ? <small>Saldo sin actualizar</small> : null}
        </button>
      </div>
      <div className="business-status-panel business-status-panel--compact">
        <div>
          <div>
            <strong>Capacidad operativa</strong>
            <small>Declarada ${businessCapacity?.declared_available_capacity_usd ?? "0.00"}</small>
            <small>
              Reservada ${businessCapacity?.reserved_capacity_usd ?? "0.00"} / Disponible ${businessCapacity?.effective_available_capacity_usd ?? "0.00"}
            </small>
            <small>Limite diario ${businessCapacity?.daily_limit_usd ?? business?.daily_limit_usd ?? "0.00"}</small>
            <small>
              Reservado activo ${businessCapacity?.daily_reserved_usd ?? "0.00"} / Consumido hoy ${businessCapacity?.daily_consumed_usd ?? "0.00"}
            </small>
            <small>Restante diario ${businessCapacity?.daily_remaining_usd ?? "0.00"}</small>
            <small>Reinicio diario: 00:00 UTC</small>
            {businessCapacityRefreshState === "stale" ? <small>Mostrando el ultimo valor disponible.</small> : null}
            {businessCapacity && effectiveCapacity < 20 ? <small>Configura al menos $20 para recibir nuevas ordenes.</small> : null}
            {businessCapacity?.capabilities.daily_limit_reached ? <small>Alcanzaste el limite operativo de hoy.</small> : null}
          </div>
        </div>
        <div className="business-inline-form">
          <label>
            <span>Disponible ahora (USD)</span>
            <input
              inputMode="decimal"
              value={businessCapacityDraft}
              onChange={(event) => setBusinessCapacityDraft(event.target.value)}
            />
          </label>
          <Button
            mode="outline"
            size="s"
            disabled={savingBusinessCapacity}
            onClick={() => void saveBusinessCapacity()}
          >
            {savingBusinessCapacity ? "Guardando..." : "Actualizar"}
          </Button>
        </div>
      </div>
      <div className="business-grid">
        <Button mode="filled" size="s" onClick={() => setView("create-ad")}>
          Crear anuncio
        </Button>
        <Button mode="outline" size="s" onClick={() => void loadMyAds()}>
          Mis anuncios
        </Button>
        <Button mode="outline" size="s" onClick={() => void loadBusinessOrders("open")}>
          Operaciones abiertas
        </Button>
        <Button mode="outline" size="s" onClick={() => void loadCreditDashboard()}>
          Creditos
        </Button>
        <Button mode="outline" size="s" onClick={openBusinessSupport}>
          Soporte NODO
          <AttentionBadge
            count={attentionCounts.support}
            label="respuestas pendientes"
            truncated={attentionTruncated.support}
          />
        </Button>
        <Button mode="outline" size="s" onClick={() => setView("payment-methods")}>
          Zelle / USDT
        </Button>
      </div>
    </div>
  );
}
