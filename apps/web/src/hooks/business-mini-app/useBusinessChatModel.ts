import { useCallback, useMemo } from "react";
import type { AuthenticatedRequest } from "../../api/client";
import type { BusinessMiniAppView } from "../../constants/businessViews";
import type { BusinessSummary } from "../../types/business";
import type { BusinessOrderSummary } from "../../types/orders";
import { useBusinessChatAttachments } from "./chat/useBusinessChatAttachments";
import { useBusinessChatComposer } from "./chat/useBusinessChatComposer";
import { useBusinessChatOrderActions } from "./chat/useBusinessChatOrderActions";
import { useBusinessChatSession } from "./chat/useBusinessChatSession";
import { useBusinessPaymentShareActions } from "./chat/useBusinessPaymentShareActions";

export function useBusinessChatModel({
  business,
  request,
  syncBusinessOrderFromChat,
  setBusy,
  setNotice,
  setView
}: {
  business: BusinessSummary | null;
  request: AuthenticatedRequest;
  syncBusinessOrderFromChat: (order: BusinessOrderSummary) => void;
  setBusy: (busy: boolean) => void;
  setNotice: (notice: string) => void;
  setView: (view: BusinessMiniAppView) => void;
}) {
  const session = useBusinessChatSession({
    request,
    syncBusinessOrderFromChat,
    setBusy,
    setNotice,
    setView
  });
  const attachments = useBusinessChatAttachments({
    request,
    session: session.scope,
    setNotice
  });
  const composer = useBusinessChatComposer({
    request,
    session: session.scope,
    getChatAttachments: attachments.getChatAttachments,
    clearSubmittedChatAttachments: attachments.clearSubmittedChatAttachments,
    setNotice
  });
  const paymentShare = useBusinessPaymentShareActions({
    request,
    session: session.scope,
    chatCapabilities: session.chatCapabilities,
    setNotice
  });
  const orderActionSession = useMemo(() => ({
    ...session.scope,
    reloadChatSession: session.reloadChatSession,
    setCurrentChatOrder: session.setCurrentChatOrder
  }), [session.reloadChatSession, session.scope, session.setCurrentChatOrder]);
  const orderActions = useBusinessChatOrderActions({
    business,
    request,
    session: orderActionSession,
    chatCapabilities: session.chatCapabilities,
    syncBusinessOrderFromChat,
    setNotice,
    setView
  });

  const openBusinessChat = useCallback(async (orderId: string) => {
    attachments.activateOrder(orderId);
    composer.activateOrder(orderId);
    paymentShare.activateOrder(orderId);
    orderActions.activateOrder(orderId);
    return session.openBusinessChat(orderId);
  }, [
    attachments.activateOrder,
    composer.activateOrder,
    orderActions.activateOrder,
    paymentShare.activateOrder,
    session.openBusinessChat
  ]);

  return {
    businessChatAction: orderActions.businessChatAction,
    chatAttachments: attachments.chatAttachments,
    chatBody: composer.chatBody,
    chatCapabilities: session.chatCapabilities,
    chatAttachmentLink: attachments.chatAttachmentLink,
    chatMessages: session.chatMessages,
    chatOrder: session.chatOrder,
    chatOrderId: session.chatOrderId,
    chatRefreshError: session.chatRefreshError,
    dismissChatAttachmentLink: attachments.dismissChatAttachmentLink,
    openBusinessChat,
    openChatAttachment: attachments.openChatAttachment,
    refreshChat: session.refreshChat,
    refreshingChat: session.refreshingChat,
    receiverDetails: paymentShare.receiverDetails,
    revealReceiverDetails: paymentShare.revealReceiverDetails,
    revealingReceiverDetails: paymentShare.revealingReceiverDetails,
    confirmBusinessPaymentInChat: orderActions.confirmBusinessPaymentInChat,
    markBusinessDeliveredInChat: orderActions.markBusinessDeliveredInChat,
    sendChatMessage: composer.sendChatMessage,
    sendingChatMessage: composer.sendingChatMessage,
    shareConfiguredPaymentDetails: paymentShare.shareConfiguredPaymentDetails,
    sharingPaymentDetails: paymentShare.sharingPaymentDetails,
    setChatBody: composer.setChatBody,
    uploadingChatAttachment: attachments.uploadingChatAttachment,
    uploadChatAttachment: attachments.uploadChatAttachment
  };
}
