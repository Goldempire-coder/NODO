import {
  formatDeliveryCurrency,
  formatDeliveryMethod,
  formatPaymentMethod
} from "../../constants/paymentLabels";

export function formatClientMethodLine(paymentMethod: unknown, deliveryMethod: unknown): string {
  const currency = formatDeliveryCurrency(deliveryMethod);
  const parts = [
    `Metodo publicado por el negocio: ${formatPaymentMethod(paymentMethod)}`,
    `Entrega declarada: ${formatDeliveryMethod(deliveryMethod)}`,
    currency ? `Referencia: ${currency}` : null
  ].filter(Boolean);
  return parts.join(" - ");
}
