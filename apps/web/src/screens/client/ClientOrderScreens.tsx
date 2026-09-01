import { Button, Text, Title } from "@telegram-apps/telegram-ui";
import { useEffect, useState } from "react";
import { AttentionBadge } from "../../components/nodo/SurfaceAttention";
import {
  formatOrderMethodLine,
  paymentMethodCurrencyPresentation
} from "../../constants/paymentLabels";
import type { OrderCancelReason } from "../../types/orders";
import { clientOrderStatusLabel } from "./clientOrderPresentation";
import { ClientOperationReportPanel } from "./ClientOperationReportPanel";
import { displayBusinessName, type RemitterScreensModel } from "./RemitterScreens.types";

const CHAT_STATUSES = ["waiting_payment", "payment_reported", "payment_rejected", "payment_confirmed", "delivered", "disputed"];

function quotedAmountBs(amountUsd: string, rateBsPerUsd: string): string {
  const amount = Number(amountUsd);
  const rate = Number(rateBsPerUsd);
  if (!Number.isFinite(amount) || !Number.isFinite(rate)) {
    return "0.00";
  }
  return (amount * rate).toFixed(2);
}

export function ClientOrderScreens({ model }: { model: RemitterScreensModel }) {
  const {
    attentionCounts,
    attentionTruncated,
    cancelOrder,
    cancellingOrderId,
    createOrder,
    creatingOrder,
    extendOrder,
    extendingOrderId,
    loadingOrders,
    loadingMoreMyOrders,
    loadMoreMyOrders,
    myOrders,
    myOrdersNextCursor,
    notice,
    openingChatOrderId,
    openingOrderId,
    openOrderChat,
    openOrderDetail,
    openClientSupport,
    orderForm,
    selectedAd,
    selectedOrder,
    selectedRatingStars,
    setView,
    setSelectedRatingStars,
    submitOrderRating,
    submittingRatingOrderId,
    view
  } = model;
  const [cancelPromptOrderId, setCancelPromptOrderId] = useState<string | null>(null);
  const [cancelReason, setCancelReason] = useState<OrderCancelReason>(
    "choose_another_business"
  );

  useEffect(() => {
    if (cancelPromptOrderId && cancelPromptOrderId !== selectedOrder?.id) {
      setCancelPromptOrderId(null);
    }
  }, [cancelPromptOrderId, selectedOrder?.id]);

  const selectedAdCurrency = paymentMethodCurrencyPresentation(
    selectedAd?.payment_method
  );
  const selectedOrderCurrency = paymentMethodCurrencyPresentation(
    selectedOrder?.payment_method_snapshot
  );

  return (
    <>
      {view === "create-order" ? (
        <div className="business-card">
          <Text className="business-card__label">Confirmar negociacion</Text>
          {selectedAd ? (
            <>
              <Title level="3" className="business-shell__title">{displayBusinessName(selectedAd)}</Title>
              <div className="business-grid marketplace-confirmation">
                <Text>Tasa: {selectedAd.rate_bs_per_usd} Bs. / {selectedAdCurrency.currencyLabel}</Text>
                <Text>Monto que entregas: {orderForm.amount_usd} {selectedAdCurrency.currencyLabel}</Text>
                <Text>Monto que recibe: {quotedAmountBs(orderForm.amount_usd, selectedAd.rate_bs_per_usd)} Bs</Text>
                <Text>Metodo: {formatOrderMethodLine(selectedAd.payment_method, selectedAd.delivery_method)}</Text>
              </div>
              {notice ? (
                <Text className="auth-entry__message" role={notice === "Preparando tu orden" ? "status" : "alert"}>
                  {notice}
                </Text>
              ) : null}
              <div className="business-shell__tabs">
                <Button mode="outline" size="s" disabled={creatingOrder} onClick={() => setView("marketplace-detail")}>
                  Volver
                </Button>
                <Button mode="filled" size="s" disabled={creatingOrder || !orderForm.amount_usd} onClick={() => void createOrder()}>
                  {creatingOrder ? "Confirmando..." : "Confirmar negociacion"}
                </Button>
              </div>
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
              <Text>{clientOrderStatusLabel(selectedOrder)}</Text>
              <Text>{selectedOrder.amount_usd} {selectedOrderCurrency.currencyLabel} - {selectedOrder.amount_bs_calculated} Bs</Text>
              <Text>Tasa {selectedOrder.rate_snapshot} Bs. / {selectedOrderCurrency.currencyLabel}</Text>
              <Text>{formatOrderMethodLine(selectedOrder.payment_method_snapshot, selectedOrder.delivery_method_snapshot)}</Text>
              <Text>Límite: {new Date(selectedOrder.payment_report_deadline_at).toLocaleString()}</Text>
              <div className="business-shell__tabs">
                <Button mode="outline" size="s" disabled={extendingOrderId === selectedOrder.id || selectedOrder.status !== "waiting_payment" || selectedOrder.extension_used} onClick={() => void extendOrder(selectedOrder.id)}>
                  {extendingOrderId === selectedOrder.id ? "Extendiendo..." : "Extender"}
                </Button>
                <Button
                  mode="outline"
                  size="s"
                  disabled={
                    cancellingOrderId === selectedOrder.id
                    || selectedOrder.status !== "waiting_payment"
                  }
                  onClick={() => {
                    setCancelReason("choose_another_business");
                    setCancelPromptOrderId(selectedOrder.id);
                  }}
                >
                  {cancellingOrderId === selectedOrder.id
                    ? "Cancelando..."
                    : "Cancelar y buscar otro negocio"}
                </Button>
                <Button mode="outline" size="s" disabled={openingChatOrderId === selectedOrder.id || !CHAT_STATUSES.includes(selectedOrder.status)} onClick={() => void openOrderChat(selectedOrder.id)}>
                  {openingChatOrderId === selectedOrder.id ? "Abriendo..." : "Chat"}
                </Button>
              </div>
              {cancelPromptOrderId === selectedOrder.id ? (
                <div className="business-grid" aria-label="Confirmar cancelacion">
                  <Text>
                    Cancela solo si no enviaste el pago. Esta orden quedara
                    registrada como cancelada antes de reportar pago.
                  </Text>
                  <label className="business-field">
                    <span>Motivo</span>
                    <select
                      value={cancelReason}
                      disabled={cancellingOrderId === selectedOrder.id}
                      onChange={(event) =>
                        setCancelReason(event.target.value as OrderCancelReason)
                      }
                    >
                      <option value="business_not_responding">
                        El negocio no responde
                      </option>
                      <option value="business_unavailable">
                        El negocio no puede atender
                      </option>
                      <option value="customer_mistake">Me equivoque</option>
                      <option value="choose_another_business">
                        Quiero elegir otro negocio
                      </option>
                    </select>
                  </label>
                  <div className="business-shell__tabs">
                    <Button
                      mode="outline"
                      size="s"
                      disabled={cancellingOrderId === selectedOrder.id}
                      onClick={() => setCancelPromptOrderId(null)}
                    >
                      Volver
                    </Button>
                    <Button
                      mode="filled"
                      size="s"
                      disabled={cancellingOrderId === selectedOrder.id}
                      onClick={() => {
                        void cancelOrder(
                          selectedOrder.id,
                          cancelReason,
                          true
                        ).then((cancelled) => {
                          if (cancelled) {
                            setCancelPromptOrderId(null);
                          }
                        });
                      }}
                    >
                      {cancellingOrderId === selectedOrder.id
                        ? "Cancelando..."
                        : "Confirmar cancelacion"}
                    </Button>
                  </div>
                </div>
              ) : null}
              {selectedOrder.rating?.already_rated ? (
                <div className="business-grid" aria-label="Calificacion enviada">
                  <Text className="business-card__label">Calificacion del negocio</Text>
                  <Text>{selectedOrder.rating.stars} de 5 estrellas</Text>
                </div>
              ) : selectedOrder.rating?.can_rate ? (
                <div className="business-grid" aria-label="Calificar negocio">
                  <Text className="business-card__label">Calificar negocio</Text>
                  <div className="business-shell__tabs" role="group" aria-label="Selecciona de 1 a 5 estrellas">
                    {[1, 2, 3, 4, 5].map((stars) => (
                      <Button
                        key={stars}
                        mode={selectedRatingStars === stars ? "filled" : "outline"}
                        size="s"
                        disabled={submittingRatingOrderId === selectedOrder.id}
                        aria-label={`${stars} estrella${stars === 1 ? "" : "s"}`}
                        onClick={() => setSelectedRatingStars(stars)}
                      >
                        {stars}
                      </Button>
                    ))}
                  </div>
                  <Button
                    mode="filled"
                    stretched
                    disabled={submittingRatingOrderId === selectedOrder.id || selectedRatingStars < 1}
                    onClick={() => void submitOrderRating(selectedOrder.id)}
                  >
                    {submittingRatingOrderId === selectedOrder.id ? "Enviando..." : "Enviar calificacion"}
                  </Button>
                </div>
              ) : null}
              <ClientOperationReportPanel model={model} order={selectedOrder} />
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
            {myOrders.map((order) => {
              const orderCurrency = paymentMethodCurrencyPresentation(
                order.payment_method_snapshot
              );
              return (
                <button className="business-row ad-row" disabled={openingOrderId === order.id} key={order.id} type="button" onClick={() => void openOrderDetail(order.id)}>
                  <span>{order.public_order_code}</span>
                  <span>{openingOrderId === order.id ? "Abriendo..." : clientOrderStatusLabel(order)}</span>
                  <span>{order.amount_usd} {orderCurrency.currencyLabel}</span>
                </button>
              );
            })}
            {myOrdersNextCursor ? (
              <Button mode="outline" size="s" disabled={loadingMoreMyOrders} onClick={() => void loadMoreMyOrders()}>
                {loadingMoreMyOrders ? "Cargando..." : "Cargar mas"}
              </Button>
            ) : null}
          </div>
        </div>
      ) : null}

      {view === "messages" ? (
        <div className="business-card">
          <Text className="business-card__label">Mensajes</Text>
          <button className="business-row ad-row" type="button" onClick={openClientSupport}>
            <span>Soporte NODO</span>
            <span>Ver conversaciones</span>
            <AttentionBadge
              count={attentionCounts.support}
              label="respuestas pendientes"
              truncated={attentionTruncated.support}
            />
          </button>
          <div className="business-list">
            {loadingOrders ? <Text>Cargando conversaciones...</Text> : null}
            {myOrders.length === 0 && !loadingOrders ? <Text>Todavía no tienes conversaciones.</Text> : null}
            {myOrders.map((order) => {
              const canOpenChat = CHAT_STATUSES.includes(order.status);
              return (
                <button className="business-row ad-row" disabled={!canOpenChat || openingChatOrderId === order.id} key={order.id} type="button" onClick={() => void openOrderChat(order.id)}>
                  <span>{order.public_order_code}</span>
                  <span>{openingChatOrderId === order.id ? "Abriendo..." : canOpenChat ? "Abrir chat" : "Sin chat aún"}</span>
                  <span>{clientOrderStatusLabel(order)}</span>
                </button>
              );
            })}
            {myOrdersNextCursor ? (
              <Button mode="outline" size="s" disabled={loadingMoreMyOrders} onClick={() => void loadMoreMyOrders()}>
                {loadingMoreMyOrders ? "Cargando..." : "Cargar mas"}
              </Button>
            ) : null}
          </div>
          <Text className="auth-entry__session-meta">El chat se abre desde que confirmas la negociacion.</Text>
        </div>
      ) : null}
    </>
  );
}
