"use client";

import { useCallback, useRef, useState } from "react";
import {
  listOrderMessages,
  openOrderDispute as openOrderDisputeRequest,
  openOrderMessageAttachment,
  sendOrderMessage,
  uploadOrderMessageAttachment
} from "../../api/chat";
import type { AuthenticatedRequest } from "../../api/client";
import { confirmOrderReceived as confirmOrderReceivedRequest, shareOrderReceiverDetails } from "../../api/orders";
import type { ChatAttachmentViewUrl, ChatMessage, ChatThread } from "../../types/chat";
import type { OrderSummary, ReceiverDetailsInput, ReceiverDetailsMasked } from "../../types/orders";
import { getTelegramWebApp } from "../../theme/telegramTheme";
import { actionStartedAt, recordActionCompleted, recordActionFailed, recordActionStarted } from "../actionTelemetry";
import { useStableIdempotencyKeys } from "../useStableIdempotencyKeys";
import type { ClientWorkspaceState } from "./useClientWorkspaceState";

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

export function useClientChatDisputesModel(state: ClientWorkspaceState & { request: AuthenticatedRequest }) {
  const {
    request,
    chatOrderId,
    chatBody,
    chatAttachments,
    disputeReason,
    setChatOrderId,
    setChatMessages,
    setChatCapabilities,
    setChatAttachments,
    setChatBody,
    setNotice,
    setSelectedOrder,
    setOpeningChatOrderId,
    setOpeningOrderDispute,
    setRefreshingChat,
    setSendingChatMessage,
    setUploadingChatAttachment,
    setView
  } = state;
  const { clearIdempotencyKey, getIdempotencyKey } = useStableIdempotencyKeys();
  const sendingChatMessageRef = useRef(false);
  const uploadingChatAttachmentRef = useRef(false);
  const openingOrderDisputeRef = useRef(false);
  const sharingReceiverDetailsRef = useRef(false);
  const confirmingOrderReceivedRef = useRef(false);
  const refreshingChatRef = useRef(false);
  const chatOrderIdRef = useRef(chatOrderId);
  chatOrderIdRef.current = chatOrderId;
  const [receiverDetailsForm, setReceiverDetailsForm] = useState<ReceiverDetailsInput>({
    bank: "0102",
    phone: "",
    document: "",
    holder: ""
  });
  const [receiverDetailsMasked, setReceiverDetailsMasked] = useState<ReceiverDetailsMasked | null>(null);
  const [sharingReceiverDetails, setSharingReceiverDetails] = useState(false);
  const [confirmingOrderReceived, setConfirmingOrderReceived] = useState(false);
  const [chatAttachmentLink, setChatAttachmentLink] = useState<ChatAttachmentLink | null>(null);

  async function openOrderChat(orderId: string) {
    const startedAt = actionStartedAt();
    recordActionStarted("client_chat_open", "order-chat");
    setOpeningChatOrderId(orderId);
    try {
      const data = await listOrderMessages<ChatThread<OrderSummary>>(request, orderId);
      setChatOrderId(orderId);
      setSelectedOrder(data.order);
      setChatMessages(sortChatMessages([...data.system_messages, ...data.items]));
      setChatCapabilities(data.capabilities);
      setChatAttachments([]);
      setChatBody("");
      setReceiverDetailsMasked(null);
      setChatAttachmentLink(null);
      setView("order-chat");
      setNotice("");
      recordActionCompleted("client_chat_open", "order-chat", startedAt);
    } catch (error) {
      setChatOrderId(orderId);
      setChatMessages([]);
      setReceiverDetailsMasked(null);
      setChatAttachmentLink(null);
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
      setView("order-chat");
      setNotice(error instanceof Error ? error.message : "No logramos abrir el chat de esta orden.");
      recordActionFailed("client_chat_open", "order-chat", startedAt, error instanceof Error ? error.name : undefined);
    } finally {
      setOpeningChatOrderId(null);
    }
  }

  const refreshChat = useCallback(async (options?: { silent?: boolean }) => {
    const targetOrderId = chatOrderIdRef.current;
    if (!targetOrderId || refreshingChatRef.current) {
      return false;
    }
    refreshingChatRef.current = true;
    const startedAt = actionStartedAt();
    recordActionStarted("client_chat_refresh", "order-chat");
    if (!options?.silent) {
      setRefreshingChat(true);
    }
    try {
      const data = await listOrderMessages<ChatThread<OrderSummary>>(request, targetOrderId);
      if (chatOrderIdRef.current !== targetOrderId) {
        return false;
      }
      setSelectedOrder(data.order);
      setChatMessages(sortChatMessages([...data.system_messages, ...data.items]));
      setChatCapabilities(data.capabilities);
      recordActionCompleted("client_chat_refresh", "order-chat", startedAt);
      return true;
    } catch (error) {
      if (!options?.silent) {
        setNotice(error instanceof Error ? error.message : "No pudimos actualizar el chat.");
      }
      recordActionFailed("client_chat_refresh", "order-chat", startedAt, error instanceof Error ? error.name : undefined);
      return false;
    } finally {
      refreshingChatRef.current = false;
      if (!options?.silent) {
        setRefreshingChat(false);
      }
    }
  }, [request, setChatCapabilities, setChatMessages, setNotice, setRefreshingChat]);

  async function uploadChatAttachment(file: File | null) {
    if (uploadingChatAttachmentRef.current || !chatOrderId || !file) {
      return;
    }
    uploadingChatAttachmentRef.current = true;
    const startedAt = actionStartedAt();
    recordActionStarted("client_chat_attachment_upload", "order-chat");
    setUploadingChatAttachment(true);
    const idempotencyScope = `message_attachment_${chatOrderId}`;
    try {
      const data = await uploadOrderMessageAttachment<any>(request, chatOrderId, file, getIdempotencyKey(idempotencyScope, { orderId: chatOrderId, name: file.name, size: file.size }));
      clearIdempotencyKey(idempotencyScope);
      setChatAttachments((current) => [...current, data.attachment]);
      recordActionCompleted("client_chat_attachment_upload", "order-chat", startedAt);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "No pudimos adjuntar el archivo.");
      recordActionFailed("client_chat_attachment_upload", "order-chat", startedAt, error instanceof Error ? error.name : undefined);
    } finally {
      uploadingChatAttachmentRef.current = false;
      setUploadingChatAttachment(false);
    }
  }

  async function sendChatMessage() {
    if (sendingChatMessageRef.current || !chatOrderId) {
      return;
    }
    const body = chatBody.trim();
    if (!body && chatAttachments.length === 0) {
      return;
    }
    sendingChatMessageRef.current = true;
    const startedAt = actionStartedAt();
    recordActionStarted("client_chat_message_send", "order-chat");
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
      recordActionCompleted("client_chat_message_send", "order-chat", startedAt);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "No pudimos enviar el mensaje.");
      recordActionFailed("client_chat_message_send", "order-chat", startedAt, error instanceof Error ? error.name : undefined);
    } finally {
      sendingChatMessageRef.current = false;
      setSendingChatMessage(false);
    }
  }

  function dismissChatAttachmentLink() {
    setChatAttachmentLink(null);
  }

  async function openChatAttachment(attachmentId: string, mimeType = "application/octet-stream") {
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
  }

  async function openOrderDispute() {
    if (openingOrderDisputeRef.current || !chatOrderId) {
      return;
    }
    openingOrderDisputeRef.current = true;
    const startedAt = actionStartedAt();
    recordActionStarted("client_order_dispute_open", "order-chat");
    setOpeningOrderDispute(true);
    const idempotencyScope = `dispute_${chatOrderId}`;
    try {
      await openOrderDisputeRequest(request, chatOrderId, {
        reason: disputeReason,
        description: chatBody.trim() || undefined,
        evidence_file_ids: []
      }, getIdempotencyKey(idempotencyScope, { orderId: chatOrderId, disputeReason, description: chatBody.trim() || undefined }));
      clearIdempotencyKey(idempotencyScope);
      await refreshChat({ silent: true });
      setNotice("Disputa abierta. La resolucion admin queda para contrato futuro.");
      recordActionCompleted("client_order_dispute_open", "order-chat", startedAt);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "No pudimos abrir la disputa.");
      recordActionFailed("client_order_dispute_open", "order-chat", startedAt, error instanceof Error ? error.name : undefined);
    } finally {
      openingOrderDisputeRef.current = false;
      setOpeningOrderDispute(false);
    }
  }

  async function shareReceiverDetails() {
    if (sharingReceiverDetailsRef.current || !chatOrderId) {
      return;
    }
    sharingReceiverDetailsRef.current = true;
    setSharingReceiverDetails(true);
    const scope = `receiver_details_${chatOrderId}`;
    try {
      const data = await shareOrderReceiverDetails<{
        receiver_details_masked: ReceiverDetailsMasked;
      }>(
        request,
        chatOrderId,
        receiverDetailsForm,
        getIdempotencyKey(scope, { orderId: chatOrderId, ...receiverDetailsForm })
      );
      clearIdempotencyKey(scope);
      setReceiverDetailsMasked(data.receiver_details_masked);
      await refreshChat({ silent: true });
      setNotice("Pago Movil compartido de forma segura.");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "No pudimos compartir el Pago Movil.");
    } finally {
      sharingReceiverDetailsRef.current = false;
      setSharingReceiverDetails(false);
    }
  }

  async function confirmOrderReceived() {
    if (confirmingOrderReceivedRef.current || !chatOrderId) {
      return;
    }
    confirmingOrderReceivedRef.current = true;
    setConfirmingOrderReceived(true);
    const scope = `confirm_received_${chatOrderId}`;
    try {
      const data = await confirmOrderReceivedRequest<{ order: OrderSummary }>(
        request,
        chatOrderId,
        getIdempotencyKey(scope, { orderId: chatOrderId, action: "manual_confirmed" })
      );
      clearIdempotencyKey(scope);
      setSelectedOrder(data.order);
      await refreshChat({ silent: true });
      setNotice("Recepcion confirmada. La orden quedo completada.");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "No pudimos confirmar la recepcion.");
    } finally {
      confirmingOrderReceivedRef.current = false;
      setConfirmingOrderReceived(false);
    }
  }

  return {
    openOrderChat,
    refreshChat,
    uploadChatAttachment,
    chatAttachmentLink,
    dismissChatAttachmentLink,
    openChatAttachment,
    sendChatMessage,
    openOrderDispute,
    receiverDetailsForm,
    setReceiverDetailsForm,
    receiverDetailsMasked,
    sharingReceiverDetails,
    shareReceiverDetails,
    confirmingOrderReceived,
    confirmOrderReceived
  };
}
