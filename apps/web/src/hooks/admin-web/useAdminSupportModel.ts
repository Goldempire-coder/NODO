"use client";

import { useCallback, useRef, useState } from "react";
import { listAdminStaff } from "../../api/admin";
import {
  adminAssignSupportTicket,
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
const ASSIGNABLE_STAFF_ROLES = new Set(["support_agent", "support_lead", "admin", "super_admin"]);

type SupportAssignee = {
  id: string;
  user_id: string;
  display_name?: string | null;
  username?: string | null;
  staff_role: string;
  status: string;
};

function supportTicketsQuery(filter: string): string {
  const normalized = filter.trim().toLowerCase();
  if (normalized === "active" || normalized === "archived") {
    return `?status_group=${encodeURIComponent(normalized)}&limit=50`;
  }
  if (!normalized || normalized === "all") {
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
  adminMutable,
  request,
  setBusy,
  setNotice,
  setView
}: {
  adminMutable: boolean;
  request: RequestFn;
  setBusy: (busy: boolean) => void;
  setNotice: (notice: string) => void;
  setView: (view: AdminWebView) => void;
}) {
  const [supportTickets, setSupportTickets] = useState<SupportTicket[]>([]);
  const [selectedSupportTicket, setSelectedSupportTicket] = useState<SupportTicket | null>(null);
  const [supportFilter, setSupportFilter] = useState("active");
  const [supportReplyDrafts, setSupportReplyDrafts] = useState<Record<string, string>>({});
  const [supportAttachmentLink, setSupportAttachmentLink] = useState<SupportAttachmentLink | null>(null);
  const [sendingSupportReply, setSendingSupportReply] = useState(false);
  const [supportAssignees, setSupportAssignees] = useState<SupportAssignee[]>([]);
  const [supportAssigneesLoaded, setSupportAssigneesLoaded] = useState(false);
  const [supportAssigneesLoading, setSupportAssigneesLoading] = useState(false);
  const [supportAssigneesTruncated, setSupportAssigneesTruncated] = useState(false);
  const [supportAssigneeUserId, setSupportAssigneeUserId] = useState("");
  const [supportAssignmentReason, setSupportAssignmentReason] = useState("");
  const [assigningSupportTicketId, setAssigningSupportTicketId] = useState<string | null>(null);
  const supportReplyInFlight = useRef(false);
  const supportAssigneesLoadingRef = useRef(false);
  const supportAssignmentInFlight = useRef(false);
  const selectedSupportTicketIdRef = useRef<string | null>(null);
  const { clearIdempotencyKey, getIdempotencyKey } = useStableIdempotencyKeys();
  const supportReply = selectedSupportTicket ? supportReplyDrafts[selectedSupportTicket.id] ?? "" : "";

  const setSupportReplyDraft = useCallback((ticketId: string, value: string) => {
    setSupportReplyDrafts((current) => {
      if (value === "") {
        if (!(ticketId in current)) {
          return current;
        }
        const next = { ...current };
        delete next[ticketId];
        return next;
      }
      if (current[ticketId] === value) {
        return current;
      }
      return { ...current, [ticketId]: value };
    });
  }, []);

  const clearSupportReplyDraft = useCallback((ticketId: string) => {
    setSupportReplyDraft(ticketId, "");
  }, [setSupportReplyDraft]);

  const setSupportReply = useCallback((value: string) => {
    const ticketId = selectedSupportTicketIdRef.current;
    if (ticketId) {
      setSupportReplyDraft(ticketId, value);
    }
  }, [setSupportReplyDraft]);

  const selectSupportTicket = useCallback((ticket: SupportTicket | null) => {
    selectedSupportTicketIdRef.current = ticket?.id ?? null;
    setSelectedSupportTicket(ticket);
  }, []);

  const loadSupportTickets = useCallback(async (filter = supportFilter) => {
    setBusy(true);
    try {
      const normalizedFilter = filter.trim().toLowerCase() || "active";
      const payload = await adminListSupportTickets(request, supportTicketsQuery(normalizedFilter));
      setSupportTickets(filterSupportTickets(payload.items, normalizedFilter));
      if (selectedSupportTicket && normalizedFilter === "active" && ARCHIVED_SUPPORT_STATUSES.has(selectedSupportTicket.status)) {
        selectSupportTicket(null);
      }
      setSupportFilter(normalizedFilter);
      setView("support");
      setNotice("");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "No pudimos cargar soporte.");
    } finally {
      setBusy(false);
    }
  }, [request, selectedSupportTicket, selectSupportTicket, setBusy, setNotice, setView, supportFilter]);

  const refreshSupportWorkspace = useCallback(async () => {
    const normalizedFilter = supportFilter.trim().toLowerCase() || "active";
    try {
      const payload = await adminListSupportTickets(request, supportTicketsQuery(normalizedFilter));
      setSupportTickets(filterSupportTickets(payload.items, normalizedFilter));
      if (selectedSupportTicket) {
        const ticket = await adminGetSupportTicket(request, selectedSupportTicket.id);
        if (normalizedFilter === "active" && ARCHIVED_SUPPORT_STATUSES.has(ticket.status)) {
          selectSupportTicket(null);
          return;
        }
        selectSupportTicket(ticket);
      }
    } catch {
      // Background refresh should not interrupt the operator's current action.
    }
  }, [request, selectedSupportTicket, selectSupportTicket, supportFilter]);

  const openSupportTicket = useCallback(async (ticketId: string) => {
    setBusy(true);
    try {
      const ticket = await adminGetSupportTicket(request, ticketId);
      selectSupportTicket(ticket);
      setSupportAssigneeUserId("");
      setSupportAssignmentReason("");
      setSupportAttachmentLink(null);
      setView("support");
      setNotice("");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "No pudimos abrir el ticket.");
    } finally {
      setBusy(false);
    }
  }, [request, selectSupportTicket, setBusy, setNotice, setView]);

  const loadSupportAssignees = useCallback(async () => {
    if (!adminMutable || supportAssigneesLoadingRef.current) {
      return;
    }
    supportAssigneesLoadingRef.current = true;
    setSupportAssigneesLoading(true);
    try {
      const response = await listAdminStaff<{
        data: { items: SupportAssignee[]; next_cursor?: string | null };
      }>(request, { status: "active", limit: 50 });
      const candidates = response.data.items.filter(
        (item) => item.status === "active" && ASSIGNABLE_STAFF_ROLES.has(item.staff_role)
      );
      setSupportAssignees(candidates);
      setSupportAssigneesTruncated(Boolean(response.data.next_cursor));
      setSupportAssigneesLoaded(true);
      setNotice(
        candidates.length > 0
          ? "Responsables activos cargados."
          : "No hay responsables activos disponibles para asignar."
      );
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "No pudimos cargar responsables activos.");
    } finally {
      supportAssigneesLoadingRef.current = false;
      setSupportAssigneesLoading(false);
    }
  }, [adminMutable, request, setNotice]);

  const assignSupportTicket = useCallback(async () => {
    if (!adminMutable || !selectedSupportTicket || ARCHIVED_SUPPORT_STATUSES.has(selectedSupportTicket.status)) {
      return;
    }
    if (!supportAssigneeUserId) {
      setNotice("Selecciona un responsable activo.");
      return;
    }
    const reason = supportAssignmentReason.trim();
    if (!reason) {
      setNotice("Escribe un motivo breve para la asignacion.");
      return;
    }
    if (supportAssignmentInFlight.current) {
      return;
    }
    const ticketId = selectedSupportTicket.id;
    const assigneeUserId = supportAssigneeUserId;
    const idempotencyScope = `admin_support_assign_${ticketId}`;
    supportAssignmentInFlight.current = true;
    setAssigningSupportTicketId(ticketId);
    try {
      const ticket = await adminAssignSupportTicket(
        request,
        ticketId,
        assigneeUserId,
        reason,
        getIdempotencyKey(idempotencyScope, { ticketId, assigneeUserId, reason })
      );
      clearIdempotencyKey(idempotencyScope);
      setSelectedSupportTicket((current) => (current?.id === ticketId ? ticket : current));
      setSupportTickets((items) => items.map((item) => (item.id === ticketId ? ticket : item)));
      setSupportAssignmentReason("");
      setNotice("Responsable actualizado.");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "No pudimos asignar el ticket.");
    } finally {
      supportAssignmentInFlight.current = false;
      setAssigningSupportTicketId(null);
    }
  }, [
    adminMutable,
    clearIdempotencyKey,
    getIdempotencyKey,
    request,
    selectedSupportTicket,
    setNotice,
    supportAssigneeUserId,
    supportAssignmentReason
  ]);

  const refreshSelectedSupportTicket = useCallback(async () => {
    if (!selectedSupportTicket) {
      return;
    }
    const ticket = await adminGetSupportTicket(request, selectedSupportTicket.id);
    selectSupportTicket(ticket);
  }, [request, selectedSupportTicket, selectSupportTicket]);

  const replySupportTicket = useCallback(async () => {
    if (!selectedSupportTicket || !supportReply.trim() || supportReplyInFlight.current) {
      return;
    }
    const ticketId = selectedSupportTicket.id;
    const body = supportReply.trim();
    const optimisticMessage = buildOptimisticSupportMessage(selectedSupportTicket, body);
    supportReplyInFlight.current = true;
    setSendingSupportReply(true);
    setBusy(true);
    const idempotencyScope = `admin_support_msg_${ticketId}`;
    try {
      clearSupportReplyDraft(ticketId);
      setSelectedSupportTicket((current) => (current?.id === ticketId ? appendSupportMessage(current, optimisticMessage) : current));
      const payload = await adminSendSupportMessage(request, ticketId, body, getIdempotencyKey(idempotencyScope, { ticketId, body }));
      clearIdempotencyKey(idempotencyScope);
      clearSupportReplyDraft(ticketId);
      setSelectedSupportTicket((current) => (current?.id === ticketId ? applySupportMessageResult(current, optimisticMessage.id, payload.message, payload.ticket) : current));
      setSupportTickets((items) => items.map((item) => (item.id === payload.ticket.id ? payload.ticket : item)));
      setNotice("");
    } catch (error) {
      setSelectedSupportTicket((current) => (current?.id === ticketId ? removeSupportMessage(current, optimisticMessage.id) : current));
      setSupportReplyDraft(ticketId, body);
      if (selectedSupportTicketIdRef.current === ticketId) {
        setNotice(error instanceof Error ? `${error.message}. Tu texto sigue listo para reintentar.` : "No pudimos confirmar el envio. Tu texto sigue listo para reintentar.");
      } else {
        setNotice(error instanceof Error ? `${error.message}. Ocurrio en la conversacion anterior.` : "No pudimos confirmar el envio en la conversacion anterior.");
      }
    } finally {
      supportReplyInFlight.current = false;
      setSendingSupportReply(false);
      setBusy(false);
    }
  }, [clearIdempotencyKey, clearSupportReplyDraft, getIdempotencyKey, request, selectedSupportTicket, setBusy, setNotice, setSupportReplyDraft, supportReply]);

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
        selectSupportTicket(null);
        setSupportTickets((items) => items.filter((item) => item.id !== ticket.id));
        setNotice(archivedTicketNotice(ticket.status));
        return;
      }
      selectSupportTicket(ticket);
      setSupportTickets((items) => items.map((item) => (item.id === ticket.id ? ticket : item)));
      setNotice(archivedTicketNotice(ticket.status));
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "No pudimos actualizar el ticket.");
    } finally {
      setBusy(false);
    }
  }, [clearIdempotencyKey, getIdempotencyKey, request, selectedSupportTicket, selectSupportTicket, setBusy, setNotice]);

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
    supportAssignees,
    supportAssigneesLoaded,
    supportAssigneesLoading,
    supportAssigneesTruncated,
    supportAssigneeUserId,
    setSupportAssigneeUserId,
    selectedSupportHasAssignee: Boolean(selectedSupportTicket?.assigned_support_user_id),
    supportAssignmentReason,
    setSupportAssignmentReason,
    assigningSupportTicketId,
    loadSupportTickets,
    refreshSupportWorkspace,
    openSupportTicket,
    refreshSelectedSupportTicket,
    replySupportTicket,
    loadSupportAssignees,
    assignSupportTicket,
    changeSupportStatus,
    openSupportAttachment
  };
}
