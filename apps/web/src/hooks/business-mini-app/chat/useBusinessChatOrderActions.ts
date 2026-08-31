import { useCallback, useRef, useState } from "react";
import { mutateBusinessOrder as mutateBusinessOrderRequest } from "../../../api/businessOrders";
import type { AuthenticatedRequest } from "../../../api/client";
import type { BusinessMiniAppView } from "../../../constants/businessViews";
import type { ChatCapabilities } from "../../../types/chat";
import type { BusinessSummary } from "../../../types/business";
import type { BusinessOrderSummary } from "../../../types/orders";
import { useStableIdempotencyKeys } from "../../useStableIdempotencyKeys";
import {
  handleBusinessPinError as routeBusinessPinError,
  requireUnlockedBusinessPin
} from "../businessPinGuards";
import type {
  BusinessChatAction,
  BusinessChatSessionScope
} from "./businessChatShared";

export function useBusinessChatOrderActions({
  business,
  request,
  session,
  chatCapabilities,
  syncBusinessOrderFromChat,
  setNotice,
  setView
}: {
  business: BusinessSummary | null;
  request: AuthenticatedRequest;
  session: BusinessChatSessionScope & {
    reloadChatSession: (orderId: string, sessionEpoch: number) => Promise<boolean>;
    setCurrentChatOrder: (
      orderId: string,
      sessionEpoch: number,
      order: BusinessOrderSummary
    ) => boolean;
  };
  chatCapabilities: ChatCapabilities;
  syncBusinessOrderFromChat: (order: BusinessOrderSummary) => void;
  setNotice: (notice: string) => void;
  setView: (view: BusinessMiniAppView) => void;
}) {
  const [businessChatAction, setBusinessChatAction] = useState<BusinessChatAction | null>(null);
  const businessChatActionRef = useRef(new Map<string, BusinessChatAction>());
  const { clearIdempotencyKey, getIdempotencyKey } = useStableIdempotencyKeys();

  const activateOrder = useCallback((orderId: string) => {
    setBusinessChatAction(businessChatActionRef.current.get(orderId) ?? null);
  }, []);

  const mutateBusinessChatOrder = useCallback(async (action: BusinessChatAction) => {
    const targetOrderId = session.chatOrderIdRef.current;
    const targetSessionEpoch = session.chatSessionEpochRef.current;
    if (
      !targetOrderId
      || businessChatActionRef.current.has(targetOrderId)
      || session.chatCapabilitiesOrderIdRef.current !== targetOrderId
    ) {
      return;
    }
    const actionLabel = action === "confirm-payment"
      ? "confirmar Zelle recibido"
      : "marcar Pago Movil enviado";
    if (
      (action === "confirm-payment" || action === "mark-delivered")
      && !requireUnlockedBusinessPin({ action: actionLabel, business, setNotice, setView })
    ) {
      return;
    }
    if (action === "confirm-payment" && !chatCapabilities.can_confirm_payment) {
      return;
    }
    if (action === "mark-delivered" && !chatCapabilities.can_mark_delivered) {
      return;
    }
    businessChatActionRef.current.set(targetOrderId, action);
    setBusinessChatAction(action);
    const idempotencyScope = `business_chat_${action}_${targetOrderId}`;
    try {
      const mutation = await mutateBusinessOrderRequest<{ order: BusinessOrderSummary }>(
        request,
        targetOrderId,
        action,
        undefined,
        getIdempotencyKey(idempotencyScope, { orderId: targetOrderId, action })
      );
      clearIdempotencyKey(idempotencyScope);
      syncBusinessOrderFromChat(mutation.order);
      session.setCurrentChatOrder(targetOrderId, targetSessionEpoch, mutation.order);
      if (!session.isCurrentChatSession(targetOrderId, targetSessionEpoch)) {
        return;
      }
      try {
        const refreshed = await session.reloadChatSession(targetOrderId, targetSessionEpoch);
        if (refreshed && session.isCurrentChatSession(targetOrderId, targetSessionEpoch)) {
          setNotice("");
        }
      } catch {
        if (session.isCurrentChatSession(targetOrderId, targetSessionEpoch)) {
          setNotice("No pudimos actualizar toda la conversacion, pero la accion fue aplicada. Toca Actualizar.");
        }
      }
    } catch (error) {
      if (!session.isCurrentChatSession(targetOrderId, targetSessionEpoch)) {
        return;
      }
      if (
        (action === "confirm-payment" || action === "mark-delivered")
        && routeBusinessPinError({ action: actionLabel, error, setNotice, setView })
      ) {
        return;
      }
      setNotice(error instanceof Error ? error.message : "No pudimos operar la orden.");
    } finally {
      businessChatActionRef.current.delete(targetOrderId);
      if (session.chatOrderIdRef.current === targetOrderId) {
        setBusinessChatAction(null);
      }
    }
  }, [
    business?.access_link,
    chatCapabilities.can_confirm_payment,
    chatCapabilities.can_mark_delivered,
    clearIdempotencyKey,
    getIdempotencyKey,
    request,
    session,
    setNotice,
    setView,
    syncBusinessOrderFromChat
  ]);

  const confirmBusinessPaymentInChat = useCallback(async () => {
    await mutateBusinessChatOrder("confirm-payment");
  }, [mutateBusinessChatOrder]);

  const markBusinessDeliveredInChat = useCallback(async () => {
    await mutateBusinessChatOrder("mark-delivered");
  }, [mutateBusinessChatOrder]);

  return {
    activateOrder,
    businessChatAction,
    confirmBusinessPaymentInChat,
    markBusinessDeliveredInChat
  };
}
