import { useEffect } from "react";

const BUSINESS_ORDER_CHAT_REFRESH_MS = 5000;

export function useBusinessChatPolling({
  chatOrderId,
  isChatView,
  sendingChatMessage,
  uploadingChatAttachment,
  refreshChat
}: {
  chatOrderId: string | null;
  isChatView: boolean;
  sendingChatMessage: boolean;
  uploadingChatAttachment: boolean;
  refreshChat: (options?: { silent?: boolean }) => Promise<boolean>;
}) {
  useEffect(() => {
    if (!chatOrderId || !isChatView) {
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
    }, BUSINESS_ORDER_CHAT_REFRESH_MS);
    return () => window.clearInterval(interval);
  }, [chatOrderId, isChatView, refreshChat, sendingChatMessage, uploadingChatAttachment]);
}
