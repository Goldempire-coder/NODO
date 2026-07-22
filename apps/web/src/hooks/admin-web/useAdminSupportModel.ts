"use client";

import { useCallback, useRef, useState } from "react";
import {
  adminCloseSupportTicket,
  adminEscalateSupportTicket,
  adminGetSupportTicket,
  adminListSupportTickets,
  adminResolveSupportTicket,
  adminSendSupportMessage,
  adminSupportAttachmentViewUrl
} from "../../api/support";
import type { SupportMessage, SupportTicket } from "../../types/support";
import { useStableIdempotencyKeys } from "../useStableIdempotencyKeys";
import type { AdminWebView, RequestFn } from "./adminWebTypes";

type SupportAttachmentLink = {
  url: string;
  downloadFilename: string;
  expiresInSeconds: number;
};

const ACTIVE_SUPPORT_STATUSES = new Set<SupportTicket["status"]>(["open", "waiting_support", "waiting_user", "escalated"]);
const ARCHIVED_SUPPORT_STATUSES = new Set<SupportTicket["status"]>(["resolved", "closed"]);

function supportTicketsQuery(filter: string): string {
  const normalized = filter.trim().toLowerCase();
  if (!normalized || normalized === "active" || normalized === "archived" || normalized === "all") {
    return "?limit=50";
  }
  return `?status=${encodeURIComponent(normalized)}&limit=50`;
}

function filterSupportTickets(items: SupportTicket[], filter: string): SupportTicket[] {
  const normalized = filter.trim().toLowerCase() || "active";
  if (normalized === "active") {
    return items.filter((ticket) => ACTIVE_SUPPORT_STATUSES.has(ticket.status));
  }
  if (normalized === "archived") {
    return items.filter((ticket) => ARCHIVED_SUPPORT_STATUSES.has(ticket.status));
  }
  return items;
}

function archivedTicketNotice(status: SupportTicket["status"]): string {
  if (status === "closed") {
    return "Ticket cerrado y enviado a archivados.";
  }
  if (status === "resolved") {
    return "Ticket resuelto y enviado a archivados.";
  }
  return "Ticket actualizado.";
}

function buildOptimisticSupportMessage(ticket: SupportTicket, body: string): SupportMessage {
  const createdAt = new Date().toISOString();
  return {
    id: `optimistic_${ticket.id}_${createdAt}`,
    ticket_id: ticket.id,
    sender_role: "support",
    body,
    visibility: "participants",
    attachments: [],
    created_at: createdAt
  };
}

function appendSupportMessage(ticket: SupportTicket, message: SupportMessage): SupportTicket {
  return {
    ...ticket,
    messages: [...(ticket.messages || []), message],
    last_message_at: message.created_at,
    updated_at: message.created_at
  };
}

function removeSupportMessage(ticket: SupportTicket, messageId: string): SupportTicket {
  return {
    ...ticket,
    messages: (ticket.messages || []).filter((message) => message.id !== messageId)
  };
}

function applySupportMessageResult(ticket: SupportTicket, optimisticMessageId: string, message: SupportMessage, summary: SupportTicket): SupportTicket {
  const mergedMessages = (ticket.messages || []).map((item) => (item.id === optimisticMessageId ? message : item));
  const hasMessage = mergedMessages.some((item) => item.id === message.id);
  return {
    ...ticket,
    ...summary,
    attachments: ticket.attachments,
    events: ticket.events,
    messages: hasMessage ? mergedMessages : [...mergedMessages, message],
    disclaimer: ticket.disclaimer
  };
}

export function useAdminSupportModel({
  request,
  setBusy,
  setNotice,
  setView
}: {
  request: RequestFn;
  setBusy: (busy: boolean) => void;
  setNotice: (notice: string) => void;
  setView: (view: AdminWebView) => void;
}) {
  const [supportTickets, setSupportTickets] = useState<SupportTicket[]>([]);
  const [selectedSupportTicket, setSelectedSupportTicket] = useState<SupportTicket | null>(null);
  const [supportFilter, setSupportFilter] = useState("active");
  const [supportReply, setSupportReply] = useState("");
  const [supportAttachmentLink, setSupportAttachmentLink] = useState<SupportAttachmentLink | null>(null);
  const [sendingSupportReply, setSendingSupportReply] = useState(false);
  const supportReplyInFlight = useRef(false);
  const { clearIdempotencyKey, getIdempotencyKey } = useStableIdempotencyKeys();

  const loadSupportTickets = useCallback(async (filter = supportFilter) => {
    setBusy(true);
    try {
      const normalizedFilter = filter.trim().toLowerCase() || "active";
      const payload = await adminListSupportTickets(request, supportTicketsQuery(normalizedFilter));
      setSupportTickets(filterSupportTickets(payload.items, normalizedFilter));
      if (selectedSupportTicket && normalizedFilter === "active" && ARCHIVED_SUPPORT_STATUSES.has(selectedSupportTicket.status)) {
        setSelectedSupportTicket(null);
      }
      setSupportFilter(normalizedFilter);
      setView("support");
      setNotice("");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "No pudimos cargar soporte.");
    } finally {
      setBusy(false);
    }
  }, [request, selectedSupportTicket, setBusy, setNotice, setView, supportFilter]);

  const refreshSupportWorkspace = useCallback(async () => {
    const normalizedFilter = supportFilter.trim().toLowerCase() || "active";
    try {
      const payload = await adminListSupportTickets(request, supportTicketsQuery(normalizedFilter));
      setSupportTickets(filterSupportTickets(payload.items, normalizedFilter));
      if (selectedSupportTicket) {
        const ticket = await adminGetSupportTicket(request, selectedSupportTicket.id);
        if (normalizedFilter === "active" && ARCHIVED_SUPPORT_STATUSES.has(ticket.status)) {
          setSelectedSupportTicket(null);
          return;
        }
        setSelectedSupportTicket(ticket);
      }
    } catch {
      // Background refresh should not interrupt the operator's current action.
    }
  }, [request, selectedSupportTicket, supportFilter]);

  const openSupportTicket = useCallback(async (ticketId: string) => {
    setBusy(true);
    try {
      const ticket = await adminGetSupportTicket(request, ticketId);
      setSelectedSupportTicket(ticket);
      setSupportAttachmentLink(null);
      setView("support");
      setNotice("");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "No pudimos abrir el ticket.");
    } finally {
      setBusy(false);
    }
  }, [request, setBusy, setNotice, setView]);

  const refreshSelectedSupportTicket = useCallback(async () => {
    if (!selectedSupportTicket) {
      return;
    }
    const ticket = await adminGetSupportTicket(request, selectedSupportTicket.id);
    setSelectedSupportTicket(ticket);
  }, [request, selectedSupportTicket]);

  const replySupportTicket = useCallback(async () => {
    if (!selectedSupportTicket || !supportReply.trim() || supportReplyInFlight.current) {
      return;
    }
    const body = supportReply.trim();
    const optimisticMessage = buildOptimisticSupportMessage(selectedSupportTicket, body);
    supportReplyInFlight.current = true;
    setSendingSupportReply(true);
    setBusy(true);
    const idempotencyScope = `admin_support_msg_${selectedSupportTicket.id}`;
    try {
      setSupportReply("");
      setSelectedSupportTicket((current) => (current?.id === selectedSupportTicket.id ? appendSupportMessage(current, optimisticMessage) : current));
      const payload = await adminSendSupportMessage(request, selectedSupportTicket.id, body, getIdempotencyKey(idempotencyScope, { ticketId: selectedSupportTicket.id, body }));
      clearIdempotencyKey(idempotencyScope);
      setSelectedSupportTicket((current) => (current?.id === selectedSupportTicket.id ? applySupportMessageResult(current, optimisticMessage.id, payload.message, payload.ticket) : current));
      setSupportTickets((items) => items.map((item) => (item.id === payload.ticket.id ? payload.ticket : item)));
      setNotice("");
    } catch (error) {
      setSelectedSupportTicket((current) => (current?.id === selectedSupportTicket.id ? removeSupportMessage(current, optimisticMessage.id) : current));
      setNotice(error instanceof Error ? `${error.message}. Actualiza el hilo antes de reenviar.` : "No pudimos confirmar el envio. Actualiza el hilo antes de reenviar.");
    } finally {
      supportReplyInFlight.current = false;
      setSendingSupportReply(false);
      setBusy(false);
    }
  }, [clearIdempotencyKey, getIdempotencyKey, request, selectedSupportTicket, setBusy, setNotice, supportReply]);

  const changeSupportStatus = useCallback(async (action: "escalate" | "resolve" | "close", reason: string) => {
    if (!selectedSupportTicket) {
      return;
    }
    setBusy(true);
    const idempotencyScope = `support_${action}_${selectedSupportTicket.id}`;
    try {
      const methods = {
        escalate: adminEscalateSupportTicket,
        resolve: adminResolveSupportTicket,
        close: adminCloseSupportTicket
      };
      const ticket = await methods[action](request, selectedSupportTicket.id, reason, getIdempotencyKey(idempotencyScope, { ticketId: selectedSupportTicket.id, action, reason }));
      clearIdempotencyKey(idempotencyScope);
      if (ARCHIVED_SUPPORT_STATUSES.has(ticket.status)) {
        setSelectedSupportTicket(null);
        setSupportTickets((items) => items.filter((item) => item.id !== ticket.id));
        setNotice(archivedTicketNotice(ticket.status));
        return;
      }
      setSelectedSupportTicket(ticket);
      setSupportTickets((items) => items.map((item) => (item.id === ticket.id ? ticket : item)));
      setNotice(archivedTicketNotice(ticket.status));
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "No pudimos actualizar el ticket.");
    } finally {
      setBusy(false);
    }
  }, [clearIdempotencyKey, getIdempotencyKey, request, selectedSupportTicket, setBusy, setNotice]);

  const openSupportAttachment = useCallback(async (fileId: string, reason: string, mode: "view" | "download" = "view") => {
    if (!selectedSupportTicket) {
      return;
    }
    setBusy(true);
    try {
      const payload = await adminSupportAttachmentViewUrl(request, selectedSupportTicket.id, fileId, reason);
      const link = {
        url: payload.url,
        downloadFilename: payload.download_filename,
        expiresInSeconds: payload.expires_in_seconds
      };
      setSupportAttachmentLink(link);
      if (mode === "download") {
        const anchor = window.document.createElement("a");
        anchor.href = payload.url;
        anchor.download = payload.download_filename;
        anchor.target = "_blank";
        anchor.rel = "noopener noreferrer";
        anchor.click();
        setNotice(`Descarga solicitada: ${payload.download_filename}.`);
        return;
      }
      window.open(payload.url, "_blank", "noopener,noreferrer");
      setNotice(`Adjunto listo por ${payload.expires_in_seconds}s. Si no se abrio, usa Abrir o Descargar.`);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "No pudimos abrir el adjunto.");
    } finally {
      setBusy(false);
    }
  }, [request, selectedSupportTicket, setBusy, setNotice]);

  return {
    supportTickets,
    selectedSupportTicket,
    supportFilter,
    setSupportFilter,
    supportReply,
    setSupportReply,
    sendingSupportReply,
    supportAttachmentLink,
    supportAttachmentUrl: supportAttachmentLink?.url || "",
    loadSupportTickets,
    refreshSupportWorkspace,
    openSupportTicket,
    refreshSelectedSupportTicket,
    replySupportTicket,
    changeSupportStatus,
    openSupportAttachment
  };
}
