import { Button, Text, Title } from "@telegram-apps/telegram-ui";
import { formatOrderMethodLine } from "../../constants/paymentLabels";
import { sanitizeDecimalInput } from "../../lib/numericInput";
import { displayBusinessName, type RemitterScreensModel } from "./RemitterScreens.types";

const CHAT_STATUSES = ["payment_reported", "payment_rejected", "payment_confirmed", "delivered", "disputed"];

export function ClientOrderScreens({ model }: { model: RemitterScreensModel }) {
  const {
    cancelOrder,
    cancellingOrderId,
    createOrder,
    creatingOrder,
    extendOrder,
    extendingOrderId,
    loadingOrders,
    loadingPaymentInstructions,
    myOrders,
    openingChatOrderId,
    openingOrderId,
    openOrderChat,
    openOrderDetail,
    openPaymentInstructions,
    orderForm,
    selectedAd,
    selectedOrder,
    setOrderForm,
    view
  } = model;

  return (
    <>
      {view === "create-order" ? (
        <div className="business-card">
          <Text className="business-card__label">Datos del receptor</Text>
          {selectedAd ? (
            <>
              <Text>{displayBusinessName(selectedAd)}</Text>
              <Text>Rango {selectedAd.amount_min_usd}-{selectedAd.amount_max_usd} USD</Text>
              <Text>Tasa {selectedAd.rate_bs_per_usd} Bs/USD</Text>
              <label className="business-field">
                <span>Monto USD</span>
                <input value={orderForm.amount_usd} onChange={(event) => setOrderForm((current) => ({ ...current, amount_usd: sanitizeDecimalInput(event.target.value, { maxDecimals: 2, maxIntegerDigits: 6 }) }))} inputMode="decimal" pattern="[0-9]*[.]?[0-9]*" autoComplete="off" />
              </label>
              <label className="business-field">
                <span>Banco receptor</span>
                <input value={orderForm.bank} onChange={(event) => setOrderForm((current) => ({ ...current, bank: event.target.value }))} />
              </label>
              <label className="business-field">
                <span>Telefono receptor</span>
                <input value={orderForm.phone} onChange={(event) => setOrderForm((current) => ({ ...current, phone: event.target.value }))} />
              </label>
              <label className="business-field">
                <span>Documento receptor</span>
                <input value={orderForm.document} onChange={(event) => setOrderForm((current) => ({ ...current, document: event.target.value }))} />
              </label>
              <label className="business-field">
                <span>Titular receptor</span>
                <input value={orderForm.holder} onChange={(event) => setOrderForm((current) => ({ ...current, holder: event.target.value }))} />
              </label>
              <Button mode="filled" stretched disabled={creatingOrder || !orderForm.amount_usd || !orderForm.bank || !orderForm.phone || !orderForm.document || !orderForm.holder} onClick={() => void createOrder()}>
                {creatingOrder ? "Creando..." : "Crear orden"}
              </Button>
            </>
          ) : (
            <Text>Selecciona un negocio disponible para crear una orden.</Text>
          )}
        </div>
      ) : null}

      {view === "order-summary" ? (
        <div className="business-card">
          <Text className="business-card__label">Resumen de la orden</Text>
          {selectedOrder ? (
            <>
              <Title level="3" className="business-shell__title">{selectedOrder.public_order_code}</Title>
              <Text>{selectedOrder.business_name}</Text>
              <Text>{selectedOrder.status}</Text>
              <Text>{selectedOrder.amount_usd} USD - {selectedOrder.amount_bs_calculated} Bs</Text>
              <Text>Tasa {selectedOrder.rate_snapshot} Bs/USD</Text>
              <Text>{formatOrderMethodLine(selectedOrder.payment_method_snapshot, selectedOrder.delivery_method_snapshot)}</Text>
              <Text className="auth-entry__session-meta">Cuenta: {selectedOrder.payment_instructions_masked.account_masked || "masked"}</Text>
              <Text className="auth-entry__session-meta">Receptor: {selectedOrder.receiver_data_masked.bank || "Banco"} - {selectedOrder.receiver_data_masked.phone || "masked"}</Text>
              <Text>Límite: {new Date(selectedOrder.payment_report_deadline_at).toLocaleString()}</Text>
              <Button mode="filled" stretched disabled={loadingPaymentInstructions || selectedOrder.status !== "waiting_payment"} onClick={() => void openPaymentInstructions(selectedOrder.id)}>
                {loadingPaymentInstructions ? "Cargando instrucciones..." : "Ver instrucciones de pago"}
              </Button>
              <div className="business-shell__tabs">
                <Button mode="outline" size="s" disabled={extendingOrderId === selectedOrder.id || selectedOrder.status !== "waiting_payment" || selectedOrder.extension_used} onClick={() => void extendOrder(selectedOrder.id)}>
                  {extendingOrderId === selectedOrder.id ? "Extendiendo..." : "Extender"}
                </Button>
                <Button mode="outline" size="s" disabled={cancellingOrderId === selectedOrder.id || selectedOrder.status !== "waiting_payment"} onClick={() => void cancelOrder(selectedOrder.id)}>
                  {cancellingOrderId === selectedOrder.id ? "Cancelando..." : "Cancelar"}
                </Button>
                <Button mode="outline" size="s" disabled={openingChatOrderId === selectedOrder.id || !CHAT_STATUSES.includes(selectedOrder.status)} onClick={() => void openOrderChat(selectedOrder.id)}>
                  {openingChatOrderId === selectedOrder.id ? "Abriendo..." : "Chat"}
                </Button>
              </div>
            </>
          ) : (
            <Text>No hay una orden seleccionada.</Text>
          )}
        </div>
      ) : null}

      {view === "my-orders" ? (
        <div className="business-card">
          <Text className="business-card__label">Mis órdenes</Text>
          <div className="business-list">
            {loadingOrders ? <Text>Cargando órdenes...</Text> : null}
            {myOrders.length === 0 && !loadingOrders ? <Text>Todavía no tienes órdenes.</Text> : null}
            {myOrders.map((order) => (
              <button className="business-row ad-row" disabled={openingOrderId === order.id} key={order.id} type="button" onClick={() => void openOrderDetail(order.id)}>
                <span>{order.public_order_code}</span>
                <span>{openingOrderId === order.id ? "Abriendo..." : order.status}</span>
                <span>{order.amount_usd} USD</span>
              </button>
            ))}
          </div>
        </div>
      ) : null}

      {view === "messages" ? (
        <div className="business-card">
          <Text className="business-card__label">Mensajes</Text>
          <div className="business-list">
            {loadingOrders ? <Text>Cargando conversaciones...</Text> : null}
            {myOrders.length === 0 && !loadingOrders ? <Text>Todavía no tienes conversaciones.</Text> : null}
            {myOrders.map((order) => {
              const canOpenChat = CHAT_STATUSES.includes(order.status);
              return (
                <button className="business-row ad-row" disabled={!canOpenChat || openingChatOrderId === order.id} key={order.id} type="button" onClick={() => void openOrderChat(order.id)}>
                  <span>{order.public_order_code}</span>
                  <span>{openingChatOrderId === order.id ? "Abriendo..." : canOpenChat ? "Abrir chat" : "Sin chat aún"}</span>
                  <span>{order.status}</span>
                </button>
              );
            })}
          </div>
          <Text className="auth-entry__session-meta">El chat se activa cuando la orden avanza a una etapa operativa.</Text>
        </div>
      ) : null}
    </>
  );
}
