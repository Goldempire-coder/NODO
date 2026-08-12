"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { closeSupportTicket, createSupportTicket, getSupportTicket, listSupportTickets, sendSupportMessage, uploadSupportAttachment } from "../api/support";
import type { SupportMessage, SupportTicket, SupportTicketCategory, SupportTicketCreateInput, SupportTicketScope } from "../types/support";
import type { AuthenticatedRequest } from "../api/client";
import { actionStartedAt, recordActionCompleted, recordActionFailed, recordActionStarted } from "./actionTelemetry";
import { appendUniqueById } from "./pagination";
import { useStableIdempotencyKeys } from "./useStableIdempotencyKeys";
import type { SurfacePollingResultGuard } from "./useVisibleSurfacePolling";

const DEFAULT_CATEGORY: SupportTicketCategory = "technical_issue";
const ACTIVE_SUPPORT_STATUSES = new Set<SupportTicket["status"]>(["open", "waiting_support", "waiting_user", "escalated"]);
const ARCHIVED_SUPPORT_STATUSES = new Set<SupportTicket["status"]>(["resolved", "closed"]);

export type SupportTicketListFilter = "active" | "archived" | "all";

function normalizeSupportFilter(filter?: string): SupportTicketListFilter {
  const normalized = filter?.trim().toLowerCase();
  if (normalized === "archived" || normalized === "all") {
    return normalized;
  }
  return "active";
}

function supportTicketsQuery(filter: SupportTicketListFilter, cursor?: string | null): string {
  const params = new URLSearchParams({ limit: "50" });
  if (filter === "active" || filter === "archived") {
    params.set("status_group", filter);
  }
  if (cursor) {
    params.set("cursor", cursor);
  }
  return `?${params.toString()}`;
}

function filterSupportTickets(items: SupportTicket[], filter: SupportTicketListFilter): SupportTicket[] {
  if (filter === "active") {
    return items.filter((ticket) => ACTIVE_SUPPORT_STATUSES.has(ticket.status));
  }
  if (filter === "archived") {
    return items.filter((ticket) => ARCHIVED_SUPPORT_STATUSES.has(ticket.status));
  }
  return items;
}

function ticketBelongsToFilter(ticket: SupportTicket, filter: SupportTicketListFilter): boolean {
  return filterSupportTickets([ticket], filter).length === 1;
}

function applySupportMessageResult(ticket: SupportTicket, message: SupportMessage, summary: SupportTicket): SupportTicket {
  const messages = (ticket.messages || []).filter((item) => item.id !== message.id);
  return {
    ...ticket,
    ...summary,
    attachments: ticket.attachments,
    events: ticket.events,
    messages: [...messages, message],
    disclaimer: ticket.disclaimer
  };
}

function normalizeSupportTopic(value: string): string {
  return value.trim().replace(/\s+/g, " ").toLowerCase();
}

function findMatchingActiveTicket(tickets: SupportTicket[], input: SupportTicketCreateInput): SupportTicket | undefined {
  const subject = normalizeSupportTopic(input.subject);
  return tickets.find(
    (ticket) =>
      ACTIVE_SUPPORT_STATUSES.has(ticket.status) &&
      ticket.scope === input.scope &&
      ticket.category === input.category &&
      ticket.order_id === (input.order_id || null) &&
      ticket.ad_id === (input.ad_id || null) &&
      ticket.credit_purchase_id === (input.credit_purchase_id || null) &&
      normalizeSupportTopic(ticket.subject) === subject
  );
}

export function useSurfaceSupportModel({
  initialScope = "client_general",
  request,
  setBusy,
  setNotice
}: {
  initialScope?: SupportTicketScope;
  request: AuthenticatedRequest;
  setBusy: (busy: boolean) => void;
  setNotice: (notice: string) => void;
}) {
  void setBusy;
  const [supportTickets, setSupportTickets] = useState<SupportTicket[]>([]);
  const [supportTicketsNextCursor, setSupportTicketsNextCursor] = useState<string | null>(null);
  const [supportTicketsLoadingMore, setSupportTicketsLoadingMore] = useState(false);
  const [selectedSupportTicket, setSelectedSupportTicket] = useState<SupportTicket | null>(null);
  const [supportFilter, setSupportFilter] = useState<SupportTicketListFilter>("active");
  const [supportReply, setSupportReply] = useState("");
  const [supportForm, setSupportForm] = useState<SupportTicketCreateInput>({
    scope: initialScope,
    category: DEFAULT_CATEGORY,
    subject: "",
    message: ""
  });
  const [creatingSupportTicket, setCreatingSupportTicket] = useState(false);
  const [loadingSupportFilter, setLoadingSupportFilter] = useState<SupportTicketListFilter | null>(null);
  const [openingSupportTicketId, setOpeningSupportTicketId] = useState<string | null>(null);
  const [sendingSupportReply, setSendingSupportReply] = useState(false);
  const [uploadingSupportAttachment, setUploadingSupportAttachment] = useState(false);
  const [closingSupportTicketId, setClosingSupportTicketId] = useState<string | null>(null);
  const supportFilterRef = useRef<SupportTicketListFilter>("active");
  const selectedSupportTicketRef = useRef<SupportTicket | null>(null);
  const creatingTicketLockRef = useRef(false);
  const openingTicketLockRef = useRef<string | null>(null);
  const sendingReplyLockRef = useRef(false);
  const uploadingAttachmentLockRef = useRef(false);
  const closingTicketLockRef = useRef<string | null>(null);
  const listRequestIdRef = useRef(0);
  const supportRefreshEpochRef = useRef(0);
  const supportRefreshInFlightRef = useRef<Promise<void> | null>(null);
  const supportLoadedPageCountRef = useRef(1);
  const { clearIdempotencyKey, getIdempotencyKey } = useStableIdempotencyKeys();

  useEffect(() => {
    supportFilterRef.current = supportFilter;
  }, [supportFilter]);

  useEffect(() => {
    selectedSupportTicketRef.current = selectedSupportTicket;
  }, [selectedSupportTicket]);

  const loadSupportTickets = useCallback(async (filter?: SupportTicketListFilter) => {
    supportRefreshEpochRef.current += 1;
    setSupportTicketsLoadingMore(false);
    const requestId = listRequestIdRef.current + 1;
    listRequestIdRef.current = requestId;
    const startedAt = actionStartedAt();
    recordActionStarted("support_tickets_load", "support");
    const normalizedFilter = normalizeSupportFilter(filter || supportFilterRef.current);
    supportFilterRef.current = normalizedFilter;
    setSupportFilter(normalizedFilter);
    setLoadingSupportFilter(normalizedFilter);
    try {
      const payload = await listSupportTickets(request, supportTicketsQuery(normalizedFilter));
      if (requestId !== listRequestIdRef.current) {
        recordActionCompleted("support_tickets_load", "support", startedAt);
        return;
      }
      setSupportTickets(filterSupportTickets(payload.items, normalizedFilter));
      setSupportTicketsNextCursor(payload.next_cursor);
      supportLoadedPageCountRef.current = 1;
      setSelectedSupportTicket((current) => {
        if (!current || normalizedFilter !== "active") {
          return current;
        }
        const latestSelected = payload.items.find((item) => item.id === current.id) || current;
        return ARCHIVED_SUPPORT_STATUSES.has(latestSelected.status) ? null : current;
      });
      setNotice("");
      recordActionCompleted("support_tickets_load", "support", startedAt);
    } catch (error) {
      if (requestId !== listRequestIdRef.current) {
        recordActionFailed("support_tickets_load", "support", startedAt, error instanceof Error ? error.name : undefined);
        return;
      }
      setNotice(error instanceof Error ? error.message : "No pudimos cargar soporte.");
      recordActionFailed("support_tickets_load", "support", startedAt, error instanceof Error ? error.name : undefined);
    } finally {
      if (requestId === listRequestIdRef.current) {
        setLoadingSupportFilter(null);
      }
    }
  }, [request, setNotice]);

  const loadMoreSupportTickets = useCallback(async () => {
    const cursor = supportTicketsNextCursor;
    if (!cursor || supportTicketsLoadingMore) {
      return;
    }
    const requestId = listRequestIdRef.current + 1;
    listRequestIdRef.current = requestId;
    supportRefreshEpochRef.current += 1;
    const normalizedFilter = normalizeSupportFilter(supportFilterRef.current);
    setSupportTicketsLoadingMore(true);
    try {
      const payload = await listSupportTickets(request, supportTicketsQuery(normalizedFilter, cursor));
      if (requestId !== listRequestIdRef.current || supportFilterRef.current !== normalizedFilter) {
        return;
      }
      setSupportTickets((current) => appendUniqueById(current, filterSupportTickets(payload.items, normalizedFilter)));
      setSupportTicketsNextCursor(payload.next_cursor);
      supportLoadedPageCountRef.current += 1;
    } catch (error) {
      if (requestId === listRequestIdRef.current) {
        setNotice(error instanceof Error ? error.message : "No pudimos cargar mas tickets.");
      }
    } finally {
      if (requestId === listRequestIdRef.current) {
        setSupportTicketsLoadingMore(false);
      }
    }
  }, [request, setNotice, supportTicketsLoadingMore, supportTicketsNextCursor]);

  const performSupportRefresh = useCallback(async (shouldApply?: SurfacePollingResultGuard) => {
    const epoch = ++supportRefreshEpochRef.current;
    const normalizedFilter = normalizeSupportFilter(supportFilterRef.current);
    const currentTicket = selectedSupportTicketRef.current;
    const isLatest = () => (
      epoch === supportRefreshEpochRef.current
      && supportFilterRef.current === normalizedFilter
      && (shouldApply?.() ?? true)
    );
    try {
      const payload = await listSupportTickets(request, supportTicketsQuery(normalizedFilter));
      if (!isLatest()) {
        return;
      }
      const firstPage = filterSupportTickets(payload.items, normalizedFilter);
      setSupportTickets((current) => (
        supportLoadedPageCountRef.current > 1
          ? appendUniqueById(firstPage, current.slice(50))
          : firstPage
      ));
      if (supportLoadedPageCountRef.current === 1) {
        setSupportTicketsNextCursor(payload.next_cursor);
      }
      if (currentTicket) {
        const ticket = await getSupportTicket(request, currentTicket.id);
        if (!isLatest() || selectedSupportTicketRef.current?.id !== currentTicket.id) {
          return;
        }
        if (normalizedFilter === "active" && ARCHIVED_SUPPORT_STATUSES.has(ticket.status)) {
          setSelectedSupportTicket(null);
          return;
        }
        setSelectedSupportTicket(ticket);
      }
    } catch {
      // Background refresh should not interrupt the user's current action.
    }
  }, [request]);

  const refreshSupportWorkspace = useCallback(async function runSupportRefresh(shouldApply?: SurfacePollingResultGuard): Promise<void> {
    if (supportRefreshInFlightRef.current) {
      const inFlight = supportRefreshInFlightRef.current;
      if (shouldApply) {
        return inFlight;
      }
      supportRefreshEpochRef.current += 1;
      await inFlight;
      return runSupportRefresh();
    }
    const refresh = performSupportRefresh(shouldApply).finally(() => {
      if (supportRefreshInFlightRef.current === refresh) {
        supportRefreshInFlightRef.current = null;
      }
    });
    supportRefreshInFlightRef.current = refresh;
    await refresh;
  }, [performSupportRefresh]);

  const openSupportTicket = useCallback(async (ticketId: string) => {
    if (openingTicketLockRef.current) {
      return false;
    }
    openingTicketLockRef.current = ticketId;
    const startedAt = actionStartedAt();
    recordActionStarted("support_ticket_open", "support");
    setOpeningSupportTicketId(ticketId);
    try {
      const ticket = await getSupportTicket(request, ticketId);
      setSelectedSupportTicket(ticket);
      setSupportReply("");
      setNotice("");
      recordActionCompleted("support_ticket_open", "support", startedAt);
      return true;
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "No pudimos abrir el ticket.");
      recordActionFailed("support_ticket_open", "support", startedAt, error instanceof Error ? error.name : undefined);
      return false;
    } finally {
      openingTicketLockRef.current = null;
      setOpeningSupportTicketId(null);
    }
  }, [request, setNotice]);

  const submitSupportTicket = useCallback(async (input?: Partial<SupportTicketCreateInput>) => {
    if (creatingTicketLockRef.current) {
      return;
    }
    creatingTicketLockRef.current = true;
    const startedAt = actionStartedAt();
    recordActionStarted("support_ticket_create", "support");
    setCreatingSupportTicket(true);
    const payload = { ...supportForm, ...(input || {}) };
    const idempotencyScope = `support_ticket_${payload.scope}`;
    try {
      const existingTicket = findMatchingActiveTicket(supportTickets, payload);
      if (existingTicket) {
        const ticket = await getSupportTicket(request, existingTicket.id);
        setSelectedSupportTicket(ticket);
        supportFilterRef.current = "active";
        setSupportFilter("active");
        setSupportForm((current) => ({ ...current, subject: "", message: "" }));
        setNotice("Ya existe una conversacion activa para este tema.");
        recordActionCompleted("support_ticket_create", "support", startedAt);
        return;
      }
      const ticket = await createSupportTicket(request, payload, getIdempotencyKey(idempotencyScope, payload));
      clearIdempotencyKey(idempotencyScope);
      setSelectedSupportTicket(ticket);
      supportFilterRef.current = "active";
      setSupportFilter("active");
      setSupportTickets((current) => [
        ticket,
        ...current.filter((item) => item.id !== ticket.id && ACTIVE_SUPPORT_STATUSES.has(item.status))
      ]);
      setSupportTicketsNextCursor(null);
      supportLoadedPageCountRef.current = 1;
      setSupportForm((current) => ({ ...current, subject: "", message: "" }));
      setNotice("Ticket enviado a soporte.");
      recordActionCompleted("support_ticket_create", "support", startedAt);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "No pudimos crear el ticket.");
      recordActionFailed("support_ticket_create", "support", startedAt, error instanceof Error ? error.name : undefined);
    } finally {
      creatingTicketLockRef.current = false;
      setCreatingSupportTicket(false);
    }
  }, [clearIdempotencyKey, getIdempotencyKey, request, setNotice, supportForm, supportTickets]);

  const submitSupportReply = useCallback(async () => {
    if (sendingReplyLockRef.current) {
      return;
    }
    if (!selectedSupportTicket || !supportReply.trim() || ARCHIVED_SUPPORT_STATUSES.has(selectedSupportTicket.status)) {
      return;
    }
    sendingReplyLockRef.current = true;
    const startedAt = actionStartedAt();
    recordActionStarted("support_reply_send", "support");
    setSendingSupportReply(true);
    const idempotencyScope = `support_msg_${selectedSupportTicket.id}`;
    const body = supportReply.trim();
    try {
      const payload = await sendSupportMessage(request, selectedSupportTicket.id, body, getIdempotencyKey(idempotencyScope, { ticketId: selectedSupportTicket.id, body }));
      clearIdempotencyKey(idempotencyScope);
      if (selectedSupportTicketRef.current?.id === selectedSupportTicket.id) {
        setSupportReply("");
      }
      setSelectedSupportTicket((current) => (current?.id === selectedSupportTicket.id ? applySupportMessageResult(current, payload.message, payload.ticket) : current));
      setSupportTickets((current) => {
        if (!ticketBelongsToFilter(payload.ticket, supportFilterRef.current)) {
          return current.filter((item) => item.id !== payload.ticket.id);
        }
        const rest = current.filter((item) => item.id !== payload.ticket.id);
        return [payload.ticket, ...rest];
      });
      setNotice("");
      recordActionCompleted("support_reply_send", "support", startedAt);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "No pudimos enviar el mensaje. Tu texto sigue listo para reintentar.");
      recordActionFailed("support_reply_send", "support", startedAt, error instanceof Error ? error.name : undefined);
    } finally {
      sendingReplyLockRef.current = false;
      setSendingSupportReply(false);
    }
  }, [clearIdempotencyKey, getIdempotencyKey, request, selectedSupportTicket, setNotice, supportReply]);

  const uploadTicketAttachment = useCallback(async (file: File | null) => {
    if (uploadingAttachmentLockRef.current || !selectedSupportTicket || !file || ARCHIVED_SUPPORT_STATUSES.has(selectedSupportTicket.status)) {
      return;
    }
    uploadingAttachmentLockRef.current = true;
    const startedAt = actionStartedAt();
    recordActionStarted("support_attachment_upload", "support");
    setUploadingSupportAttachment(true);
    const idempotencyScope = `support_file_${selectedSupportTicket.id}`;
    try {
      const payload = await uploadSupportAttachment(request, selectedSupportTicket.id, file, getIdempotencyKey(idempotencyScope, { ticketId: selectedSupportTicket.id, name: file.name, size: file.size }));
      clearIdempotencyKey(idempotencyScope);
      setSelectedSupportTicket((current) => (current?.id === selectedSupportTicket.id ? applySupportMessageResult(current, payload.message, payload.ticket) : current));
      setSupportTickets((current) => {
        if (!ticketBelongsToFilter(payload.ticket, supportFilterRef.current)) {
          return current.filter((item) => item.id !== payload.ticket.id);
        }
        const rest = current.filter((item) => item.id !== payload.ticket.id);
        return [payload.ticket, ...rest];
      });
      setNotice("Adjunto enviado a Soporte NODO.");
      recordActionCompleted("support_attachment_upload", "support", startedAt);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "No pudimos subir el adjunto.");
      recordActionFailed("support_attachment_upload", "support", startedAt, error instanceof Error ? error.name : undefined);
    } finally {
      uploadingAttachmentLockRef.current = false;
      setUploadingSupportAttachment(false);
    }
  }, [clearIdempotencyKey, getIdempotencyKey, request, selectedSupportTicket, setNotice]);

  const closeOwnSupportTicket = useCallback(async () => {
    const ticket = selectedSupportTicketRef.current;
    if (!ticket || closingTicketLockRef.current || !ACTIVE_SUPPORT_STATUSES.has(ticket.status)) {
      return;
    }
    closingTicketLockRef.current = ticket.id;
    setClosingSupportTicketId(ticket.id);
    const startedAt = actionStartedAt();
    recordActionStarted("support_ticket_close", "support");
    const idempotencyScope = `support_close_${ticket.id}`;
    try {
      const closedTicket = await closeSupportTicket(
        request,
        ticket.id,
        getIdempotencyKey(idempotencyScope, { ticketId: ticket.id, action: "close_by_requester" })
      );
      clearIdempotencyKey(idempotencyScope);
      supportFilterRef.current = "archived";
      setSupportFilter("archived");
      setSelectedSupportTicket((current) => (current?.id === ticket.id ? closedTicket : current));
      setSupportTickets((current) => [
        closedTicket,
        ...current.filter((item) => item.id !== closedTicket.id && ARCHIVED_SUPPORT_STATUSES.has(item.status))
      ]);
      setSupportTicketsNextCursor(null);
      supportLoadedPageCountRef.current = 1;
      setSupportReply("");
      setNotice("Conversacion cerrada y enviada a Archivados.");
      recordActionCompleted("support_ticket_close", "support", startedAt);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "No pudimos cerrar la conversacion.");
      recordActionFailed("support_ticket_close", "support", startedAt, error instanceof Error ? error.name : undefined);
    } finally {
      closingTicketLockRef.current = null;
      setClosingSupportTicketId(null);
    }
  }, [clearIdempotencyKey, getIdempotencyKey, request, setNotice]);

  const setSupportScope = useCallback((scope: SupportTicketScope) => {
    setSupportForm((current) => ({ ...current, scope }));
  }, []);

  return {
    creatingSupportTicket,
    loadingSupportFilter,
    loadingSupportTickets: loadingSupportFilter !== null,
    openingSupportTicketId,
    supportTickets,
    supportTicketsLoadingMore,
    supportTicketsNextCursor,
    supportFilter,
    setSupportFilter,
    selectedSupportTicket,
    setSelectedSupportTicket,
    supportForm,
    setSupportForm,
    supportReply,
    setSupportReply,
    setSupportScope,
    sendingSupportReply,
    closingSupportTicketId,
    loadSupportTickets,
    loadMoreSupportTickets,
    refreshSupportWorkspace,
    openSupportTicket,
    submitSupportTicket,
    submitSupportReply,
    closeOwnSupportTicket,
    uploadTicketAttachment,
    uploadingSupportAttachment
  };
}
