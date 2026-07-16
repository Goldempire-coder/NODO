import { useCallback, useState } from "react";
import { listOrderMessages, openOrderDispute as openOrderDisputeRequest, sendOrderMessage, uploadOrderMessageAttachment } from "../../api/chat";
import type { AuthenticatedRequest } from "../../api/client";
import type { BusinessMiniAppView } from "../../constants/businessViews";
import type { ChatAttachment, ChatCapabilities, ChatMessage } from "../../types/chat";
import { idempotencyKey } from "./helpers";

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
    try {
      const data = await uploadOrderMessageAttachment<{ attachment: ChatAttachment }>(request, chatOrderId, file, idempotencyKey(`message_attachment_${chatOrderId}`));
      setChatAttachments((current) => [...current, data.attachment]);
      setNotice("Archivo privado agregado al mensaje.");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "No pudimos adjuntar el archivo.");
    } finally {
      setUploadingChatAttachment(false);
    }
  }, [chatOrderId, request, setNotice]);

  const sendChatMessage = useCallback(async () => {
    if (!chatOrderId) {
      return;
    }
    setSendingChatMessage(true);
    try {
      await sendOrderMessage(request, chatOrderId, {
        body: chatBody,
        attachment_ids: chatAttachments.map((attachment) => attachment.id)
      }, idempotencyKey(`message_${chatOrderId}`));
      setChatBody("");
      setChatAttachments([]);
      await refreshChat();
      setNotice("Mensaje enviado.");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "No pudimos enviar el mensaje.");
    } finally {
      setSendingChatMessage(false);
    }
  }, [chatAttachments, chatBody, chatOrderId, refreshChat, request, setNotice]);

  const openOrderDispute = useCallback(async () => {
    if (!chatOrderId) {
      return;
    }
    setOpeningOrderDispute(true);
    try {
      await openOrderDisputeRequest(request, chatOrderId, {
        reason: disputeReason,
        description: chatBody || undefined,
        evidence_file_ids: []
      }, idempotencyKey(`dispute_${chatOrderId}`));
      await refreshChat();
      setNotice("Caso abierto para revision de NODO.");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "No pudimos abrir el caso.");
    } finally {
      setOpeningOrderDispute(false);
    }
  }, [chatBody, chatOrderId, disputeReason, refreshChat, request, setNotice]);

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
