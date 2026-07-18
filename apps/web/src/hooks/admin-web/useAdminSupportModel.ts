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
  const [supportFilter, setSupportFilter] = useState("");
  const [supportReply, setSupportReply] = useState("");
  const [supportAssigneeId, setSupportAssigneeId] = useState("");
  const [supportAttachmentUrl, setSupportAttachmentUrl] = useState("");
  const { clearIdempotencyKey, getIdempotencyKey } = useStableIdempotencyKeys();

  const loadSupportTickets = useCallback(async (filter = supportFilter) => {
    setBusy(true);
    try {
      const query = filter ? `?status=${encodeURIComponent(filter)}` : "";
      const payload = await adminListSupportTickets(request, query);
      setSupportTickets(payload.items);
      setSupportFilter(filter);
      setView("support");
      setNotice("");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "No pudimos cargar soporte.");
    } finally {
      setBusy(false);
    }
  }, [request, setBusy, setNotice, setView, supportFilter]);

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

  const refreshSelected = useCallback(async () => {
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
      await refreshSelected();
      setNotice("");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "No pudimos responder.");
    } finally {
      setBusy(false);
    }
  }, [clearIdempotencyKey, getIdempotencyKey, refreshSelected, request, selectedSupportTicket, setBusy, setNotice, supportReply]);

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
      setSelectedSupportTicket(ticket);
      setNotice("Ticket actualizado.");
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
    openSupportTicket,
    replySupportTicket,
    assignSupportTicket,
    changeSupportStatus,
    openSupportAttachment
  };
}
