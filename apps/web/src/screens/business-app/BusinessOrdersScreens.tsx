import { Button, Text, Title } from "@telegram-apps/telegram-ui";
import { formatOrderMethodLine } from "../../constants/paymentLabels";
import { humanizeOrderStatus, humanizePurchaseStatus } from "../../hooks/business-mini-app/helpers";
import type { BusinessMiniAppModel } from "../../hooks/useBusinessMiniAppModel";
import type { BusinessOrderSummary } from "../../types/orders";

function requiresBusinessAction(order: BusinessOrderSummary) {
  return (
    order.capabilities.can_confirm_payment
    || order.capabilities.can_reject_payment_report
    || order.capabilities.can_mark_delivered
    || order.status === "disputed"
  );
}

function operationBucket(order: BusinessOrderSummary) {
  if (requiresBusinessAction(order)) {
    return "Requiere accion";
  }
  if (order.status === "completed" || order.status === "cancelled" || order.status === "delivered") {
    return "Historial";
  }
  return "En curso";
}

function nextBusinessAction(order: BusinessOrderSummary) {
  if (order.capabilities.can_mark_delivered) {
    return "Pagar al cliente";
  }
  if (order.capabilities.can_confirm_payment || order.capabilities.can_reject_payment_report) {
    return "Verificar ingreso";
  }
  if (order.status === "disputed") {
    return "Responder soporte";
  }
  if (order.status === "waiting_payment") {
    return "Esperar pago";
  }
  return "Revisar";
}

export function IncomingOrdersScreen({ model }: { model: BusinessMiniAppModel }) {
  const { businessOrderFilter, businessOrders, loadBusinessOrders, openBusinessOrder } = model;
  const actionCount = businessOrders.filter(requiresBusinessAction).length;
  const inProgressCount = businessOrders.filter((order) => operationBucket(order) === "En curso").length;
  const historyCount = businessOrders.filter((order) => operationBucket(order) === "Historial").length;
  return (
    <div className="business-card">
      <Text className="business-card__label">Operaciones</Text>
      <Title level="3" className="business-shell__title">Bandeja operacional</Title>
      <div className="business-priority-list">
        <button className={businessOrderFilter === "open" ? "is-selected" : ""} type="button" onClick={() => void loadBusinessOrders("open")}>
          <span>Abiertas</span>
          <strong>{businessOrderFilter === "open" ? businessOrders.length : inProgressCount + actionCount}</strong>
        </button>
        <button className={businessOrderFilter === "payment_reported" ? "is-selected" : ""} type="button" onClick={() => void loadBusinessOrders("payment_reported")}>
          <span>Por verificar</span>
          <strong>{actionCount}</strong>
        </button>
        <button className={businessOrderFilter === "history" ? "is-selected" : ""} type="button" onClick={() => void loadBusinessOrders("history")}>
          <span>Historial</span>
          <strong>{businessOrderFilter === "history" ? businessOrders.length : historyCount}</strong>
        </button>
      </div>
      <div className="business-shell__tabs">
        <Button mode="outline" size="s" onClick={() => void loadBusinessOrders("payment_reported")}>Verificar</Button>
        <Button mode="outline" size="s" onClick={() => void loadBusinessOrders("payment_confirmed")}>Pagar</Button>
        <Button mode="outline" size="s" onClick={() => void loadBusinessOrders("delivered")}>Enviadas</Button>
      </div>
      <div className="business-list business-list--scrollable">
        {businessOrders.length === 0 ? <Text>{businessOrderFilter === "history" ? "No hay ordenes completadas todavia." : "No hay ordenes abiertas por ahora."}</Text> : null}
        {businessOrders.map((order) => (
          <button className="business-row order-row" key={order.id} type="button" onClick={() => void openBusinessOrder(order.id)}>
            <span>
              <strong>Orden {order.public_order_code}</strong>
              <small>{humanizeOrderStatus(order.status)}</small>
            </span>
            <span>{nextBusinessAction(order)}</span>
            <span>{order.amount_usd} USD</span>
          </button>
        ))}
      </div>
    </div>
  );
}

export function BusinessOrderDetailScreen({ model }: { model: BusinessMiniAppModel }) {
  const { businessOrderAction, businessOrderDetail, businessOrderReason, busy, mutateBusinessOrder, openBusinessChat, setBusinessOrderReason } = model;
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
          <Text className="auth-entry__session-meta">Receptor: {businessOrderDetail.receiver_data.bank || "Banco"} - {businessOrderDetail.receiver_data.phone_masked || "enmascarado"} - {businessOrderDetail.receiver_data.holder || "Titular"}</Text>
          {businessOrderDetail.payment_report ? (
            <div className="business-grid">
              <Text>Reporte: {humanizePurchaseStatus(businessOrderDetail.payment_report.status)}</Text>
              <Text>Monto: {businessOrderDetail.payment_report.payment_amount}</Text>
              <Text>Referencia: {businessOrderDetail.payment_report.payment_reference_masked || businessOrderDetail.payment_report.tx_hash_masked || "enmascarada"}</Text>
              <Text>Evidencia: {businessOrderDetail.evidence.length}</Text>
            </div>
          ) : <Text>No hay reporte pendiente.</Text>}
          <label className="business-field">
            <span>Motivo operativo</span>
            <textarea value={businessOrderReason} onChange={(event) => setBusinessOrderReason(event.target.value)} />
          </label>
          <div className="business-shell__tabs">
            <Button mode="filled" size="s" disabled={businessOrderAction === "confirm-payment" || !businessOrderDetail.order.capabilities.can_confirm_payment} onClick={() => void mutateBusinessOrder("confirm-payment")}>
              {businessOrderAction === "confirm-payment" ? "Confirmando..." : "Confirmar pago"}
            </Button>
            <Button mode="outline" size="s" disabled={businessOrderAction === "reject-payment-report" || !businessOrderDetail.order.capabilities.can_reject_payment_report} onClick={() => void mutateBusinessOrder("reject-payment-report")}>
              {businessOrderAction === "reject-payment-report" ? "Rechazando..." : "Rechazar reporte"}
            </Button>
            <Button mode="filled" size="s" disabled={businessOrderAction === "mark-delivered" || !businessOrderDetail.order.capabilities.can_mark_delivered} onClick={() => void mutateBusinessOrder("mark-delivered")}>
              {businessOrderAction === "mark-delivered" ? "Marcando..." : "Marcar enviado"}
            </Button>
            <Button mode="outline" size="s" disabled={busy} onClick={() => void openBusinessChat(businessOrderDetail.order.id)}>Chat</Button>
          </div>
        </>
      ) : <Text>Selecciona una orden para ver el detalle.</Text>}
    </div>
  );
}
