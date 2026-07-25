"use client";

import { useRef } from "react";
import { listOrderMessages, openOrderDispute as openOrderDisputeRequest, sendOrderMessage, uploadOrderMessageAttachment } from "../../api/chat";
import type { AuthenticatedRequest } from "../../api/client";
import { CHAT_DISPUTE_COPY } from "../../constants/copy";
import { actionStartedAt, recordActionCompleted, recordActionFailed, recordActionStarted } from "../actionTelemetry";
import { useStableIdempotencyKeys } from "../useStableIdempotencyKeys";
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
  const { clearIdempotencyKey, getIdempotencyKey } = useStableIdempotencyKeys();
  const sendingChatMessageRef = useRef(false);
  const uploadingChatAttachmentRef = useRef(false);
  const openingOrderDisputeRef = useRef(false);

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

  async function refreshChat(options?: { silent?: boolean }) {
    if (!chatOrderId) {
      return;
    }
    const startedAt = actionStartedAt();
    recordActionStarted("client_chat_refresh", "order-chat");
    if (!options?.silent) {
      setRefreshingChat(true);
    }
    try {
      const data = await listOrderMessages<any>(request, chatOrderId);
      setChatMessages(data.items);
      setChatCapabilities(data.capabilities);
      setNotice(data.disclaimer || CHAT_DISPUTE_COPY);
      recordActionCompleted("client_chat_refresh", "order-chat", startedAt);
    } catch (error) {
      if (!options?.silent) {
        setNotice(error instanceof Error ? error.message : "No pudimos actualizar el chat.");
      }
      recordActionFailed("client_chat_refresh", "order-chat", startedAt, error instanceof Error ? error.name : undefined);
    } finally {
      if (!options?.silent) {
        setRefreshingChat(false);
      }
    }
  }

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
      setNotice("Archivo privado agregado al mensaje. No se muestra ruta interna.");
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
      setNotice("Mensaje registrado.");
      recordActionCompleted("client_chat_message_send", "order-chat", startedAt);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "No pudimos enviar el mensaje.");
      recordActionFailed("client_chat_message_send", "order-chat", startedAt, error instanceof Error ? error.name : undefined);
    } finally {
      sendingChatMessageRef.current = false;
      setSendingChatMessage(false);
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

  return { openOrderChat, refreshChat, uploadChatAttachment, sendChatMessage, openOrderDispute };
}
