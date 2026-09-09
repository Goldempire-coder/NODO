import type { BusinessChatAction } from "../../../hooks/business-mini-app/chat/businessChatShared";
import type { BusinessOrderSummary } from "../../../types/orders";

export function BusinessChatActionDock({
  currentOrder,
  canSharePaymentDetails,
  canConfirmPayment,
  canMarkDelivered,
  businessChatAction,
  sharingPaymentDetails,
  shareConfiguredPaymentDetails,
  confirmBusinessPaymentInChat,
  markBusinessDeliveredInChat
}: {
  currentOrder: BusinessOrderSummary | null;
  canSharePaymentDetails: boolean;
  canConfirmPayment: boolean;
  canMarkDelivered: boolean;
  businessChatAction: BusinessChatAction | null;
  sharingPaymentDetails: boolean;
  shareConfiguredPaymentDetails: () => Promise<void>;
  confirmBusinessPaymentInChat: () => Promise<void>;
  markBusinessDeliveredInChat: () => Promise<void>;
}) {
  if (!canSharePaymentDetails && !canConfirmPayment && !canMarkDelivered) {
    return null;
  }

  return (
    <div className="business-order-chat-action-dock" aria-label="Acciones de la orden">
      {canSharePaymentDetails ? (
        <button
          className="business-order-chat-payment-action"
          type="button"
          disabled={sharingPaymentDetails}
          onClick={() => void shareConfiguredPaymentDetails()}
        >
          {sharingPaymentDetails
            ? "Compartiendo..."
            : currentOrder?.payment_method_snapshot === "usdt_trc20"
              ? "Compartir wallet"
              : "Compartir datos de pago"}
        </button>
      ) : null}
      {canConfirmPayment ? (
        <button
          className="business-order-chat-payment-action"
          type="button"
          disabled={businessChatAction === "confirm-payment"}
          onClick={() => void confirmBusinessPaymentInChat()}
        >
          {businessChatAction === "confirm-payment" ? "Verificando..." : "Verificar ingreso"}
        </button>
      ) : null}
      {canMarkDelivered ? (
        <button
          className="business-order-chat-payment-action"
          type="button"
          disabled={businessChatAction === "mark-delivered"}
          onClick={() => void markBusinessDeliveredInChat()}
        >
          {businessChatAction === "mark-delivered" ? "Marcando..." : "Marcar entrega realizada"}
        </button>
      ) : null}
    </div>
  );
}
