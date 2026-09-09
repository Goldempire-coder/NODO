import { Button, Text, Title } from "@telegram-apps/telegram-ui";
import { formatOrderMethodLine } from "../../constants/paymentLabels";
import { humanizeOrderStatus, humanizePurchaseStatus } from "../../hooks/business-mini-app/helpers";
import type { BusinessMiniAppModel } from "../../hooks/useBusinessMiniAppModel";
import type { BusinessOrderSummary } from "../../types/orders";

function canReportPaymentProblem(order: BusinessOrderSummary) {
  return order.status === "payment_reported" && order.capabilities.can_open_dispute;
}

function requiresBusinessAction(order: BusinessOrderSummary) {
  return (
    order.capabilities.can_confirm_payment
    || canReportPaymentProblem(order)
    || order.capabilities.can_mark_delivered
    || order.status === "disputed"
  );
}

function requiresBusinessAttention(order: BusinessOrderSummary) {
  return order.status === "waiting_payment" || requiresBusinessAction(order);
}

function nextBusinessAction(order: BusinessOrderSummary) {
  if (order.capabilities.can_mark_delivered) {
    return "Completar entrega acordada";
  }
  if (order.capabilities.can_confirm_payment || canReportPaymentProblem(order)) {
    return "Verificar ingreso";
  }
  if (order.status === "disputed") {
    return "Responder soporte";
  }
  if (order.status === "waiting_payment") {
    return "Abrir chat";
  }
  return "Revisar";
}

function BusinessOrderInboxTab({
  ariaLabel,
  count,
  filter,
  label,
  loaded,
  onSelect,
  selected
}: {
  ariaLabel: string;
  count: number;
  filter: string;
  label: string;
  loaded: boolean;
  onSelect: (filter: string) => void;
  selected: boolean;
}) {
  return (
    <button aria-label={ariaLabel} className={selected ? "is-selected" : ""} type="button" onClick={() => onSelect(filter)}>
      <span>{label}</span>
      {loaded ? <strong>{count}</strong> : <span className="business-order-tab__action">Ver</span>}
    </button>
  );
}

export function IncomingOrdersScreen({ model }: { model: BusinessMiniAppModel }) {
  const {
    businessOrderFilter,
    businessOrderFilterCounts,
    businessOrderLoadingMore,
    businessOrderNextCursor,
    businessOrders,
    loadBusinessOrders,
    loadMoreBusinessOrders,
    loadedBusinessOrderFilters,
    openBusinessOrder
  } = model;
  const filterCount = (filter: string) => businessOrderFilterCounts[filter] ?? 0;
  return (
    <div className="business-card">
      <Text className="business-card__label">Operaciones</Text>
      <Title level="3" className="business-shell__title">Bandeja operacional</Title>
      <div className="business-priority-list">
        <BusinessOrderInboxTab
          ariaLabel="Ver órdenes abiertas"
          count={filterCount("open")}
          filter="open"
          label="Abiertas"
          loaded={loadedBusinessOrderFilters.has("open")}
          selected={businessOrderFilter === "open"}
          onSelect={(filter) => void loadBusinessOrders(filter)}
        />
        <BusinessOrderInboxTab
          ariaLabel="Ver órdenes por verificar"
          count={filterCount("payment_reported")}
          filter="payment_reported"
          label="Por verificar"
          loaded={loadedBusinessOrderFilters.has("payment_reported")}
          selected={businessOrderFilter === "payment_reported"}
          onSelect={(filter) => void loadBusinessOrders(filter)}
        />
        <BusinessOrderInboxTab
          ariaLabel="Ver historial de órdenes"
          count={filterCount("history")}
          filter="history"
          label="Historial"
          loaded={loadedBusinessOrderFilters.has("history")}
          selected={businessOrderFilter === "history"}
          onSelect={(filter) => void loadBusinessOrders(filter)}
        />
      </div>
      <div className="business-shell__tabs">
        <Button mode="outline" size="s" onClick={() => void loadBusinessOrders("payment_reported")}>Verificar</Button>
        <Button mode="outline" size="s" onClick={() => void loadBusinessOrders("payment_confirmed")}>Entrega pendiente</Button>
        <Button mode="outline" size="s" onClick={() => void loadBusinessOrders("delivered")}>Entrega realizada</Button>
      </div>
      <div className="business-list business-list--scrollable">
        {businessOrders.length === 0 ? (
          <div className="business-order-empty">
            <Text>
              {businessOrderFilter === "history"
                ? "No hay operaciones cerradas todavia."
                : businessOrderFilter === "payment_reported"
                  ? "No hay ordenes por verificar ahora."
                  : "No hay ordenes abiertas por ahora."}
            </Text>
            {businessOrderFilter === "open" ? (
              <>
                <Text className="business-order-empty__hint">Puedes revisar Por verificar o Historial cuando lo necesites.</Text>
                <div className="business-order-empty__actions">
                  <Button mode="outline" size="s" onClick={() => void loadBusinessOrders("payment_reported")}>Por verificar</Button>
                  <Button mode="outline" size="s" onClick={() => void loadBusinessOrders("history")}>Historial</Button>
                </div>
              </>
            ) : null}
          </div>
        ) : null}
        {businessOrders.map((order) => (
          <button className={`business-row order-row${requiresBusinessAttention(order) ? " order-row--attention" : ""}`} key={order.id} type="button" onClick={() => void openBusinessOrder(order.id)}>
            <span>
              <strong>
                Orden {order.public_order_code}
                {requiresBusinessAttention(order) ? (
                  <small className="order-row__badge">{order.status === "waiting_payment" ? "Nueva" : "Accion"}</small>
                ) : null}
              </strong>
              <small>{humanizeOrderStatus(order.status)}</small>
            </span>
            <span>{nextBusinessAction(order)}</span>
            <span>{order.amount_usd} USD</span>
          </button>
        ))}
        {businessOrderNextCursor ? (
          <Button mode="outline" size="s" disabled={businessOrderLoadingMore} onClick={() => void loadMoreBusinessOrders()}>
            {businessOrderLoadingMore ? "Cargando..." : "Cargar mas"}
          </Button>
        ) : null}
      </div>
    </div>
  );
}

export function BusinessOrderDetailScreen({ model }: { model: BusinessMiniAppModel }) {
  const { businessOrderAction, businessOrderDetail, businessOrderInlineNotice, businessOrderReason, busy, mutateBusinessOrder, openBusinessChat, setBusinessOrderReason } = model;
  const shouldHandleInChat = Boolean(
    businessOrderDetail?.order.capabilities.can_confirm_payment
    || businessOrderDetail?.order.capabilities.can_mark_delivered
  );
  const canReportCurrentPaymentProblem = Boolean(
    businessOrderDetail && canReportPaymentProblem(businessOrderDetail.order)
  );
  return (
    <div className="business-card">
      <Text className="business-card__label">Detalle</Text>
      {businessOrderDetail ? (
        <>
          <Title level="3" className="business-shell__title">{businessOrderDetail.order.public_order_code}</Title>
          <div className="payment-copy-box payment-copy-box--compact">
            <div>
              <Text className="business-card__label">Numero de orden</Text>
              <strong>{businessOrderDetail.order.public_order_code}</strong>
            </div>
          </div>
          <Text>{humanizeOrderStatus(businessOrderDetail.order.status)}</Text>
          <Text>{businessOrderDetail.order.amount_usd} USD - {businessOrderDetail.order.amount_bs_calculated} Bs</Text>
          <Text>{formatOrderMethodLine(businessOrderDetail.order.payment_method_snapshot, businessOrderDetail.order.delivery_method_snapshot)}</Text>
          {businessOrderDetail.order.capabilities.receiver_details_shared ? (
            <Text className="auth-entry__session-meta">
              Datos de entrega disponibles. Abre el chat para consultarlos.
            </Text>
          ) : (
            <Text className="auth-entry__session-meta">
              Entrega pendiente en chat
            </Text>
          )}
          {businessOrderDetail.payment_report ? (
            <div className="business-grid">
              <Text>Reporte: {humanizePurchaseStatus(businessOrderDetail.payment_report.status)}</Text>
              <Text>Monto: {businessOrderDetail.payment_report.payment_amount}</Text>
              <Text>Referencia: {businessOrderDetail.payment_report.payment_reference_masked || businessOrderDetail.payment_report.tx_hash_masked || "enmascarada"}</Text>
              <Text>Evidencia: {businessOrderDetail.evidence.length}</Text>
            </div>
          ) : <Text>No hay reporte pendiente.</Text>}
          {businessOrderInlineNotice ? (
            <Text className="auth-entry__message" role="status">
              {businessOrderInlineNotice}
            </Text>
          ) : null}
          {!businessOrderDetail.order.capabilities.can_decline_before_payment ? (
            <label className="business-field">
              <span>Motivo operativo</span>
              <textarea value={businessOrderReason} onChange={(event) => setBusinessOrderReason(event.target.value)} />
            </label>
          ) : null}
          <div className="business-shell__tabs">
            {shouldHandleInChat ? (
              <Button mode="filled" size="s" onClick={() => void openBusinessChat(businessOrderDetail.order.id)}>Abrir chat</Button>
            ) : null}
            {canReportCurrentPaymentProblem ? (
              <Button mode="outline" size="s" disabled={businessOrderAction === "report-payment-problem"} onClick={() => void mutateBusinessOrder("report-payment-problem")}>
                {businessOrderAction === "report-payment-problem" ? "Reportando..." : "Reportar problema con pago"}
              </Button>
            ) : null}
            {businessOrderDetail.order.capabilities.can_decline_before_payment ? (
              <Button mode="outline" size="s" disabled={businessOrderAction === "cannot-attend"} onClick={() => void mutateBusinessOrder("cannot-attend")}>
                {businessOrderAction === "cannot-attend" ? "Cancelando..." : "No puedo atender"}
              </Button>
            ) : null}
            {!shouldHandleInChat ? (
              <Button mode="outline" size="s" disabled={busy} onClick={() => void openBusinessChat(businessOrderDetail.order.id)}>Chat</Button>
            ) : null}
          </div>
        </>
      ) : busy ? (
        <div className="business-order-empty" role="status">
          <Text>Cargando orden...</Text>
        </div>
      ) : <Text>Selecciona una orden para ver el detalle.</Text>}
    </div>
  );
}
