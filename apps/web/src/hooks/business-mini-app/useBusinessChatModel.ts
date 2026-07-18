import { useCallback, useState } from "react";
import { listOrderMessages, openOrderDispute as openOrderDisputeRequest, sendOrderMessage, uploadOrderMessageAttachment } from "../../api/chat";
import type { AuthenticatedRequest } from "../../api/client";
import type { BusinessMiniAppView } from "../../constants/businessViews";
import type { ChatAttachment, ChatCapabilities, ChatMessage } from "../../types/chat";
import { useStableIdempotencyKeys } from "../useStableIdempotencyKeys";

export function useBusinessChatModel({
  request,
  setBusy,
  setNotice,
  setView
}: {
  request: AuthenticatedRequest;
  setBusy: (busy: boolean) => void;
  setNotice: (notice: string) => void;
  setView: (view: BusinessMiniAppView) => void;
}) {
  const [chatOrderId, setChatOrderId] = useState<string | null>(null);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [chatCapabilities, setChatCapabilities] = useState<ChatCapabilities>({ can_send_message: false, can_open_dispute: false });
  const [chatBody, setChatBody] = useState("");
  const [chatAttachments, setChatAttachments] = useState<ChatAttachment[]>([]);
  const [disputeReason, setDisputeReason] = useState("business_no_payment_confirmation");
  const [openingOrderDispute, setOpeningOrderDispute] = useState(false);
  const [refreshingChat, setRefreshingChat] = useState(false);
  const [sendingChatMessage, setSendingChatMessage] = useState(false);
  const [uploadingChatAttachment, setUploadingChatAttachment] = useState(false);
  const { clearIdempotencyKey, getIdempotencyKey } = useStableIdempotencyKeys();

  const openBusinessChat = useCallback(async (orderId: string) => {
    setBusy(true);
    try {
      const data = await listOrderMessages<{ items: ChatMessage[]; capabilities: ChatCapabilities; disclaimer?: string }>(request, orderId);
      setChatOrderId(orderId);
      setChatMessages(data.items);
      setChatCapabilities(data.capabilities);
      setChatAttachments([]);
      setChatBody("");
      setView("business-chat");
      setNotice(data.disclaimer || "Chat operativo de la orden.");
    } catch (error) {
      setChatOrderId(orderId);
      setChatMessages([]);
      setChatCapabilities({ can_send_message: false, can_open_dispute: false });
      setView("business-chat");
      setNotice(error instanceof Error ? error.message : "No logramos abrir el chat de esta orden.");
    } finally {
      setBusy(false);
    }
  }, [request, setBusy, setNotice, setView]);

  const refreshChat = useCallback(async () => {
    if (!chatOrderId) {
      return;
    }
    setRefreshingChat(true);
    try {
      const data = await listOrderMessages<{ items: ChatMessage[]; capabilities: ChatCapabilities; disclaimer?: string }>(request, chatOrderId);
      setChatMessages(data.items);
      setChatCapabilities(data.capabilities);
      setNotice(data.disclaimer || "Chat actualizado.");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "No pudimos actualizar el chat.");
    } finally {
      setRefreshingChat(false);
    }
  }, [chatOrderId, request, setNotice]);

  const uploadChatAttachment = useCallback(async (file: File | null) => {
    if (!chatOrderId || !file) {
      return;
    }
    setUploadingChatAttachment(true);
    const idempotencyScope = `message_attachment_${chatOrderId}`;
    try {
      const data = await uploadOrderMessageAttachment<{ attachment: ChatAttachment }>(request, chatOrderId, file, getIdempotencyKey(idempotencyScope, { orderId: chatOrderId, name: file.name, size: file.size }));
      clearIdempotencyKey(idempotencyScope);
      setChatAttachments((current) => [...current, data.attachment]);
      setNotice("Archivo privado agregado al mensaje.");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "No pudimos adjuntar el archivo.");
    } finally {
      setUploadingChatAttachment(false);
    }
  }, [chatOrderId, clearIdempotencyKey, getIdempotencyKey, request, setNotice]);

  const sendChatMessage = useCallback(async () => {
    if (!chatOrderId) {
      return;
    }
    setSendingChatMessage(true);
    const idempotencyScope = `message_${chatOrderId}`;
    try {
      await sendOrderMessage(request, chatOrderId, {
        body: chatBody,
        attachment_ids: chatAttachments.map((attachment) => attachment.id)
      }, getIdempotencyKey(idempotencyScope, { orderId: chatOrderId, body: chatBody, attachmentIds: chatAttachments.map((attachment) => attachment.id) }));
      clearIdempotencyKey(idempotencyScope);
      setChatBody("");
      setChatAttachments([]);
      await refreshChat();
      setNotice("Mensaje enviado.");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "No pudimos enviar el mensaje.");
    } finally {
      setSendingChatMessage(false);
    }
  }, [chatAttachments, chatBody, chatOrderId, clearIdempotencyKey, getIdempotencyKey, refreshChat, request, setNotice]);

  const openOrderDispute = useCallback(async () => {
    if (!chatOrderId) {
      return;
    }
    setOpeningOrderDispute(true);
    const idempotencyScope = `dispute_${chatOrderId}`;
    try {
      await openOrderDisputeRequest(request, chatOrderId, {
        reason: disputeReason,
        description: chatBody || undefined,
        evidence_file_ids: []
      }, getIdempotencyKey(idempotencyScope, { orderId: chatOrderId, disputeReason, description: chatBody || undefined }));
      clearIdempotencyKey(idempotencyScope);
      await refreshChat();
      setNotice("Caso abierto para revision de NODO.");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "No pudimos abrir el caso.");
    } finally {
      setOpeningOrderDispute(false);
    }
  }, [chatBody, chatOrderId, clearIdempotencyKey, disputeReason, getIdempotencyKey, refreshChat, request, setNotice]);

  return {
    chatAttachments,
    chatBody,
    chatCapabilities,
    chatMessages,
    chatOrderId,
    disputeReason,
    openBusinessChat,
    openOrderDispute,
    openingOrderDispute,
    refreshChat,
    refreshingChat,
    sendChatMessage,
    sendingChatMessage,
    setChatBody,
    setDisputeReason,
    uploadingChatAttachment,
    uploadChatAttachment
  };
}
