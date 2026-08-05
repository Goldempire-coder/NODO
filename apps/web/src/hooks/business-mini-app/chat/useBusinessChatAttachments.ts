import { useCallback, useRef, useState } from "react";
import {
  openOrderMessageAttachment,
  uploadOrderMessageAttachment
} from "../../../api/chat";
import type { AuthenticatedRequest } from "../../../api/client";
import type {
  ChatAttachment,
  ChatAttachmentViewUrl
} from "../../../types/chat";
import { getTelegramWebApp } from "../../../theme/telegramTheme";
import { useStableIdempotencyKeys } from "../../useStableIdempotencyKeys";
import type {
  BusinessChatSessionScope,
  ChatAttachmentLink
} from "./businessChatShared";

function openTemporaryAttachmentUrl(url: string) {
  try {
    getTelegramWebApp()?.openLink?.(url);
    return;
  } catch {
    // Telegram native opening is best-effort; the signed-link preview remains visible.
  }
  window.open(url, "_blank", "noopener,noreferrer");
}

export function useBusinessChatAttachments({
  request,
  session,
  setNotice
}: {
  request: AuthenticatedRequest;
  session: BusinessChatSessionScope;
  setNotice: (notice: string) => void;
}) {
  const [chatAttachmentsByOrder, setChatAttachmentsByOrder] = useState<Record<string, ChatAttachment[]>>({});
  const [uploadingChatAttachment, setUploadingChatAttachment] = useState(false);
  const [chatAttachmentLink, setChatAttachmentLink] = useState<ChatAttachmentLink | null>(null);
  const uploadingChatAttachmentRef = useRef(new Set<string>());
  const chatAttachmentsByOrderRef = useRef(chatAttachmentsByOrder);
  chatAttachmentsByOrderRef.current = chatAttachmentsByOrder;
  const { clearIdempotencyKey, getIdempotencyKey } = useStableIdempotencyKeys();

  const chatAttachments = session.chatOrderId
    ? chatAttachmentsByOrder[session.chatOrderId] ?? []
    : [];

  const activateOrder = useCallback((orderId: string) => {
    setUploadingChatAttachment(uploadingChatAttachmentRef.current.has(orderId));
    setChatAttachmentLink(null);
  }, []);

  const getChatAttachments = useCallback((orderId: string) => (
    chatAttachmentsByOrderRef.current[orderId] ?? []
  ), []);

  const clearSubmittedChatAttachments = useCallback((orderId: string, submittedAttachmentIds: string[]) => {
    const submittedIds = new Set(submittedAttachmentIds);
    setChatAttachmentsByOrder((current) => {
      const existing = current[orderId] ?? [];
      const remaining = existing.filter((attachment) => !submittedIds.has(attachment.id));
      if (remaining.length === existing.length) {
        return current;
      }
      const next = { ...current };
      if (remaining.length) {
        next[orderId] = remaining;
      } else {
        delete next[orderId];
      }
      return next;
    });
  }, []);

  const uploadChatAttachment = useCallback(async (file: File | null) => {
    const targetOrderId = session.chatOrderIdRef.current;
    const targetSessionEpoch = session.chatSessionEpochRef.current;
    if (!targetOrderId || !file || uploadingChatAttachmentRef.current.has(targetOrderId)) {
      return;
    }
    uploadingChatAttachmentRef.current.add(targetOrderId);
    setUploadingChatAttachment(true);
    const idempotencyScope = `message_attachment_${targetOrderId}`;
    try {
      const data = await uploadOrderMessageAttachment<{ attachment: ChatAttachment }>(
        request,
        targetOrderId,
        file,
        getIdempotencyKey(idempotencyScope, {
          orderId: targetOrderId,
          name: file.name,
          size: file.size
        })
      );
      clearIdempotencyKey(idempotencyScope);
      if (!session.isCurrentChatSession(targetOrderId, targetSessionEpoch)) {
        return;
      }
      setChatAttachmentsByOrder((current) => {
        const existing = current[targetOrderId] ?? [];
        if (existing.some((attachment) => attachment.id === data.attachment.id)) {
          return current;
        }
        return { ...current, [targetOrderId]: [...existing, data.attachment] };
      });
    } catch (error) {
      if (session.isCurrentChatSession(targetOrderId, targetSessionEpoch)) {
        setNotice(error instanceof Error ? error.message : "No pudimos adjuntar el archivo.");
      }
    } finally {
      uploadingChatAttachmentRef.current.delete(targetOrderId);
      if (session.chatOrderIdRef.current === targetOrderId) {
        setUploadingChatAttachment(false);
      }
    }
  }, [clearIdempotencyKey, getIdempotencyKey, request, session, setNotice]);

  const dismissChatAttachmentLink = useCallback(() => {
    setChatAttachmentLink(null);
  }, []);

  const openChatAttachment = useCallback(async (
    attachmentId: string,
    mimeType = "application/octet-stream"
  ) => {
    const targetOrderId = session.chatOrderIdRef.current;
    const targetSessionEpoch = session.chatSessionEpochRef.current;
    if (!targetOrderId) {
      return;
    }
    try {
      const data = await openOrderMessageAttachment<ChatAttachmentViewUrl>(
        request,
        targetOrderId,
        attachmentId
      );
      if (!session.isCurrentChatSession(targetOrderId, targetSessionEpoch) || typeof window === "undefined") {
        return;
      }
      setChatAttachmentLink({
        url: data.url,
        downloadFilename: data.download_filename,
        expiresInSeconds: data.expires_in_seconds,
        mimeType
      });
      openTemporaryAttachmentUrl(data.url);
    } catch (error) {
      if (session.isCurrentChatSession(targetOrderId, targetSessionEpoch)) {
        setNotice(error instanceof Error ? error.message : "No pudimos abrir la imagen.");
      }
    }
  }, [request, session, setNotice]);

  return {
    activateOrder,
    chatAttachmentLink,
    chatAttachments,
    clearSubmittedChatAttachments,
    dismissChatAttachmentLink,
    getChatAttachments,
    openChatAttachment,
    uploadChatAttachment,
    uploadingChatAttachment
  };
}
