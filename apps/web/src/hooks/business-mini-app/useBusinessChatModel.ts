import { useCallback, useRef, useState } from "react";
import {
  listOrderMessages,
  openOrderDispute as openOrderDisputeRequest,
  sendOrderMessage,
  shareConfiguredZelle as shareConfiguredZelleRequest,
  uploadOrderMessageAttachment
} from "../../api/chat";
import type { AuthenticatedRequest } from "../../api/client";
import { revealOrderReceiverDetails } from "../../api/orders";
import type { BusinessMiniAppView } from "../../constants/businessViews";
import type {
  ChatAttachment,
  ChatCapabilities,
  ChatMessage,
  ChatThread
} from "../../types/chat";
import type { ReceiverDetails } from "../../types/orders";
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
    can_confirm_received: false
  });
  const [chatBody, setChatBody] = useState("");
  const [chatAttachments, setChatAttachments] = useState<ChatAttachment[]>([]);
  const [disputeReason, setDisputeReason] = useState("business_no_payment_confirmation");
  const [openingOrderDispute, setOpeningOrderDispute] = useState(false);
  const [refreshingChat, setRefreshingChat] = useState(false);
  const [sendingChatMessage, setSendingChatMessage] = useState(false);
  const [uploadingChatAttachment, setUploadingChatAttachment] = useState(false);
  const [sharingZelle, setSharingZelle] = useState(false);
  const [receiverDetails, setReceiverDetails] = useState<ReceiverDetails | null>(null);
  const [revealingReceiverDetails, setRevealingReceiverDetails] = useState(false);
  const sendingChatMessageRef = useRef(false);
  const uploadingChatAttachmentRef = useRef(false);
  const openingOrderDisputeRef = useRef(false);
  const sharingZelleRef = useRef(false);
  const revealingReceiverDetailsRef = useRef(false);
  const refreshingChatRef = useRef(false);
  const chatOrderIdRef = useRef(chatOrderId);
  chatOrderIdRef.current = chatOrderId;
  const { clearIdempotencyKey, getIdempotencyKey } = useStableIdempotencyKeys();

  const openBusinessChat = useCallback(async (orderId: string) => {
    chatOrderIdRef.current = orderId;
    setBusy(true);
    try {
      const data = await listOrderMessages<ChatThread>(request, orderId, 50);
      setChatOrderId(orderId);
      setChatMessages([...data.system_messages, ...data.items]);
      setChatCapabilities(data.capabilities);
      setChatAttachments([]);
      setChatBody("");
      setReceiverDetails(null);
      setView("business-chat");
      setNotice(data.disclaimer || "Chat operativo de la orden.");
    } catch (error) {
      setChatOrderId(orderId);
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
        can_confirm_received: false
      });
      setReceiverDetails(null);
      setView("business-chat");
      setNotice(error instanceof Error ? error.message : "No logramos abrir el chat de esta orden.");
    } finally {
      setBusy(false);
    }
  }, [request, setBusy, setNotice, setView]);

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
      const data = await listOrderMessages<ChatThread>(request, targetOrderId, 50);
      if (chatOrderIdRef.current !== targetOrderId) {
        return false;
      }
      setChatMessages([...data.system_messages, ...data.items]);
      setChatCapabilities(data.capabilities);
      if (!options?.silent) {
        setNotice(data.disclaimer || "Chat actualizado.");
      }
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
  }, [request, setNotice]);

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
      setNotice("Archivo privado agregado al mensaje.");
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
      setNotice("Mensaje enviado.");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "No pudimos enviar el mensaje.");
    } finally {
      sendingChatMessageRef.current = false;
      setSendingChatMessage(false);
    }
  }, [chatAttachments, chatBody, chatOrderId, clearIdempotencyKey, getIdempotencyKey, refreshChat, request, setNotice]);

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

  const openOrderDispute = useCallback(async () => {
    if (!chatOrderId || openingOrderDisputeRef.current) {
      return;
    }
    openingOrderDisputeRef.current = true;
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
      openingOrderDisputeRef.current = false;
      setOpeningOrderDispute(false);
    }
  }, [chatBody, chatOrderId, clearIdempotencyKey, disputeReason, getIdempotencyKey, refreshChat, request, setNotice]);

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
    receiverDetails,
    revealReceiverDetails,
    revealingReceiverDetails,
    sendChatMessage,
    sendingChatMessage,
    shareConfiguredZelle,
    sharingZelle,
    setChatBody,
    setDisputeReason,
    uploadingChatAttachment,
    uploadChatAttachment
  };
}
