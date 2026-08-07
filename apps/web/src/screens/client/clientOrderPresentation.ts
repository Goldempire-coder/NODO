import type { OrderSummary } from "../../types/orders";

export function clientOrderStatusLabel(
  order: Pick<OrderSummary, "status" | "terminal_display_status">
): string {
  if (order.terminal_display_status === "payment_rejected_admin_review") {
    return "Pago rechazado";
  }
  return order.status;
}
