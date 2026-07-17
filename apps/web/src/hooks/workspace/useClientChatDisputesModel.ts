"use client";

import { listOrderMessages, openOrderDispute as openOrderDisputeRequest, sendOrderMessage, uploadOrderMessageAttachment } from "../../api/chat";
import type { AuthenticatedRequest } from "../../api/client";
import { CHAT_DISPUTE_COPY } from "../../constants/copy";
import { actionStartedAt, recordActionCompleted, recordActionFailed, recordActionStarted } from "../actionTelemetry";
import type { ClientWorkspaceState } from "./useClientWorkspaceState";

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
    setOpeningChatOrderId,
    setOpeningOrderDispute,
    setRefreshingChat,
    setSendingChatMessage,
    setUploadingChatAttachment,
    setView
  } = state;

  async function openOrderChat(orderId: string) {
    const startedAt = actionStartedAt();
    recordActionStarted("client_chat_open", "order-chat");
    setOpeningChatOrderId(orderId);
    try {
      const data = await listOrderMessages<any>(request, orderId);
      setChatOrderId(orderId);
      setChatMessages(data.items);
      setChatCapabilities(data.capabilities);
      setChatAttachments([]);
      setChatBody("");
      setView("order-chat");
      setNotice(data.disclaimer || CHAT_DISPUTE_COPY);
      recordActionCompleted("client_chat_open", "order-chat", startedAt);
    } catch (error) {
      setChatOrderId(orderId);
      setChatMessages([]);
      setChatCapabilities({ can_send_message: false, can_open_dispute: false });
      setView("order-chat");
      setNotice(error instanceof Error ? error.message : "No logramos abrir el chat de esta orden.");
      recordActionFailed("client_chat_open", "order-chat", startedAt, error instanceof Error ? error.name : undefined);
    } finally {
      setOpeningChatOrderId(null);
    }
  }

  async function refreshChat() {
    if (!chatOrderId) {
      return;
    }
    const startedAt = actionStartedAt();
    recordActionStarted("client_chat_refresh", "order-chat");
    setRefreshingChat(true);
    try {
      const data = await listOrderMessages<any>(request, chatOrderId);
      setChatMessages(data.items);
      setChatCapabilities(data.capabilities);
      setNotice(data.disclaimer || CHAT_DISPUTE_COPY);
      recordActionCompleted("client_chat_refresh", "order-chat", startedAt);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "No pudimos actualizar el chat.");
      recordActionFailed("client_chat_refresh", "order-chat", startedAt, error instanceof Error ? error.name : undefined);
    } finally {
      setRefreshingChat(false);
    }
  }

  async function uploadChatAttachment(file: File | null) {
    if (!chatOrderId || !file) {
      return;
    }
    const startedAt = actionStartedAt();
    recordActionStarted("client_chat_attachment_upload", "order-chat");
    setUploadingChatAttachment(true);
    try {
      const data = await uploadOrderMessageAttachment<any>(request, chatOrderId, file, `message_attachment_${chatOrderId}_${Date.now()}`);
      setChatAttachments((current) => [...current, data.attachment]);
      setNotice("Archivo privado agregado al mensaje. No se muestra ruta interna.");
      recordActionCompleted("client_chat_attachment_upload", "order-chat", startedAt);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "No pudimos adjuntar el archivo.");
      recordActionFailed("client_chat_attachment_upload", "order-chat", startedAt, error instanceof Error ? error.name : undefined);
    } finally {
      setUploadingChatAttachment(false);
    }
  }

  async function sendChatMessage() {
    if (!chatOrderId) {
      return;
    }
    const startedAt = actionStartedAt();
    recordActionStarted("client_chat_message_send", "order-chat");
    setSendingChatMessage(true);
    try {
      await sendOrderMessage(request, chatOrderId, {
        body: chatBody,
        attachment_ids: chatAttachments.map((attachment) => attachment.id)
      }, `message_${chatOrderId}_${Date.now()}`);
      setChatBody("");
      setChatAttachments([]);
      await refreshChat();
      setNotice("Mensaje registrado.");
      recordActionCompleted("client_chat_message_send", "order-chat", startedAt);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "No pudimos enviar el mensaje.");
      recordActionFailed("client_chat_message_send", "order-chat", startedAt, error instanceof Error ? error.name : undefined);
    } finally {
      setSendingChatMessage(false);
    }
  }

  async function openOrderDispute() {
    if (!chatOrderId) {
      return;
    }
    const startedAt = actionStartedAt();
    recordActionStarted("client_order_dispute_open", "order-chat");
    setOpeningOrderDispute(true);
    try {
      await openOrderDisputeRequest(request, chatOrderId, {
        reason: disputeReason,
        description: chatBody || undefined,
        evidence_file_ids: []
      }, `dispute_${chatOrderId}_${Date.now()}`);
      await refreshChat();
      setNotice("Disputa abierta. La resolucion admin queda para contrato futuro.");
      recordActionCompleted("client_order_dispute_open", "order-chat", startedAt);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "No pudimos abrir la disputa.");
      recordActionFailed("client_order_dispute_open", "order-chat", startedAt, error instanceof Error ? error.name : undefined);
    } finally {
      setOpeningOrderDispute(false);
    }
  }

  return { openOrderChat, refreshChat, uploadChatAttachment, sendChatMessage, openOrderDispute };
}
