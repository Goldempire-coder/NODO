"use client";

import { useCallback, useState } from "react";
import { createSupportTicket, getSupportTicket, listSupportTickets, sendSupportMessage, uploadSupportAttachment } from "../api/support";
import type { SupportTicket, SupportTicketCategory, SupportTicketCreateInput, SupportTicketScope } from "../types/support";
import type { AuthenticatedRequest } from "../api/client";

const DEFAULT_CATEGORY: SupportTicketCategory = "technical_issue";

export function useSurfaceSupportModel({
  request,
  setBusy,
  setNotice
}: {
  request: AuthenticatedRequest;
  setBusy: (busy: boolean) => void;
  setNotice: (notice: string) => void;
}) {
  void setBusy;
  const [supportTickets, setSupportTickets] = useState<SupportTicket[]>([]);
  const [selectedSupportTicket, setSelectedSupportTicket] = useState<SupportTicket | null>(null);
  const [supportReply, setSupportReply] = useState("");
  const [supportForm, setSupportForm] = useState<SupportTicketCreateInput>({
    scope: "client_general",
    category: DEFAULT_CATEGORY,
    subject: "",
    message: ""
  });
  const [creatingSupportTicket, setCreatingSupportTicket] = useState(false);
  const [loadingSupportTickets, setLoadingSupportTickets] = useState(false);
  const [openingSupportTicketId, setOpeningSupportTicketId] = useState<string | null>(null);
  const [sendingSupportReply, setSendingSupportReply] = useState(false);
  const [uploadingSupportAttachment, setUploadingSupportAttachment] = useState(false);

  const loadSupportTickets = useCallback(async () => {
    setLoadingSupportTickets(true);
    try {
      const payload = await listSupportTickets(request);
      setSupportTickets(payload.items);
      setNotice("");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "No pudimos cargar soporte.");
    } finally {
      setLoadingSupportTickets(false);
    }
  }, [request, setNotice]);

  const openSupportTicket = useCallback(async (ticketId: string) => {
    setOpeningSupportTicketId(ticketId);
    try {
      const ticket = await getSupportTicket(request, ticketId);
      setSelectedSupportTicket(ticket);
      setNotice("");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "No pudimos abrir el ticket.");
    } finally {
      setOpeningSupportTicketId(null);
    }
  }, [request, setNotice]);

  const submitSupportTicket = useCallback(async (input?: Partial<SupportTicketCreateInput>) => {
    setCreatingSupportTicket(true);
    try {
      const ticket = await createSupportTicket(request, { ...supportForm, ...(input || {}) });
      setSelectedSupportTicket(ticket);
      setSupportTickets((current) => [ticket, ...current.filter((item) => item.id !== ticket.id)]);
      setSupportForm((current) => ({ ...current, subject: "", message: "" }));
      setNotice("Ticket enviado a soporte.");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "No pudimos crear el ticket.");
    } finally {
      setCreatingSupportTicket(false);
    }
  }, [request, setNotice, supportForm]);

  const submitSupportReply = useCallback(async () => {
    if (!selectedSupportTicket || !supportReply.trim()) {
      return;
    }
    setSendingSupportReply(true);
    try {
      await sendSupportMessage(request, selectedSupportTicket.id, supportReply);
      const ticket = await getSupportTicket(request, selectedSupportTicket.id);
      setSelectedSupportTicket(ticket);
      setSupportReply("");
      setNotice("");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "No pudimos enviar el mensaje.");
    } finally {
      setSendingSupportReply(false);
    }
  }, [request, selectedSupportTicket, setNotice, supportReply]);

  const uploadTicketAttachment = useCallback(async (file: File | null) => {
    if (!selectedSupportTicket || !file) {
      return;
    }
    setUploadingSupportAttachment(true);
    try {
      await uploadSupportAttachment(request, selectedSupportTicket.id, file);
      const ticket = await getSupportTicket(request, selectedSupportTicket.id);
      setSelectedSupportTicket(ticket);
      setNotice("Adjunto guardado de forma privada.");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "No pudimos subir el adjunto.");
    } finally {
      setUploadingSupportAttachment(false);
    }
  }, [request, selectedSupportTicket, setNotice]);

  const setSupportScope = useCallback((scope: SupportTicketScope) => {
    setSupportForm((current) => ({ ...current, scope }));
  }, []);

  return {
    creatingSupportTicket,
    loadingSupportTickets,
    openingSupportTicketId,
    supportTickets,
    selectedSupportTicket,
    setSelectedSupportTicket,
    supportForm,
    setSupportForm,
    supportReply,
    setSupportReply,
    setSupportScope,
    sendingSupportReply,
    loadSupportTickets,
    openSupportTicket,
    submitSupportTicket,
    submitSupportReply,
    uploadTicketAttachment,
    uploadingSupportAttachment
  };
}
