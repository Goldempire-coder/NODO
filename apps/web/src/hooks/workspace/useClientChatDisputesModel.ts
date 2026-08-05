"use client";

import { useCallback, useRef, useState, type SetStateAction } from "react";
import { listOrderMessages } from "../../api/chat";
import type { AuthenticatedRequest } from "../../api/client";
import { confirmOrderReceived as confirmOrderReceivedRequest, getOrder, shareOrderReceiverDetails } from "../../api/orders";
import type { ChatCapabilities, ChatMessage, ChatThread } from "../../types/chat";
import type { OrderSummary, ReceiverDetailsInput, ReceiverDetailsMasked } from "../../types/orders";
import { actionStartedAt, recordActionCompleted, recordActionFailed, recordActionStarted } from "../actionTelemetry";
import { useStableIdempotencyKeys } from "../useStableIdempotencyKeys";
import { useClientChatComposerModel } from "./useClientChatComposerModel";
import { emptyPaymentReportForm, type ClientWorkspaceState } from "./useClientWorkspaceState";

const EMPTY_CHAT_CAPABILITIES: ChatCapabilities = {
  can_send_message: false,
  can_open_dispute: false,
  can_share_zelle: false,
  can_share_payment_details: false,
  payment_details_shared: false,
  can_report_payment: false,
  receiver_details_shared: false,
  can_share_receiver_details: false,
  can_reveal_receiver_details: false,
  receiver_details_required: false,
  can_confirm_received: false,
  can_confirm_payment: false,
  can_mark_delivered: false
};

function emptyReceiverDetailsForm(): ReceiverDetailsInput {
  return {
    bank: "0102",
    phone: "",
    document: "",
    holder: ""
  };
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

/** Coordinates active-order identity and backend-authoritative chat hydration. */
export function useClientChatDisputesModel(state: ClientWorkspaceState & { request: AuthenticatedRequest }) {
  const {
    request,
    chatOrderId,
    selectedOrder,
    paymentOrderContextRef,
    setChatOrderId,
    setChatMessages,
    setChatCapabilities,
    setNotice,
    setPaymentEvidence,
    setPaymentInstructions,
    setPaymentReportForm,
    setPendingPaymentReportId,
    setSelectedOrder,
    setOpeningChatOrderId,
    setRefreshingChat,
    setView
  } = state;
  const { clearIdempotencyKey, getIdempotencyKey } = useStableIdempotencyKeys();
  const receiverDetailsRequestsRef = useRef(new Set<string>());
  const confirmingOrderReceivedRef = useRef(new Set<string>());
  const refreshingChatRef = useRef(false);
  const openChatRequestIdRef = useRef(0);
  const chatOrderIdRef = useRef(chatOrderId);
  chatOrderIdRef.current = chatOrderId;
  const selectedOrderRef = useRef(selectedOrder);
  selectedOrderRef.current = selectedOrder;
  const [receiverDetailsDraftsByOrder, setReceiverDetailsDraftsByOrder] = useState<Record<string, ReceiverDetailsInput>>({});
  const receiverDetailsForm = chatOrderId
    ? receiverDetailsDraftsByOrder[chatOrderId] || emptyReceiverDetailsForm()
    : emptyReceiverDetailsForm();
  const setReceiverDetailsForm = useCallback((update: SetStateAction<ReceiverDetailsInput>) => {
    const targetOrderId = chatOrderId;
    if (!targetOrderId) {
      return;
    }
    setReceiverDetailsDraftsByOrder((current) => {
      const previous = current[targetOrderId] || emptyReceiverDetailsForm();
      const next = typeof update === "function" ? update(previous) : update;
      return { ...current, [targetOrderId]: next };
    });
  }, [chatOrderId]);
  const [receiverDetailsMasked, setReceiverDetailsMasked] = useState<ReceiverDetailsMasked | null>(null);
  const [sharingReceiverDetails, setSharingReceiverDetails] = useState(false);
  const [, setPendingActionVersion] = useState(0);
  const confirmingOrderReceived = Boolean(chatOrderId && confirmingOrderReceivedRef.current.has(chatOrderId));

  function setOrderActionPending(pendingOrders: Set<string>, orderId: string, pending: boolean) {
    if (pending) {
      pendingOrders.add(orderId);
    } else {
      pendingOrders.delete(orderId);
    }
    setPendingActionVersion((current) => current + 1);
  }

  const withRatingState = useCallback(async (order: OrderSummary): Promise<{ order: OrderSummary; ratingLoadFailed: boolean }> => {
    if (order.status !== "completed") {
      return { order, ratingLoadFailed: false };
    }
    const current = selectedOrderRef.current;
    if (current?.id === order.id && current.rating) {
      return { order: { ...order, rating: current.rating }, ratingLoadFailed: false };
    }
    try {
      const data = await getOrder<{ order: OrderSummary }>(request, order.id);
      return { order: { ...order, rating: data.order.rating }, ratingLoadFailed: false };
    } catch {
      return { order, ratingLoadFailed: true };
    }
  }, [request]);

  async function openOrderChat(orderId: string) {
    const targetOrderId = orderId;
    const requestId = openChatRequestIdRef.current + 1;
    openChatRequestIdRef.current = requestId;
    const startedAt = actionStartedAt();
    recordActionStarted("client_chat_open", "order-chat");
    paymentOrderContextRef.current = orderId;
    if (chatOrderIdRef.current !== targetOrderId) {
      chatOrderIdRef.current = targetOrderId;
      setChatOrderId(targetOrderId);
      setPaymentInstructions(null);
      setPaymentEvidence(null);
      setPendingPaymentReportId(null);
      setPaymentReportForm(emptyPaymentReportForm());
      setReceiverDetailsMasked(null);
      setChatMessages([]);
      setChatCapabilities(EMPTY_CHAT_CAPABILITIES);
      selectedOrderRef.current = null;
      setSelectedOrder(null);
      setSharingReceiverDetails(receiverDetailsRequestsRef.current.has(targetOrderId));
    }
    setOpeningChatOrderId(targetOrderId);
    try {
      const data = await listOrderMessages<ChatThread<OrderSummary>>(request, targetOrderId);
      const hydrated = await withRatingState(data.order);
      if (
        chatOrderIdRef.current !== targetOrderId
        || openChatRequestIdRef.current !== requestId
      ) {
        return false;
      }
      selectedOrderRef.current = hydrated.order;
      setSelectedOrder(hydrated.order);
      setChatMessages(sortChatMessages([...data.system_messages, ...data.items]));
      setChatCapabilities(data.capabilities);
      setReceiverDetailsMasked(null);
      setView("order-chat");
      setNotice(hydrated.ratingLoadFailed ? "Abrimos el chat, pero no pudimos cargar la calificacion." : "");
      recordActionCompleted("client_chat_open", "order-chat", startedAt);
      return true;
    } catch (error) {
      if (
        chatOrderIdRef.current !== targetOrderId
        || openChatRequestIdRef.current !== requestId
      ) {
        return false;
      }
      setChatMessages([]);
      setReceiverDetailsMasked(null);
      setChatCapabilities(EMPTY_CHAT_CAPABILITIES);
      setView("order-chat");
      setNotice(error instanceof Error ? error.message : "No logramos abrir el chat de esta orden.");
      recordActionFailed("client_chat_open", "order-chat", startedAt, error instanceof Error ? error.name : undefined);
      return false;
    } finally {
      setOpeningChatOrderId((current) => current === targetOrderId ? null : current);
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
      const hydrated = await withRatingState(data.order);
      if (chatOrderIdRef.current !== targetOrderId) {
        return false;
      }
      selectedOrderRef.current = hydrated.order;
      setSelectedOrder(hydrated.order);
      setChatMessages(sortChatMessages([...data.system_messages, ...data.items]));
      setChatCapabilities(data.capabilities);
      if (hydrated.ratingLoadFailed && !options?.silent) {
        setNotice("No pudimos cargar el estado de la calificacion.");
      }
      recordActionCompleted("client_chat_refresh", "order-chat", startedAt);
      return true;
    } catch (error) {
      if (chatOrderIdRef.current !== targetOrderId) {
        return false;
      }
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
  }, [request, setChatCapabilities, setChatMessages, setNotice, setRefreshingChat, setSelectedOrder, withRatingState]);

  const composer = useClientChatComposerModel({
    request,
    chatOrderId,
    chatOrderIdRef,
    refreshChat,
    setNotice
  });

  async function shareReceiverDetails() {
    const targetOrderId = chatOrderId;
    if (
      !targetOrderId
      || chatOrderIdRef.current !== targetOrderId
      || receiverDetailsRequestsRef.current.has(targetOrderId)
    ) {
      return;
    }
    const targetReceiverDetails = receiverDetailsForm;
    receiverDetailsRequestsRef.current.add(targetOrderId);
    setSharingReceiverDetails(true);
    const scope = `receiver_details_${targetOrderId}`;
    try {
      const data = await shareOrderReceiverDetails<{
        receiver_details_masked: ReceiverDetailsMasked;
      }>(
        request,
        targetOrderId,
        targetReceiverDetails,
        getIdempotencyKey(scope, { orderId: targetOrderId, ...targetReceiverDetails })
      );
      clearIdempotencyKey(scope);
      if (chatOrderIdRef.current !== targetOrderId) {
        return;
      }
      setReceiverDetailsMasked(data.receiver_details_masked);
      await refreshChat({ silent: true });
      if (chatOrderIdRef.current !== targetOrderId) {
        return;
      }
      setNotice("Pago Movil compartido.");
    } catch (error) {
      if (chatOrderIdRef.current === targetOrderId) {
        setNotice(error instanceof Error ? error.message : "No pudimos compartir el Pago Movil.");
      }
    } finally {
      receiverDetailsRequestsRef.current.delete(targetOrderId);
      if (chatOrderIdRef.current === targetOrderId) {
        setSharingReceiverDetails(false);
      }
    }
  }

  async function confirmOrderReceived() {
    const targetOrderId = chatOrderIdRef.current;
    if (!targetOrderId || confirmingOrderReceivedRef.current.has(targetOrderId)) {
      return;
    }
    setOrderActionPending(confirmingOrderReceivedRef.current, targetOrderId, true);
    const scope = `confirm_received_${targetOrderId}`;
    try {
      const data = await confirmOrderReceivedRequest<{
        order: OrderSummary;
        rating?: OrderSummary["rating"];
      }>(
        request,
        targetOrderId,
        getIdempotencyKey(scope, { orderId: targetOrderId, action: "manual_confirmed" })
      );
      clearIdempotencyKey(scope);
      if (chatOrderIdRef.current !== targetOrderId) {
        return;
      }
      const completedOrder = { ...data.order, rating: data.rating };
      selectedOrderRef.current = completedOrder;
      setSelectedOrder(completedOrder);
      await refreshChat({ silent: true });
      if (chatOrderIdRef.current !== targetOrderId) {
        return;
      }
      setNotice("Recepcion confirmada. La orden quedo completada.");
    } catch (error) {
      if (chatOrderIdRef.current === targetOrderId) {
        setNotice(error instanceof Error ? error.message : "No pudimos confirmar la recepcion.");
      }
    } finally {
      setOrderActionPending(confirmingOrderReceivedRef.current, targetOrderId, false);
    }
  }

  return {
    openOrderChat,
    refreshChat,
    ...composer,
    receiverDetailsForm,
    setReceiverDetailsForm,
    receiverDetailsMasked,
    sharingReceiverDetails,
    shareReceiverDetails,
    confirmingOrderReceived,
    confirmOrderReceived
  };
}
