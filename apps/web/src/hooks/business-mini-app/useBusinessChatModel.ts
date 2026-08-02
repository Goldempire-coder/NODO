import { useCallback, useRef, useState } from "react";
import {
  mutateBusinessOrder as mutateBusinessOrderRequest
} from "../../api/businessOrders";
import {
  listOrderMessages,
  openOrderMessageAttachment,
  sendOrderMessage,
  shareConfiguredZelle as shareConfiguredZelleRequest,
  uploadOrderMessageAttachment
} from "../../api/chat";
import type { AuthenticatedRequest } from "../../api/client";
import { revealOrderReceiverDetails } from "../../api/orders";
import type { BusinessMiniAppView } from "../../constants/businessViews";
import type {
  ChatAttachment,
  ChatAttachmentViewUrl,
  ChatCapabilities,
  ChatMessage,
  ChatThread
} from "../../types/chat";
import type { BusinessSummary } from "../../types/business";
import type { BusinessOrderSummary, ReceiverDetails } from "../../types/orders";
import { getTelegramWebApp } from "../../theme/telegramTheme";
import { useStableIdempotencyKeys } from "../useStableIdempotencyKeys";
import { handleBusinessPinError as routeBusinessPinError, requireUnlockedBusinessPin } from "./businessPinGuards";

type ChatAttachmentLink = {
  url: string;
  downloadFilename: string;
  expiresInSeconds: number;
  mimeType: string;
};

function openTemporaryAttachmentUrl(url: string) {
  try {
    getTelegramWebApp()?.openLink?.(url);
    return;
  } catch {
    // Telegram native link opening is best-effort; the visible fallback remains available.
  }
  window.open(url, "_blank", "noopener,noreferrer");
}

function sortChatMessages(messages: ChatMessage[]) {
  return [...messages].sort((left, right) => {
    const timeDelta = new Date(left.created_at).getTime() - new Date(right.created_at).getTime();
    if (timeDelta !== 0) {
      return timeDelta;
    }
    return left.id.localeCompare(right.id);
  });
}

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
  const [chatOrderId, setChatOrderId] = useState<string | null>(null);
  const [chatOrder, setChatOrder] = useState<BusinessOrderSummary | null>(null);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [chatCapabilities, setChatCapabilities] = useState<ChatCapabilities>({
    can_send_message: false,
    can_open_dispute: false,
    can_share_zelle: false,
    payment_details_shared: false,
    can_report_payment: false,
    receiver_details_shared: false,
    can_share_receiver_details: false,
    can_reveal_receiver_details: false,
    receiver_details_required: false,
    can_confirm_received: false,
    can_confirm_payment: false,
    can_mark_delivered: false
  });
  const [chatBody, setChatBody] = useState("");
  const [chatAttachments, setChatAttachments] = useState<ChatAttachment[]>([]);
  const [refreshingChat, setRefreshingChat] = useState(false);
  const [sendingChatMessage, setSendingChatMessage] = useState(false);
  const [uploadingChatAttachment, setUploadingChatAttachment] = useState(false);
  const [sharingZelle, setSharingZelle] = useState(false);
  const [receiverDetails, setReceiverDetails] = useState<ReceiverDetails | null>(null);
  const [revealingReceiverDetails, setRevealingReceiverDetails] = useState(false);
  const [chatAttachmentLink, setChatAttachmentLink] = useState<ChatAttachmentLink | null>(null);
  const [businessChatAction, setBusinessChatAction] = useState<"confirm-payment" | "mark-delivered" | null>(null);
  const sendingChatMessageRef = useRef(false);
  const uploadingChatAttachmentRef = useRef(false);
  const sharingZelleRef = useRef(false);
  const revealingReceiverDetailsRef = useRef(false);
  const businessChatActionRef = useRef(false);
  const refreshingChatRef = useRef(false);
  const chatOrderIdRef = useRef(chatOrderId);
  chatOrderIdRef.current = chatOrderId;
  const { clearIdempotencyKey, getIdempotencyKey } = useStableIdempotencyKeys();

  const openBusinessChat = useCallback(async (orderId: string) => {
    chatOrderIdRef.current = orderId;
    setBusy(true);
    try {
      const data = await listOrderMessages<ChatThread<BusinessOrderSummary>>(request, orderId, 50);
      setChatOrderId(orderId);
      setChatOrder(data.order);
      syncBusinessOrderFromChat(data.order);
      setChatMessages(sortChatMessages([...data.system_messages, ...data.items]));
      setChatCapabilities(data.capabilities);
      setChatAttachments([]);
      setChatAttachmentLink(null);
      setChatBody("");
      setReceiverDetails(null);
      setView("business-chat");
      setNotice("");
    } catch (error) {
      setChatOrderId(orderId);
      setChatOrder(null);
      setChatMessages([]);
      setChatCapabilities({
        can_send_message: false,
        can_open_dispute: false,
        can_share_zelle: false,
        payment_details_shared: false,
        can_report_payment: false,
        receiver_details_shared: false,
        can_share_receiver_details: false,
        can_reveal_receiver_details: false,
        receiver_details_required: false,
        can_confirm_received: false,
        can_confirm_payment: false,
        can_mark_delivered: false
      });
      setReceiverDetails(null);
      setChatAttachmentLink(null);
      setView("business-chat");
      setNotice(error instanceof Error ? error.message : "No logramos abrir el chat de esta orden.");
    } finally {
      setBusy(false);
    }
  }, [request, setBusy, setNotice, setView, syncBusinessOrderFromChat]);

  const refreshChat = useCallback(async (options?: { silent?: boolean }) => {
    const targetOrderId = chatOrderIdRef.current;
    if (!targetOrderId || refreshingChatRef.current) {
      return false;
    }
    refreshingChatRef.current = true;
    if (!options?.silent) {
      setRefreshingChat(true);
    }
    try {
      const data = await listOrderMessages<ChatThread<BusinessOrderSummary>>(request, targetOrderId, 50);
      if (chatOrderIdRef.current !== targetOrderId) {
        return false;
      }
      syncBusinessOrderFromChat(data.order);
      setChatOrder(data.order);
      setChatMessages(sortChatMessages([...data.system_messages, ...data.items]));
      setChatCapabilities(data.capabilities);
      return true;
    } catch (error) {
      if (!options?.silent) {
        setNotice(error instanceof Error ? error.message : "No pudimos actualizar el chat.");
      }
      return false;
    } finally {
      refreshingChatRef.current = false;
      if (!options?.silent) {
        setRefreshingChat(false);
      }
    }
  }, [request, setNotice, syncBusinessOrderFromChat]);

  const uploadChatAttachment = useCallback(async (file: File | null) => {
    if (!chatOrderId || !file || uploadingChatAttachmentRef.current) {
      return;
    }
    uploadingChatAttachmentRef.current = true;
    setUploadingChatAttachment(true);
    const idempotencyScope = `message_attachment_${chatOrderId}`;
    try {
      const data = await uploadOrderMessageAttachment<{ attachment: ChatAttachment }>(request, chatOrderId, file, getIdempotencyKey(idempotencyScope, { orderId: chatOrderId, name: file.name, size: file.size }));
      clearIdempotencyKey(idempotencyScope);
      setChatAttachments((current) => [...current, data.attachment]);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "No pudimos adjuntar el archivo.");
    } finally {
      uploadingChatAttachmentRef.current = false;
      setUploadingChatAttachment(false);
    }
  }, [chatOrderId, clearIdempotencyKey, getIdempotencyKey, request, setNotice]);

  const sendChatMessage = useCallback(async () => {
    const body = chatBody.trim();
    if (!chatOrderId || sendingChatMessageRef.current || (!body && chatAttachments.length === 0)) {
      return;
    }
    sendingChatMessageRef.current = true;
    setSendingChatMessage(true);
    const idempotencyScope = `message_${chatOrderId}`;
    try {
      await sendOrderMessage(request, chatOrderId, {
        body,
        attachment_ids: chatAttachments.map((attachment) => attachment.id)
      }, getIdempotencyKey(idempotencyScope, { orderId: chatOrderId, body, attachmentIds: chatAttachments.map((attachment) => attachment.id) }));
      clearIdempotencyKey(idempotencyScope);
      setChatBody("");
      setChatAttachments([]);
      await refreshChat({ silent: true });
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "No pudimos enviar el mensaje.");
    } finally {
      sendingChatMessageRef.current = false;
      setSendingChatMessage(false);
    }
  }, [chatAttachments, chatBody, chatOrderId, clearIdempotencyKey, getIdempotencyKey, refreshChat, request, setNotice]);

  const dismissChatAttachmentLink = useCallback(() => {
    setChatAttachmentLink(null);
  }, []);

  const openChatAttachment = useCallback(async (attachmentId: string, mimeType = "application/octet-stream") => {
    const targetOrderId = chatOrderIdRef.current;
    if (!targetOrderId) {
      return;
    }
    try {
      const data = await openOrderMessageAttachment<ChatAttachmentViewUrl>(request, targetOrderId, attachmentId);
      if (chatOrderIdRef.current !== targetOrderId || typeof window === "undefined") {
        return;
      }
      setChatAttachmentLink({
        url: data.url,
        downloadFilename: data.download_filename,
        expiresInSeconds: data.expires_in_seconds,
        mimeType
      });
      openTemporaryAttachmentUrl(data.url);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "No pudimos abrir la imagen.");
    }
  }, [request, setNotice]);

  const shareConfiguredZelle = useCallback(async () => {
    if (!chatOrderId || sharingZelleRef.current || !chatCapabilities.can_share_zelle) {
      return;
    }
    sharingZelleRef.current = true;
    setSharingZelle(true);
    const idempotencyScope = `share_zelle_${chatOrderId}`;
    try {
      await shareConfiguredZelleRequest(
        request,
        chatOrderId,
        getIdempotencyKey(idempotencyScope, { orderId: chatOrderId })
      );
      clearIdempotencyKey(idempotencyScope);
      await refreshChat({ silent: true });
      setNotice("Zelle compartido en el chat.");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "No pudimos compartir el Zelle.");
    } finally {
      sharingZelleRef.current = false;
      setSharingZelle(false);
    }
  }, [
    chatCapabilities.can_share_zelle,
    chatOrderId,
    clearIdempotencyKey,
    getIdempotencyKey,
    refreshChat,
    request,
    setNotice
  ]);

  const revealReceiverDetails = useCallback(async () => {
    if (!chatOrderId || revealingReceiverDetailsRef.current || !chatCapabilities.can_reveal_receiver_details) {
      return;
    }
    revealingReceiverDetailsRef.current = true;
    setRevealingReceiverDetails(true);
    try {
      const data = await revealOrderReceiverDetails<ReceiverDetails>(
        request,
        chatOrderId
      );
      if (chatOrderIdRef.current !== chatOrderId) {
        return;
      }
      setReceiverDetails(data);
      setNotice("Pago Movil revelado para esta orden.");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "No pudimos revelar el Pago Movil.");
    } finally {
      revealingReceiverDetailsRef.current = false;
      setRevealingReceiverDetails(false);
    }
  }, [chatCapabilities.can_reveal_receiver_details, chatOrderId, request, setNotice]);

  const mutateBusinessChatOrder = useCallback(async (action: "confirm-payment" | "mark-delivered") => {
    const targetOrderId = chatOrderIdRef.current;
    if (!targetOrderId || businessChatActionRef.current) {
      return;
    }
    const actionLabel = action === "confirm-payment" ? "confirmar Zelle recibido" : "marcar Pago Movil enviado";
    if (!requireUnlockedBusinessPin({ action: actionLabel, business, setNotice, setView })) {
      return;
    }
    if (action === "confirm-payment" && !chatCapabilities.can_confirm_payment) {
      return;
    }
    if (action === "mark-delivered" && !chatCapabilities.can_mark_delivered) {
      return;
    }
    businessChatActionRef.current = true;
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
      if (chatOrderIdRef.current === targetOrderId) {
        setChatOrder(mutation.order);
        syncBusinessOrderFromChat(mutation.order);
      }
      try {
        const data = await listOrderMessages<ChatThread<BusinessOrderSummary>>(request, targetOrderId, 50);
        if (chatOrderIdRef.current !== targetOrderId) {
          return;
        }
        setChatOrder(data.order);
        syncBusinessOrderFromChat(data.order);
        setChatMessages(sortChatMessages([...data.system_messages, ...data.items]));
        setChatCapabilities(data.capabilities);
        setNotice("");
      } catch {
        if (chatOrderIdRef.current === targetOrderId) {
          setNotice("No pudimos actualizar toda la conversacion, pero la accion fue aplicada. Toca Actualizar.");
        }
      }
    } catch (error) {
      if (routeBusinessPinError({ action: actionLabel, error, setNotice, setView })) {
        return;
      }
      setNotice(error instanceof Error ? error.message : "No pudimos operar la orden.");
    } finally {
      businessChatActionRef.current = false;
      setBusinessChatAction(null);
    }
  }, [
    business?.access_link,
    chatCapabilities.can_confirm_payment,
    chatCapabilities.can_mark_delivered,
    clearIdempotencyKey,
    getIdempotencyKey,
    request,
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
    businessChatAction,
    chatAttachments,
    chatBody,
    chatCapabilities,
    chatAttachmentLink,
    chatMessages,
    chatOrder,
    chatOrderId,
    dismissChatAttachmentLink,
    openBusinessChat,
    openChatAttachment,
    refreshChat,
    refreshingChat,
    receiverDetails,
    revealReceiverDetails,
    revealingReceiverDetails,
    confirmBusinessPaymentInChat,
    markBusinessDeliveredInChat,
    sendChatMessage,
    sendingChatMessage,
    shareConfiguredZelle,
    sharingZelle,
    setChatBody,
    uploadingChatAttachment,
    uploadChatAttachment
  };
}
