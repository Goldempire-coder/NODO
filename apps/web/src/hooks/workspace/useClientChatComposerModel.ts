"use client";

import { useCallback, useEffect, useRef, useState, type Dispatch, type MutableRefObject, type SetStateAction } from "react";
import {
  openOrderMessageAttachment,
  sendOrderMessage,
  uploadOrderMessageAttachment
} from "../../api/chat";
import type { AuthenticatedRequest } from "../../api/client";
import { getTelegramWebApp } from "../../theme/telegramTheme";
import type { ChatAttachment, ChatAttachmentViewUrl } from "../../types/chat";
import { actionStartedAt, recordActionCompleted, recordActionFailed, recordActionStarted } from "../actionTelemetry";
import { useStableIdempotencyKeys } from "../useStableIdempotencyKeys";

type ChatComposerDraft = {
  body: string;
  attachments: ChatAttachment[];
};

export type ClientChatAttachmentLink = {
  orderId: string;
  url: string;
  downloadFilename: string;
  expiresInSeconds: number;
  mimeType: string;
};

function emptyChatComposerDraft(): ChatComposerDraft {
  return { body: "", attachments: [] };
}

function sameAttachmentIds(left: ChatAttachment[], right: ChatAttachment[]) {
  return left.length === right.length
    && left.every((attachment, index) => attachment.id === right[index]?.id);
}

function openTemporaryAttachmentUrl(url: string) {
  try {
    getTelegramWebApp()?.openLink?.(url);
    return;
  } catch {
    // Telegram link opening is best-effort; the rendered HTTPS fallback remains available.
  }
  window.open(url, "_blank", "noopener,noreferrer");
}

export function useClientChatComposerModel({
  request,
  chatOrderId,
  chatOrderIdRef,
  refreshChat,
  setNotice
}: {
  request: AuthenticatedRequest;
  chatOrderId: string | null;
  chatOrderIdRef: MutableRefObject<string | null>;
  refreshChat: (options?: { silent?: boolean }) => Promise<boolean>;
  setNotice: Dispatch<SetStateAction<string>>;
}) {
  const { clearIdempotencyKey, getIdempotencyKey } = useStableIdempotencyKeys();
  const sendingChatMessageRef = useRef(new Set<string>());
  const uploadingChatAttachmentRef = useRef(new Set<string>());
  const [composerDraftsByOrder, setComposerDraftsByOrder] = useState<Record<string, ChatComposerDraft>>({});
  const composerDraftsRef = useRef(composerDraftsByOrder);
  const [, setPendingVersion] = useState(0);
  const [chatAttachmentLink, setChatAttachmentLink] = useState<ClientChatAttachmentLink | null>(null);
  composerDraftsRef.current = composerDraftsByOrder;

  useEffect(() => {
    setChatAttachmentLink(null);
  }, [chatOrderId]);

  const activeDraft = chatOrderId
    ? composerDraftsByOrder[chatOrderId] || emptyChatComposerDraft()
    : emptyChatComposerDraft();

  const updateComposerDraftForOrder = useCallback((
    orderId: string,
    update: (draft: ChatComposerDraft) => ChatComposerDraft
  ) => {
    setComposerDraftsByOrder((current) => {
      const next = { ...current, [orderId]: update(current[orderId] || emptyChatComposerDraft()) };
      composerDraftsRef.current = next;
      return next;
    });
  }, []);

  const setChatBody = useCallback((update: SetStateAction<string>) => {
    const targetOrderId = chatOrderIdRef.current;
    if (!targetOrderId) {
      return;
    }
    updateComposerDraftForOrder(targetOrderId, (draft) => ({
      ...draft,
      body: typeof update === "function" ? update(draft.body) : update
    }));
  }, [chatOrderIdRef, updateComposerDraftForOrder]);

  const setOrderPending = (pendingOrders: Set<string>, orderId: string, pending: boolean) => {
    if (pending) {
      pendingOrders.add(orderId);
    } else {
      pendingOrders.delete(orderId);
    }
    setPendingVersion((current) => current + 1);
  };

  const clearSentComposerDraft = useCallback((orderId: string, sentDraft: ChatComposerDraft) => {
    setComposerDraftsByOrder((current) => {
      const active = current[orderId] || emptyChatComposerDraft();
      if (active.body !== sentDraft.body || !sameAttachmentIds(active.attachments, sentDraft.attachments)) {
        return current;
      }
      const next = { ...current, [orderId]: emptyChatComposerDraft() };
      composerDraftsRef.current = next;
      return next;
    });
  }, []);

  async function uploadChatAttachment(file: File | null) {
    const targetOrderId = chatOrderIdRef.current;
    if (!targetOrderId || uploadingChatAttachmentRef.current.has(targetOrderId) || !file) {
      return;
    }
    setOrderPending(uploadingChatAttachmentRef.current, targetOrderId, true);
    const startedAt = actionStartedAt();
    recordActionStarted("client_chat_attachment_upload", "order-chat");
    const idempotencyScope = `message_attachment_${targetOrderId}`;
    try {
      const data = await uploadOrderMessageAttachment<{ attachment: ChatAttachment }>(
        request,
        targetOrderId,
        file,
        getIdempotencyKey(idempotencyScope, { orderId: targetOrderId, name: file.name, size: file.size })
      );
      clearIdempotencyKey(idempotencyScope);
      // Store by order even when the user moved away; never inject an A response into B.
      updateComposerDraftForOrder(targetOrderId, (draft) => ({
        ...draft,
        attachments: [...draft.attachments, data.attachment]
      }));
      recordActionCompleted("client_chat_attachment_upload", "order-chat", startedAt);
    } catch (error) {
      if (chatOrderIdRef.current === targetOrderId) {
        setNotice(error instanceof Error ? error.message : "No pudimos adjuntar el archivo.");
      }
      recordActionFailed("client_chat_attachment_upload", "order-chat", startedAt, error instanceof Error ? error.name : undefined);
    } finally {
      setOrderPending(uploadingChatAttachmentRef.current, targetOrderId, false);
    }
  }

  async function sendChatMessage() {
    const targetOrderId = chatOrderIdRef.current;
    if (!targetOrderId || sendingChatMessageRef.current.has(targetOrderId)) {
      return;
    }
    const targetDraft = composerDraftsRef.current[targetOrderId] || emptyChatComposerDraft();
    const body = targetDraft.body.trim();
    if (!body && targetDraft.attachments.length === 0) {
      return;
    }
    setOrderPending(sendingChatMessageRef.current, targetOrderId, true);
    const startedAt = actionStartedAt();
    recordActionStarted("client_chat_message_send", "order-chat");
    const idempotencyScope = `message_${targetOrderId}`;
    const attachmentIds = targetDraft.attachments.map((attachment) => attachment.id);
    try {
      await sendOrderMessage(
        request,
        targetOrderId,
        { body, attachment_ids: attachmentIds },
        getIdempotencyKey(idempotencyScope, { orderId: targetOrderId, body, attachmentIds })
      );
      clearIdempotencyKey(idempotencyScope);
      clearSentComposerDraft(targetOrderId, targetDraft);
      if (chatOrderIdRef.current === targetOrderId) {
        await refreshChat({ silent: true });
      }
      recordActionCompleted("client_chat_message_send", "order-chat", startedAt);
    } catch (error) {
      if (chatOrderIdRef.current === targetOrderId) {
        setNotice(error instanceof Error ? error.message : "No pudimos enviar el mensaje.");
      }
      recordActionFailed("client_chat_message_send", "order-chat", startedAt, error instanceof Error ? error.name : undefined);
    } finally {
      setOrderPending(sendingChatMessageRef.current, targetOrderId, false);
    }
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
        orderId: targetOrderId,
        url: data.url,
        downloadFilename: data.download_filename,
        expiresInSeconds: data.expires_in_seconds,
        mimeType
      });
      openTemporaryAttachmentUrl(data.url);
    } catch (error) {
      if (chatOrderIdRef.current === targetOrderId) {
        setNotice(error instanceof Error ? error.message : "No pudimos abrir la imagen.");
      }
    }
  }

  return {
    chatBody: activeDraft.body,
    setChatBody,
    chatAttachments: activeDraft.attachments,
    uploadChatAttachment,
    uploadingChatAttachment: Boolean(chatOrderId && uploadingChatAttachmentRef.current.has(chatOrderId)),
    chatAttachmentLink: chatAttachmentLink?.orderId === chatOrderId ? chatAttachmentLink : null,
    dismissChatAttachmentLink: () => setChatAttachmentLink(null),
    openChatAttachment,
    sendChatMessage,
    sendingChatMessage: Boolean(chatOrderId && sendingChatMessageRef.current.has(chatOrderId))
  };
}
