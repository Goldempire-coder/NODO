import { Button, Text, Title } from "@telegram-apps/telegram-ui";
import { formatOrderMethodLine } from "../../constants/paymentLabels";
import { humanizeOrderStatus, humanizePurchaseStatus } from "../../hooks/business-mini-app/helpers";
import type { BusinessMiniAppModel } from "../../hooks/useBusinessMiniAppModel";

export function IncomingOrdersScreen({ model }: { model: BusinessMiniAppModel }) {
  const { businessOrders, loadBusinessOrders, openBusinessOrder } = model;
  return (
    <div className="business-card">
      <Text className="business-card__label">Ordenes</Text>
      <Text className="auth-entry__session-meta">Aqui ves solo las ordenes de tu negocio.</Text>
      <div className="business-shell__tabs">
        <Button mode="outline" size="s" onClick={() => void loadBusinessOrders("payment_reported")}>Por revisar</Button>
        <Button mode="outline" size="s" onClick={() => void loadBusinessOrders("payment_confirmed")}>Por entregar</Button>
        <Button mode="outline" size="s" onClick={() => void loadBusinessOrders("delivered")}>Enviadas</Button>
      </div>
      <div className="business-list">
        {businessOrders.length === 0 ? <Text>No hay ordenes entrantes por ahora.</Text> : null}
        {businessOrders.map((order) => (
          <button className="business-row ad-row" key={order.id} type="button" onClick={() => void openBusinessOrder(order.id)}>
            <span>{order.public_order_code}</span>
            <span>{humanizeOrderStatus(order.status)}</span>
            <span>{order.amount_usd} USD</span>
            <span>{order.receiver_data_masked?.phone || "enmascarado"}</span>
          </button>
        ))}
      </div>
    </div>
  );
}

export function BusinessOrderDetailScreen({ model }: { model: BusinessMiniAppModel }) {
  const { businessOrderDetail, businessOrderReason, busy, mutateBusinessOrder, openBusinessChat, setBusinessOrderReason } = model;
  return (
    <div className="business-card">
      <Text className="business-card__label">Detalle</Text>
      {businessOrderDetail ? (
        <>
          <Title level="3" className="business-shell__title">{businessOrderDetail.order.public_order_code}</Title>
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
            <Button mode="filled" size="s" disabled={busy || !businessOrderDetail.order.capabilities.can_confirm_payment} onClick={() => void mutateBusinessOrder("confirm-payment")}>Confirmar pago</Button>
            <Button mode="outline" size="s" disabled={busy || !businessOrderDetail.order.capabilities.can_reject_payment_report} onClick={() => void mutateBusinessOrder("reject-payment-report")}>Rechazar reporte</Button>
            <Button mode="filled" size="s" disabled={busy || !businessOrderDetail.order.capabilities.can_mark_delivered} onClick={() => void mutateBusinessOrder("mark-delivered")}>Marcar enviado</Button>
            <Button mode="outline" size="s" disabled={busy} onClick={() => void openBusinessChat(businessOrderDetail.order.id)}>Chat</Button>
          </div>
          <Text className="auth-entry__session-meta">Confirmar pago consume creditos. Marcar enviado es una accion separada.</Text>
        </>
      ) : <Text>Selecciona una orden para ver el detalle.</Text>}
    </div>
  );
}
