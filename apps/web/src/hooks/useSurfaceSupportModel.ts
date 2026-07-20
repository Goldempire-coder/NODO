"use client";

import { useCallback, useState } from "react";
import { createSupportTicket, getSupportTicket, listSupportTickets, sendSupportMessage, uploadSupportAttachment } from "../api/support";
import type { SupportTicket, SupportTicketCategory, SupportTicketCreateInput, SupportTicketScope } from "../types/support";
import type { AuthenticatedRequest } from "../api/client";
import { actionStartedAt, recordActionCompleted, recordActionFailed, recordActionStarted } from "./actionTelemetry";
import { useStableIdempotencyKeys } from "./useStableIdempotencyKeys";

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

function supportTicketsQuery(filter: SupportTicketListFilter): string {
  void filter;
  return "?limit=50";
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
  const [loadingSupportTickets, setLoadingSupportTickets] = useState(false);
  const [openingSupportTicketId, setOpeningSupportTicketId] = useState<string | null>(null);
  const [sendingSupportReply, setSendingSupportReply] = useState(false);
  const [uploadingSupportAttachment, setUploadingSupportAttachment] = useState(false);
  const { clearIdempotencyKey, getIdempotencyKey } = useStableIdempotencyKeys();

  const loadSupportTickets = useCallback(async (filter: SupportTicketListFilter = supportFilter) => {
    const startedAt = actionStartedAt();
    recordActionStarted("support_tickets_load", "support");
    setLoadingSupportTickets(true);
    try {
      const normalizedFilter = normalizeSupportFilter(filter);
      const payload = await listSupportTickets(request, supportTicketsQuery(normalizedFilter));
      setSupportTickets(filterSupportTickets(payload.items, normalizedFilter));
      if (selectedSupportTicket && normalizedFilter === "active" && ARCHIVED_SUPPORT_STATUSES.has(selectedSupportTicket.status)) {
        setSelectedSupportTicket(null);
      }
      setSupportFilter(normalizedFilter);
      setNotice("");
      recordActionCompleted("support_tickets_load", "support", startedAt);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "No pudimos cargar soporte.");
      recordActionFailed("support_tickets_load", "support", startedAt, error instanceof Error ? error.name : undefined);
    } finally {
      setLoadingSupportTickets(false);
    }
  }, [request, selectedSupportTicket, setNotice, supportFilter]);

  const refreshSupportWorkspace = useCallback(async () => {
    const normalizedFilter = normalizeSupportFilter(supportFilter);
    try {
      const payload = await listSupportTickets(request, supportTicketsQuery(normalizedFilter));
      setSupportTickets(filterSupportTickets(payload.items, normalizedFilter));
      if (selectedSupportTicket) {
        const ticket = await getSupportTicket(request, selectedSupportTicket.id);
        if (normalizedFilter === "active" && ARCHIVED_SUPPORT_STATUSES.has(ticket.status)) {
          setSelectedSupportTicket(null);
          return;
        }
        setSelectedSupportTicket(ticket);
      }
    } catch {
      // Background refresh should not interrupt the user's current action.
    }
  }, [request, selectedSupportTicket, supportFilter]);

  const openSupportTicket = useCallback(async (ticketId: string) => {
    const startedAt = actionStartedAt();
    recordActionStarted("support_ticket_open", "support");
    setOpeningSupportTicketId(ticketId);
    try {
      const ticket = await getSupportTicket(request, ticketId);
      setSelectedSupportTicket(ticket);
      setNotice("");
      recordActionCompleted("support_ticket_open", "support", startedAt);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "No pudimos abrir el ticket.");
      recordActionFailed("support_ticket_open", "support", startedAt, error instanceof Error ? error.name : undefined);
    } finally {
      setOpeningSupportTicketId(null);
    }
  }, [request, setNotice]);

  const submitSupportTicket = useCallback(async (input?: Partial<SupportTicketCreateInput>) => {
    const startedAt = actionStartedAt();
    recordActionStarted("support_ticket_create", "support");
    setCreatingSupportTicket(true);
    const payload = { ...supportForm, ...(input || {}) };
    const idempotencyScope = `support_ticket_${payload.scope}`;
    try {
      const ticket = await createSupportTicket(request, payload, getIdempotencyKey(idempotencyScope, payload));
      clearIdempotencyKey(idempotencyScope);
      setSelectedSupportTicket(ticket);
      setSupportFilter("active");
      setSupportTickets((current) => [ticket, ...current.filter((item) => item.id !== ticket.id)]);
      setSupportForm((current) => ({ ...current, subject: "", message: "" }));
      setNotice("Ticket enviado a soporte.");
      recordActionCompleted("support_ticket_create", "support", startedAt);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "No pudimos crear el ticket.");
      recordActionFailed("support_ticket_create", "support", startedAt, error instanceof Error ? error.name : undefined);
    } finally {
      setCreatingSupportTicket(false);
    }
  }, [clearIdempotencyKey, getIdempotencyKey, request, setNotice, supportForm]);

  const submitSupportReply = useCallback(async () => {
    if (!selectedSupportTicket || !supportReply.trim()) {
      return;
    }
    const startedAt = actionStartedAt();
    recordActionStarted("support_reply_send", "support");
    setSendingSupportReply(true);
    const idempotencyScope = `support_msg_${selectedSupportTicket.id}`;
    const body = supportReply.trim();
    try {
      await sendSupportMessage(request, selectedSupportTicket.id, body, getIdempotencyKey(idempotencyScope, { ticketId: selectedSupportTicket.id, body }));
      clearIdempotencyKey(idempotencyScope);
      setSupportReply("");
      try {
        const ticket = await getSupportTicket(request, selectedSupportTicket.id);
        setSelectedSupportTicket(ticket);
        setSupportTickets((current) => {
          if (!ticketBelongsToFilter(ticket, supportFilter)) {
            return current.filter((item) => item.id !== ticket.id);
          }
          const rest = current.filter((item) => item.id !== ticket.id);
          return [ticket, ...rest];
        });
        setNotice("");
      } catch {
        setNotice("Mensaje enviado. No pudimos refrescar la conversacion automaticamente.");
      }
      recordActionCompleted("support_reply_send", "support", startedAt);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "No pudimos enviar el mensaje.");
      recordActionFailed("support_reply_send", "support", startedAt, error instanceof Error ? error.name : undefined);
    } finally {
      setSendingSupportReply(false);
    }
  }, [clearIdempotencyKey, getIdempotencyKey, request, selectedSupportTicket, setNotice, supportReply]);

  const uploadTicketAttachment = useCallback(async (file: File | null) => {
    if (!selectedSupportTicket || !file) {
      return;
    }
    const startedAt = actionStartedAt();
    recordActionStarted("support_attachment_upload", "support");
    setUploadingSupportAttachment(true);
    const idempotencyScope = `support_file_${selectedSupportTicket.id}`;
    try {
      await uploadSupportAttachment(request, selectedSupportTicket.id, file, getIdempotencyKey(idempotencyScope, { ticketId: selectedSupportTicket.id, name: file.name, size: file.size }));
      clearIdempotencyKey(idempotencyScope);
      const ticket = await getSupportTicket(request, selectedSupportTicket.id);
      setSelectedSupportTicket(ticket);
      setNotice("Adjunto guardado de forma privada.");
      recordActionCompleted("support_attachment_upload", "support", startedAt);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "No pudimos subir el adjunto.");
      recordActionFailed("support_attachment_upload", "support", startedAt, error instanceof Error ? error.name : undefined);
    } finally {
      setUploadingSupportAttachment(false);
    }
  }, [clearIdempotencyKey, getIdempotencyKey, request, selectedSupportTicket, setNotice]);

  const setSupportScope = useCallback((scope: SupportTicketScope) => {
    setSupportForm((current) => ({ ...current, scope }));
  }, []);

  return {
    creatingSupportTicket,
    loadingSupportTickets,
    openingSupportTicketId,
    supportTickets,
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
    loadSupportTickets,
    refreshSupportWorkspace,
    openSupportTicket,
    submitSupportTicket,
    submitSupportReply,
    uploadTicketAttachment,
    uploadingSupportAttachment
  };
}
