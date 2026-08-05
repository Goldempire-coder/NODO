import { useCallback, useMemo, useRef, useState } from "react";
import { listOrderMessages } from "../../../api/chat";
import type { AuthenticatedRequest } from "../../../api/client";
import type { BusinessMiniAppView } from "../../../constants/businessViews";
import type { ChatCapabilities, ChatMessage, ChatThread } from "../../../types/chat";
import type { BusinessOrderSummary } from "../../../types/orders";
import {
  chatSessionKey,
  EMPTY_CHAT_CAPABILITIES,
  sortChatMessages
} from "./businessChatShared";

export function useBusinessChatSession({
  request,
  syncBusinessOrderFromChat,
  setBusy,
  setNotice,
  setView
}: {
  request: AuthenticatedRequest;
  syncBusinessOrderFromChat: (order: BusinessOrderSummary) => void;
  setBusy: (busy: boolean) => void;
  setNotice: (notice: string) => void;
  setView: (view: BusinessMiniAppView) => void;
}) {
  const [chatOrderId, setChatOrderId] = useState<string | null>(null);
  const [chatOrder, setChatOrder] = useState<BusinessOrderSummary | null>(null);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [chatCapabilities, setChatCapabilities] = useState<ChatCapabilities>({ ...EMPTY_CHAT_CAPABILITIES });
  const [refreshingChat, setRefreshingChat] = useState(false);
  const refreshingChatRef = useRef(new Set<string>());
  const chatSessionEpochRef = useRef(0);
  const chatCapabilitiesOrderIdRef = useRef<string | null>(null);
  const chatOrderIdRef = useRef(chatOrderId);
  chatOrderIdRef.current = chatOrderId;

  // Every async chat operation captures this pair so order A can never overwrite order B.
  const isCurrentChatSession = useCallback((orderId: string, sessionEpoch: number) => (
    chatOrderIdRef.current === orderId && chatSessionEpochRef.current === sessionEpoch
  ), []);

  const applyChatThread = useCallback((
    orderId: string,
    data: ChatThread<BusinessOrderSummary>
  ) => {
    syncBusinessOrderFromChat(data.order);
    setChatOrder(data.order);
    setChatMessages(sortChatMessages([...data.system_messages, ...data.items]));
    chatCapabilitiesOrderIdRef.current = orderId;
    setChatCapabilities(data.capabilities);
  }, [syncBusinessOrderFromChat]);

  const reloadChatSession = useCallback(async (orderId: string, sessionEpoch: number) => {
    if (!isCurrentChatSession(orderId, sessionEpoch)) {
      return false;
    }
    const data = await listOrderMessages<ChatThread<BusinessOrderSummary>>(request, orderId, 50);
    if (!isCurrentChatSession(orderId, sessionEpoch)) {
      return false;
    }
    applyChatThread(orderId, data);
    return true;
  }, [applyChatThread, isCurrentChatSession, request]);

  const openBusinessChat = useCallback(async (orderId: string) => {
    const targetSessionEpoch = chatSessionEpochRef.current + 1;
    chatSessionEpochRef.current = targetSessionEpoch;
    chatOrderIdRef.current = orderId;
    setChatOrderId(orderId);
    setChatOrder(null);
    setChatMessages([]);
    chatCapabilitiesOrderIdRef.current = null;
    setChatCapabilities({ ...EMPTY_CHAT_CAPABILITIES });
    setRefreshingChat(false);
    setView("business-chat");
    setNotice("");
    setBusy(true);
    try {
      return await reloadChatSession(orderId, targetSessionEpoch);
    } catch (error) {
      if (!isCurrentChatSession(orderId, targetSessionEpoch)) {
        return false;
      }
      setChatOrder(null);
      setChatMessages([]);
      chatCapabilitiesOrderIdRef.current = null;
      setChatCapabilities({ ...EMPTY_CHAT_CAPABILITIES });
      setNotice(error instanceof Error ? error.message : "No logramos abrir el chat de esta orden.");
      return false;
    } finally {
      if (isCurrentChatSession(orderId, targetSessionEpoch)) {
        setBusy(false);
      }
    }
  }, [isCurrentChatSession, reloadChatSession, setBusy, setNotice, setView]);

  const refreshChatSession = useCallback(async (
    targetOrderId: string,
    targetSessionEpoch: number,
    options?: { silent?: boolean }
  ) => {
    const targetSessionKey = chatSessionKey(targetOrderId, targetSessionEpoch);
    if (
      !isCurrentChatSession(targetOrderId, targetSessionEpoch)
      || refreshingChatRef.current.has(targetSessionKey)
    ) {
      return false;
    }
    refreshingChatRef.current.add(targetSessionKey);
    if (!options?.silent) {
      setRefreshingChat(true);
    }
    try {
      return await reloadChatSession(targetOrderId, targetSessionEpoch);
    } catch (error) {
      if (isCurrentChatSession(targetOrderId, targetSessionEpoch) && !options?.silent) {
        setNotice(error instanceof Error ? error.message : "No pudimos actualizar el chat.");
      }
      return false;
    } finally {
      refreshingChatRef.current.delete(targetSessionKey);
      if (isCurrentChatSession(targetOrderId, targetSessionEpoch) && !options?.silent) {
        setRefreshingChat(false);
      }
    }
  }, [isCurrentChatSession, reloadChatSession, setNotice]);

  const refreshChat = useCallback(async (options?: { silent?: boolean }) => {
    const targetOrderId = chatOrderIdRef.current;
    const targetSessionEpoch = chatSessionEpochRef.current;
    if (!targetOrderId) {
      return false;
    }
    return refreshChatSession(targetOrderId, targetSessionEpoch, options);
  }, [refreshChatSession]);

  const setCurrentChatOrder = useCallback((
    orderId: string,
    sessionEpoch: number,
    order: BusinessOrderSummary
  ) => {
    if (!isCurrentChatSession(orderId, sessionEpoch)) {
      return false;
    }
    setChatOrder(order);
    return true;
  }, [isCurrentChatSession]);

  const scope = useMemo(() => ({
    chatOrderId,
    chatOrderIdRef,
    chatSessionEpochRef,
    chatCapabilitiesOrderIdRef,
    isCurrentChatSession,
    refreshChatSession
  }), [chatOrderId, isCurrentChatSession, refreshChatSession]);

  return {
    chatCapabilities,
    chatCapabilitiesOrderIdRef,
    chatMessages,
    chatOrder,
    chatOrderId,
    chatOrderIdRef,
    chatSessionEpochRef,
    isCurrentChatSession,
    openBusinessChat,
    refreshChat,
    refreshingChat,
    refreshChatSession,
    reloadChatSession,
    scope,
    setCurrentChatOrder
  };
}
