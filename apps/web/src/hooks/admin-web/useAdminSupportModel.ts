"use client";

import { useCallback, useState } from "react";
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
import type { SupportTicket } from "../../types/support";
import { useStableIdempotencyKeys } from "../useStableIdempotencyKeys";
import type { AdminWebView, RequestFn } from "./adminWebTypes";

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
  const [supportAssigneeId, setSupportAssigneeId] = useState("");
  const [supportAttachmentUrl, setSupportAttachmentUrl] = useState("");
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
    if (!selectedSupportTicket || !supportReply.trim()) {
      return;
    }
    setBusy(true);
    const idempotencyScope = `admin_support_msg_${selectedSupportTicket.id}`;
    try {
      await adminSendSupportMessage(request, selectedSupportTicket.id, supportReply, getIdempotencyKey(idempotencyScope, { ticketId: selectedSupportTicket.id, body: supportReply }));
      clearIdempotencyKey(idempotencyScope);
      setSupportReply("");
      await refreshSelectedSupportTicket();
      setNotice("");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "No pudimos responder.");
    } finally {
      setBusy(false);
    }
  }, [clearIdempotencyKey, getIdempotencyKey, refreshSelectedSupportTicket, request, selectedSupportTicket, setBusy, setNotice, supportReply]);

  const assignSupportTicket = useCallback(async (reason: string) => {
    if (!selectedSupportTicket || !supportAssigneeId.trim()) {
      return;
    }
    setBusy(true);
    const idempotencyScope = `support_assign_${selectedSupportTicket.id}`;
    try {
      const ticket = await adminAssignSupportTicket(request, selectedSupportTicket.id, supportAssigneeId, reason, getIdempotencyKey(idempotencyScope, { ticketId: selectedSupportTicket.id, supportAssigneeId, reason }));
      clearIdempotencyKey(idempotencyScope);
      setSelectedSupportTicket(ticket);
      setSupportTickets((items) => items.map((item) => (item.id === ticket.id ? ticket : item)));
      setNotice("Ticket asignado.");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "No pudimos asignar.");
    } finally {
      setBusy(false);
    }
  }, [clearIdempotencyKey, getIdempotencyKey, request, selectedSupportTicket, setBusy, setNotice, supportAssigneeId]);

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

  const openSupportAttachment = useCallback(async (fileId: string, reason: string) => {
    if (!selectedSupportTicket) {
      return;
    }
    setBusy(true);
    try {
      const payload = await adminSupportAttachmentViewUrl(request, selectedSupportTicket.id, fileId, reason);
      setSupportAttachmentUrl(payload.url);
      setNotice("URL temporal generada.");
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
    supportAssigneeId,
    setSupportAssigneeId,
    supportAttachmentUrl,
    loadSupportTickets,
    refreshSupportWorkspace,
    openSupportTicket,
    refreshSelectedSupportTicket,
    replySupportTicket,
    assignSupportTicket,
    changeSupportStatus,
    openSupportAttachment
  };
}
