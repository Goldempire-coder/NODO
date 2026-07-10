"use client";

import { listOrderMessages, openOrderDispute as openOrderDisputeRequest, sendOrderMessage, uploadOrderMessageAttachment } from "../../api/chat";
import type { AuthenticatedRequest } from "../../api/client";
import { CHAT_DISPUTE_COPY } from "../../constants/copy";
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
    setBusy,
    setView
  } = state;

  async function openOrderChat(orderId: string) {
    setBusy(true);
    try {
      const data = await listOrderMessages<any>(request, orderId);
      setChatOrderId(orderId);
      setChatMessages(data.items);
      setChatCapabilities(data.capabilities);
      setChatAttachments([]);
      setChatBody("");
      setView("order-chat");
      setNotice(data.disclaimer || CHAT_DISPUTE_COPY);
    } catch (error) {
      setChatOrderId(orderId);
      setChatMessages([]);
      setChatCapabilities({ can_send_message: false, can_open_dispute: false });
      setView("order-chat");
      setNotice(error instanceof Error ? error.message : "No logramos abrir el chat de esta orden.");
    } finally {
      setBusy(false);
    }
  }

  async function refreshChat() {
    if (!chatOrderId) {
      return;
    }
    const data = await listOrderMessages<any>(request, chatOrderId);
    setChatMessages(data.items);
    setChatCapabilities(data.capabilities);
    setNotice(data.disclaimer || CHAT_DISPUTE_COPY);
  }

  async function uploadChatAttachment(file: File | null) {
    if (!chatOrderId || !file) {
      return;
    }
    setBusy(true);
    try {
      const data = await uploadOrderMessageAttachment<any>(request, chatOrderId, file, `message_attachment_${chatOrderId}_${Date.now()}`);
      setChatAttachments((current) => [...current, data.attachment]);
      setNotice("Archivo privado agregado al mensaje. No se muestra ruta interna.");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "No pudimos adjuntar el archivo.");
    } finally {
      setBusy(false);
    }
  }

  async function sendChatMessage() {
    if (!chatOrderId) {
      return;
    }
    setBusy(true);
    try {
      await sendOrderMessage(request, chatOrderId, {
        body: chatBody,
        attachment_ids: chatAttachments.map((attachment) => attachment.id)
      }, `message_${chatOrderId}_${Date.now()}`);
      setChatBody("");
      setChatAttachments([]);
      await refreshChat();
      setNotice("Mensaje registrado.");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "No pudimos enviar el mensaje.");
    } finally {
      setBusy(false);
    }
  }

  async function openOrderDispute() {
    if (!chatOrderId) {
      return;
    }
    setBusy(true);
    try {
      await openOrderDisputeRequest(request, chatOrderId, {
        reason: disputeReason,
        description: chatBody || undefined,
        evidence_file_ids: []
      }, `dispute_${chatOrderId}_${Date.now()}`);
      await refreshChat();
      setNotice("Disputa abierta. La resolucion admin queda para contrato futuro.");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "No pudimos abrir la disputa.");
    } finally {
      setBusy(false);
    }
  }

  return { openOrderChat, refreshChat, uploadChatAttachment, sendChatMessage, openOrderDispute };
}
