import { Button, Text } from "@telegram-apps/telegram-ui";
import { useState } from "react";
import { paymentMethodCurrencyPresentation } from "../../constants/paymentLabels";
import type { OrderSummary } from "../../types/orders";
import type { OperationReportCategory } from "../../types/support";
import { formatClientMethodLine } from "./clientMethodCopy";
import type { RemitterScreensModel } from "./RemitterScreens.types";
import { clientOrderStatusLabel } from "./clientOrderPresentation";

export const REPORTABLE_OPERATION_STATUSES = new Set([
  "payment_confirmed",
  "delivered",
  "completed",
  "payment_rejected",
  "disputed",
  "cancelled"
]);

export function ClientOperationReportPanel({
  model,
  order
}: {
  model: RemitterScreensModel;
  order: OrderSummary;
}) {
  const [showForm, setShowForm] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [category, setCategory] = useState<OperationReportCategory>("order_help");
  const [message, setMessage] = useState("");
  const creating = model.creatingOperationReportOrderId === order.id;
  const error = model.operationReportError?.orderId === order.id
    ? model.operationReportError.message
    : null;
  const submitted = model.operationReportSuccessOrderId === order.id;
  const currency = paymentMethodCurrencyPresentation(order.payment_method_snapshot);

  if (!REPORTABLE_OPERATION_STATUSES.has(order.status)) {
    return null;
  }

  if (submitted) {
    return (
      <div className="business-grid" role="status">
        <Text className="business-card__label">Reporte recibido</Text>
        <Text>Soporte NODO revisara la orden.</Text>
      </div>
    );
  }

  if (!showForm) {
    return (
      <Button mode="outline" size="s" onClick={() => setShowForm(true)}>
        Reportar orden
      </Button>
    );
  }

  return (
    <div className="business-grid" aria-label="Reportar orden">
      <Text className="business-card__label">Reportar orden</Text>
      <Text>{order.public_order_code} · {order.amount_usd} {currency.currencyLabel}</Text>
      <Text>{formatClientMethodLine(order.payment_method_snapshot, order.delivery_method_snapshot)} · {clientOrderStatusLabel(order)}</Text>
      <label className="business-field">
        <span>Motivo</span>
        <select
          disabled={creating || confirming}
          value={category}
          onChange={(event) => setCategory(event.target.value as OperationReportCategory)}
        >
          <option value="order_help">Ayuda con la orden</option>
          <option value="payment_report_help">Revision del reporte de pago</option>
          <option value="suspicious_activity">Actividad inusual</option>
          <option value="other">Otro</option>
        </select>
      </label>
      <label className="business-field">
        <span>Describe brevemente lo ocurrido</span>
        <textarea
          disabled={creating}
          maxLength={1000}
          rows={3}
          value={message}
          onChange={(event) => setMessage(event.target.value)}
        />
      </label>
      {error ? <Text role="alert">{error}</Text> : null}
      {confirming ? (
        <div className="business-grid" aria-label="Confirmar reporte de orden">
          <Text>Confirma el reporte para {order.public_order_code}. Soporte revisara la informacion sin cambiar automaticamente la orden o el pago.</Text>
          <div className="business-shell__tabs">
            <Button mode="outline" size="s" disabled={creating} onClick={() => setConfirming(false)}>
              Volver
            </Button>
            <Button
              mode="filled"
              size="s"
              disabled={creating}
              onClick={() => void model.submitOperationReport(order.id, { category, message })}
            >
              {creating ? "Enviando..." : "Confirmar envio"}
            </Button>
          </div>
        </div>
      ) : (
        <div className="business-shell__tabs">
          <Button mode="outline" size="s" disabled={creating} onClick={() => setShowForm(false)}>
            Cancelar
          </Button>
          <Button mode="filled" size="s" disabled={creating || message.trim().length < 3} onClick={() => setConfirming(true)}>
            Revisar reporte
          </Button>
        </div>
      )}
    </div>
  );
}
