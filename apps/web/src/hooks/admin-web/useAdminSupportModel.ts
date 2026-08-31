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
import type {
  AdminBusinessPublicationHold,
  AdminStaffSummary,
  AdminSupportTicket
} from "../../types/admin";
import type { SupportMessage, SupportTicket } from "../../types/support";
import { appendUniqueById } from "../pagination";
import { useStableIdempotencyKeys } from "../useStableIdempotencyKeys";
import type { AdminWebView, RequestFn } from "./adminWebTypes";
import { useAdminPublicationHoldModel } from "./useAdminPublicationHoldModel";
import type { AdminPollingResultGuard } from "./useVisibleAdminPolling";
import { mergeSupportTicketPage } from "../supportDetailPagination";

type SupportAttachmentLink = {
  url: string;
  downloadFilename: string;
  expiresInSeconds: number;
};

const ACTIVE_SUPPORT_STATUSES = new Set<SupportTicket["status"]>(["open", "waiting_support", "waiting_user", "escalated"]);
const ARCHIVED_SUPPORT_STATUSES = new Set<SupportTicket["status"]>(["resolved", "closed"]);
const ASSIGNABLE_STAFF_ROLES = new Set(["support_agent", "support_lead", "admin", "super_admin"]);
const ADMIN_SUPPORT_TICKET_PAGE_SIZE = 20;
const ADMIN_SUPPORT_ASSIGNEE_LIMIT = 20;

function supportTicketsQuery(filter: string, cursor?: string | null): string {
  const normalized = filter.trim().toLowerCase();
  const params = new URLSearchParams({ limit: String(ADMIN_SUPPORT_TICKET_PAGE_SIZE) });
  if (normalized === "active" || normalized === "archived") {
    params.set("status_group", normalized);
  } else if (normalized && normalized !== "all") {
    params.set("status", normalized);
  }
  if (cursor) {
    params.set("cursor", cursor);
  }
  return `?${params.toString()}`;
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
  queueCriticalAction,
  request,
  setBusy,
  setNotice,
  setView
}: {
  adminMutable: boolean;
  queueCriticalAction: (
    title: string,
    detail: string,
    run: () => Promise<void>,
    options?: { requiresReason?: boolean }
  ) => void;
  request: RequestFn;
  setBusy: (busy: boolean) => void;
  setNotice: (notice: string) => void;
  setView: (view: AdminWebView) => void;
}) {
  const [supportTickets, setSupportTickets] = useState<AdminSupportTicket[]>([]);
  const [supportTicketsNextCursor, setSupportTicketsNextCursor] = useState<string | null>(null);
  const [supportTicketsLoadingMore, setSupportTicketsLoadingMore] = useState(false);
  const [supportMessagesLoadingMore, setSupportMessagesLoadingMore] = useState(false);
  const [selectedSupportTicket, setSelectedSupportTicket] = useState<AdminSupportTicket | null>(null);
  const [supportFilter, setSupportFilter] = useState("active");
  const [supportReplyDrafts, setSupportReplyDrafts] = useState<Record<string, string>>({});
  const [supportAttachmentLink, setSupportAttachmentLink] = useState<SupportAttachmentLink | null>(null);
  const [sendingSupportReply, setSendingSupportReply] = useState(false);
  const [supportAssignees, setSupportAssignees] = useState<AdminStaffSummary[]>([]);
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
  const supportRequestEpoch = useRef(0);
  const foregroundSupportRequests = useRef(0);
  const supportLoadedPageCountRef = useRef(1);
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

  const selectSupportTicket = useCallback((ticket: AdminSupportTicket | null) => {
    selectedSupportTicketIdRef.current = ticket?.id ?? null;
    setSelectedSupportTicket(ticket);
  }, []);

  const loadSupportTickets = useCallback(async (filter = supportFilter) => {
    foregroundSupportRequests.current += 1;
    const requestEpoch = ++supportRequestEpoch.current;
    const isLatest = () => requestEpoch === supportRequestEpoch.current;
    setSupportTicketsLoadingMore(false);
    setBusy(true);
    try {
      const normalizedFilter = filter.trim().toLowerCase() || "active";
      const payload = await adminListSupportTickets(request, supportTicketsQuery(normalizedFilter));
      if (!isLatest()) {
        return;
      }
      setSupportTickets(filterSupportTickets(payload.items, normalizedFilter));
      setSupportTicketsNextCursor(payload.next_cursor);
      supportLoadedPageCountRef.current = 1;
      if (selectedSupportTicket && normalizedFilter === "active" && ARCHIVED_SUPPORT_STATUSES.has(selectedSupportTicket.status)) {
        selectSupportTicket(null);
      }
      setSupportFilter(normalizedFilter);
      setView("support");
      setNotice("");
    } catch (error) {
      if (isLatest()) {
        setSupportTicketsNextCursor(null);
        setNotice(error instanceof Error ? error.message : "No pudimos cargar soporte.");
      }
    } finally {
      foregroundSupportRequests.current = Math.max(0, foregroundSupportRequests.current - 1);
      setBusy(false);
    }
  }, [request, selectedSupportTicket, selectSupportTicket, setBusy, setNotice, setView, supportFilter]);

  const refreshSupportWorkspace = useCallback(async (shouldApply: AdminPollingResultGuard = () => true) => {
    if (foregroundSupportRequests.current > 0) {
      return;
    }
    const requestEpoch = ++supportRequestEpoch.current;
    const isLatest = () => requestEpoch === supportRequestEpoch.current && shouldApply();
    const normalizedFilter = supportFilter.trim().toLowerCase() || "active";
    try {
      const payload = await adminListSupportTickets(request, supportTicketsQuery(normalizedFilter));
      if (!isLatest()) {
        return;
      }
      const firstPage = filterSupportTickets(payload.items, normalizedFilter);
      setSupportTickets((current) => (
        supportLoadedPageCountRef.current > 1
          ? appendUniqueById(firstPage, current.slice(ADMIN_SUPPORT_TICKET_PAGE_SIZE))
          : firstPage
      ));
      if (supportLoadedPageCountRef.current === 1) {
        setSupportTicketsNextCursor(payload.next_cursor);
      }
      if (selectedSupportTicket) {
        const ticket = await adminGetSupportTicket(request, selectedSupportTicket.id);
        if (!isLatest()) {
          return;
        }
        if (normalizedFilter === "active" && ARCHIVED_SUPPORT_STATUSES.has(ticket.status)) {
          selectSupportTicket(null);
          return;
        }
        setSelectedSupportTicket((current) => {
          const merged = current?.id === ticket.id
            ? mergeSupportTicketPage(current, ticket, { preserveHistoryCursor: true })
            : ticket;
          selectedSupportTicketIdRef.current = merged.id;
          return merged;
        });
      }
    } catch {
      // Background refresh should not interrupt the operator's current action.
    }
  }, [request, selectedSupportTicket, selectSupportTicket, supportFilter]);

  const loadMoreSupportTickets = useCallback(async () => {
    const cursor = supportTicketsNextCursor;
    if (!cursor || supportTicketsLoadingMore) {
      return;
    }
    foregroundSupportRequests.current += 1;
    const requestEpoch = ++supportRequestEpoch.current;
    const normalizedFilter = supportFilter.trim().toLowerCase() || "active";
    setSupportTicketsLoadingMore(true);
    try {
      const payload = await adminListSupportTickets(request, supportTicketsQuery(normalizedFilter, cursor));
      if (requestEpoch !== supportRequestEpoch.current) {
        return;
      }
      setSupportTickets((current) => appendUniqueById(current, filterSupportTickets(payload.items, normalizedFilter)));
      setSupportTicketsNextCursor(payload.next_cursor);
      supportLoadedPageCountRef.current += 1;
    } catch (error) {
      if (requestEpoch === supportRequestEpoch.current) {
        setNotice(error instanceof Error ? error.message : "No pudimos cargar mas tickets.");
      }
    } finally {
      foregroundSupportRequests.current = Math.max(0, foregroundSupportRequests.current - 1);
      if (requestEpoch === supportRequestEpoch.current) {
        setSupportTicketsLoadingMore(false);
      }
    }
  }, [request, setNotice, supportFilter, supportTicketsLoadingMore, supportTicketsNextCursor]);

  const openSupportTicket = useCallback(async (ticketId: string) => {
    foregroundSupportRequests.current += 1;
    const requestEpoch = ++supportRequestEpoch.current;
    const isLatest = () => requestEpoch === supportRequestEpoch.current;
    setBusy(true);
    try {
      const ticket = await adminGetSupportTicket(request, ticketId);
      if (!isLatest()) {
        return;
      }
      selectSupportTicket(ticket);
      setSupportAssigneeUserId("");
      setSupportAssignmentReason("");
      setSupportAttachmentLink(null);
      setView("support");
      setNotice("");
    } catch (error) {
      if (isLatest()) {
        setNotice(error instanceof Error ? error.message : "No pudimos abrir el ticket.");
      }
    } finally {
      foregroundSupportRequests.current = Math.max(0, foregroundSupportRequests.current - 1);
      setBusy(false);
    }
  }, [request, selectSupportTicket, setBusy, setNotice, setView]);

  const loadMoreSupportMessages = useCallback(async () => {
    const ticket = selectedSupportTicket;
    const cursor = ticket?.messages_next_cursor;
    if (!ticket || !cursor || supportMessagesLoadingMore) {
      return;
    }
    foregroundSupportRequests.current += 1;
    const requestEpoch = ++supportRequestEpoch.current;
    setSupportMessagesLoadingMore(true);
    try {
      const olderPage = await adminGetSupportTicket(request, ticket.id, { messagesCursor: cursor });
      if (requestEpoch !== supportRequestEpoch.current || selectedSupportTicketIdRef.current !== ticket.id) {
        return;
      }
      setSelectedSupportTicket((current) => (
        current?.id === ticket.id ? mergeSupportTicketPage(current, olderPage) : current
      ));
    } catch (error) {
      if (requestEpoch === supportRequestEpoch.current) {
        setNotice(error instanceof Error ? error.message : "No pudimos cargar mensajes anteriores.");
      }
    } finally {
      foregroundSupportRequests.current = Math.max(0, foregroundSupportRequests.current - 1);
      if (requestEpoch === supportRequestEpoch.current) {
        setSupportMessagesLoadingMore(false);
      }
    }
  }, [request, selectedSupportTicket, setNotice, supportMessagesLoadingMore]);

  const loadSupportAssignees = useCallback(async () => {
    if (!adminMutable || supportAssigneesLoadingRef.current) {
      return;
    }
    supportAssigneesLoadingRef.current = true;
    setSupportAssigneesLoading(true);
    try {
      const response = await listAdminStaff(request, { status: "active", limit: ADMIN_SUPPORT_ASSIGNEE_LIMIT });
      const candidates = response.items.filter(
        (item) => item.status === "active" && ASSIGNABLE_STAFF_ROLES.has(item.staff_role)
      );
      setSupportAssignees(candidates);
      setSupportAssigneesTruncated(Boolean(response.next_cursor));
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
      setSelectedSupportTicket((current) => (
        current?.id === ticketId
          ? mergeSupportTicketPage(current, ticket, { preserveHistoryCursor: true })
          : current
      ));
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

  const refreshSupportTicket = useCallback(async (ticketId: string) => {
    foregroundSupportRequests.current += 1;
    const requestEpoch = ++supportRequestEpoch.current;
    const isLatest = () => requestEpoch === supportRequestEpoch.current;
    try {
      const ticket = await adminGetSupportTicket(request, ticketId);
      if (!isLatest()) {
        return;
      }
      setSupportTickets((items) => items.map((item) => (item.id === ticketId ? ticket : item)));
      if (selectedSupportTicketIdRef.current === ticketId) {
        setSelectedSupportTicket((current) => {
          const merged = current?.id === ticket.id
            ? mergeSupportTicketPage(current, ticket, { preserveHistoryCursor: true })
            : ticket;
          selectedSupportTicketIdRef.current = merged.id;
          return merged;
        });
      }
    } finally {
      foregroundSupportRequests.current = Math.max(0, foregroundSupportRequests.current - 1);
    }
  }, [request, selectSupportTicket]);

  const refreshSelectedSupportTicket = useCallback(async () => {
    const ticketId = selectedSupportTicketIdRef.current;
    if (!ticketId) {
      return;
    }
    await refreshSupportTicket(ticketId);
  }, [refreshSupportTicket]);

  const applyReleasedHold = useCallback((ticketId: string, hold: AdminBusinessPublicationHold) => {
    setSupportTickets((items) => items.map((item) => (
      item.id === ticketId ? { ...item, publication_hold: hold } : item
    )));
    if (selectedSupportTicketIdRef.current === ticketId) {
      setSelectedSupportTicket((current) => (
        current?.id === ticketId ? { ...current, publication_hold: hold } : current
      ));
    }
  }, []);

  const publicationHold = useAdminPublicationHoldModel({
    adminMutable,
    applyReleasedHold,
    queueCriticalAction,
    refreshTicket: refreshSupportTicket,
    request,
    selectedTicket: selectedSupportTicket
  });

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
    supportTicketsLoadingMore,
    supportMessagesLoadingMore,
    supportTicketsNextCursor,
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
    ...publicationHold,
    loadSupportTickets,
    loadMoreSupportTickets,
    loadMoreSupportMessages,
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
