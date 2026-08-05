import { useCallback, useRef, useState } from "react";
import { sendOrderMessage } from "../../../api/chat";
import type { AuthenticatedRequest } from "../../../api/client";
import type { ChatAttachment } from "../../../types/chat";
import { useStableIdempotencyKeys } from "../../useStableIdempotencyKeys";
import type { BusinessChatSessionScope } from "./businessChatShared";

export function useBusinessChatComposer({
  request,
  session,
  getChatAttachments,
  clearSubmittedChatAttachments,
  setNotice
}: {
  request: AuthenticatedRequest;
  session: BusinessChatSessionScope;
  getChatAttachments: (orderId: string) => ChatAttachment[];
  clearSubmittedChatAttachments: (orderId: string, attachmentIds: string[]) => void;
  setNotice: (notice: string) => void;
}) {
  const [chatDraftsByOrder, setChatDraftsByOrder] = useState<Record<string, string>>({});
  const [sendingChatMessage, setSendingChatMessage] = useState(false);
  const sendingChatMessageRef = useRef(new Set<string>());
  const chatDraftsByOrderRef = useRef(chatDraftsByOrder);
  chatDraftsByOrderRef.current = chatDraftsByOrder;
  const { clearIdempotencyKey, getIdempotencyKey } = useStableIdempotencyKeys();

  const chatBody = session.chatOrderId
    ? chatDraftsByOrder[session.chatOrderId] ?? ""
    : "";

  const activateOrder = useCallback((orderId: string) => {
    setSendingChatMessage(sendingChatMessageRef.current.has(orderId));
  }, []);

  const setChatBody = useCallback((body: string) => {
    const targetOrderId = session.chatOrderIdRef.current;
    if (!targetOrderId) {
      return;
    }
    setChatDraftsByOrder((current) => ({ ...current, [targetOrderId]: body }));
  }, [session.chatOrderIdRef]);

  const clearSubmittedChatDraft = useCallback((orderId: string, submittedBody: string) => {
    setChatDraftsByOrder((current) => {
      if ((current[orderId] ?? "").trim() !== submittedBody) {
        return current;
      }
      const next = { ...current };
      delete next[orderId];
      return next;
    });
  }, []);

  const sendChatMessage = useCallback(async () => {
    const targetOrderId = session.chatOrderIdRef.current;
    const targetSessionEpoch = session.chatSessionEpochRef.current;
    const body = targetOrderId ? (chatDraftsByOrderRef.current[targetOrderId] ?? "").trim() : "";
    const attachments = targetOrderId ? getChatAttachments(targetOrderId) : [];
    const attachmentIds = attachments.map((attachment) => attachment.id);
    if (
      !targetOrderId
      || sendingChatMessageRef.current.has(targetOrderId)
      || (!body && attachmentIds.length === 0)
    ) {
      return;
    }
    sendingChatMessageRef.current.add(targetOrderId);
    setSendingChatMessage(true);
    const idempotencyScope = `message_${targetOrderId}`;
    try {
      await sendOrderMessage(request, targetOrderId, {
        body,
        attachment_ids: attachmentIds
      }, getIdempotencyKey(idempotencyScope, { orderId: targetOrderId, body, attachmentIds }));
      clearIdempotencyKey(idempotencyScope);
      clearSubmittedChatDraft(targetOrderId, body);
      clearSubmittedChatAttachments(targetOrderId, attachmentIds);
      if (session.isCurrentChatSession(targetOrderId, targetSessionEpoch)) {
        await session.refreshChatSession(targetOrderId, targetSessionEpoch, { silent: true });
      }
    } catch (error) {
      if (session.isCurrentChatSession(targetOrderId, targetSessionEpoch)) {
        setNotice(error instanceof Error ? error.message : "No pudimos enviar el mensaje.");
      }
    } finally {
      sendingChatMessageRef.current.delete(targetOrderId);
      if (session.chatOrderIdRef.current === targetOrderId) {
        setSendingChatMessage(false);
      }
    }
  }, [
    clearIdempotencyKey,
    clearSubmittedChatAttachments,
    clearSubmittedChatDraft,
    getChatAttachments,
    getIdempotencyKey,
    request,
    session,
    setNotice
  ]);

  return {
    activateOrder,
    chatBody,
    sendChatMessage,
    sendingChatMessage,
    setChatBody
  };
}
