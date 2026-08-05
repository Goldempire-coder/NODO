"use client";

import { useEffect, useRef } from "react";
import type { ClientView } from "../../constants/clientViews";

const CLIENT_ORDER_CHAT_REFRESH_MS = 5000;

type ClientOrderChatSyncInput = {
  canReportPayment: boolean;
  chatOrderId: string | null;
  hasPaymentInstructions: boolean;
  sendingChatMessage: boolean;
  uploadingChatAttachment: boolean;
  view: ClientView;
  openPaymentReport: (orderId: string) => void | Promise<boolean>;
  refreshChat: (options?: { silent?: boolean }) => void | Promise<boolean>;
};

/** Coordinates chat-only network effects. Backend capabilities remain the authority. */
export function useClientOrderChatSync({
  canReportPayment,
  chatOrderId,
  hasPaymentInstructions,
  openPaymentReport,
  refreshChat,
  sendingChatMessage,
  uploadingChatAttachment,
  view
}: ClientOrderChatSyncInput) {
  const paymentInstructionsRequestedForRef = useRef<string | null>(null);

  useEffect(() => {
    if (!chatOrderId || view !== "order-chat") {
      return;
    }
    const interval = window.setInterval(() => {
      if (
        document.visibilityState !== "visible"
        || sendingChatMessage
        || uploadingChatAttachment
      ) {
        return;
      }
      void refreshChat({ silent: true });
    }, CLIENT_ORDER_CHAT_REFRESH_MS);
    return () => window.clearInterval(interval);
  }, [chatOrderId, refreshChat, sendingChatMessage, uploadingChatAttachment, view]);

  useEffect(() => {
    if (!chatOrderId || !canReportPayment || hasPaymentInstructions) {
      return;
    }
    if (paymentInstructionsRequestedForRef.current === chatOrderId) {
      return;
    }
    paymentInstructionsRequestedForRef.current = chatOrderId;
    void openPaymentReport(chatOrderId);
  }, [canReportPayment, chatOrderId, hasPaymentInstructions, openPaymentReport]);
}
