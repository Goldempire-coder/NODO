import { useEffect, useRef, useState } from "react";
import { Button, Text, Title } from "@telegram-apps/telegram-ui";
import type { BusinessMiniAppModel } from "../../hooks/useBusinessMiniAppModel";
import { humanizeSenderRole } from "../../hooks/business-mini-app/helpers";

const BUSINESS_SUPPORT_REFRESH_MS = 5000;

function supportStatusLabel(status: string): string {
  const labels: Record<string, string> = {
    open: "Soporte revisa",
    waiting_support: "Soporte revisa",
    waiting_user: "Esperando tu respuesta",
    escalated: "En revision",
    resolved: "Archivado",
    closed: "Archivado"
  };
  return labels[status] || status;
}

function supportCategoryLabel(category: string): string {
  const labels: Record<string, string> = {
    technical_issue: "Problema tecnico",
    business_access: "Acceso negocio",
    credits_help: "Creditos",
    order_help: "Orden",
    other: "Otro"
  };
  return labels[category] || category;
}

function supportSenderLabel(senderRole: string): string {
  if (senderRole === "business_owner") {
    return "Tu";
  }
  if (senderRole === "admin" || senderRole === "support" || senderRole === "super_admin") {
    return "Soporte NODO";
  }
  return humanizeSenderRole(senderRole);
}

function supportTimestamp(value: string | null): string {
  if (!value) {
    return "Sin mensajes";
  }
  return new Date(value).toLocaleString();
}

export function BusinessSupportScreen({ model }: { model: BusinessMiniAppModel }) {
  const {
    creatingSupportTicket,
    loadingSupportFilter,
    loadingSupportTickets,
    loadSupportTickets,
    openSupportTicket,
    openingSupportTicketId,
    refreshSupportWorkspace,
    selectedSupportTicket,
    sendingSupportReply,
    setSelectedSupportTicket,
    setSupportForm,
    supportForm,
    supportFilter,
    supportReply,
    supportTickets,
    setSupportReply,
    submitSupportReply,
    submitSupportTicket,
    uploadingSupportAttachment,
    uploadTicketAttachment
  } = model;
  const [showNewConversation, setShowNewConversation] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  const ticketMessages = selectedSupportTicket?.messages || [];
  const selectedArchived = selectedSupportTicket?.status === "resolved" || selectedSupportTicket?.status === "closed";
  const emptyCopy = supportFilter === "archived" ? "No tienes conversaciones archivadas." : "No tienes conversaciones activas.";

  useEffect(() => {
    void loadSupportTickets("active");
  }, [loadSupportTickets]);

  useEffect(() => {
    const interval = window.setInterval(() => {
      void refreshSupportWorkspace();
    }, BUSINESS_SUPPORT_REFRESH_MS);
    return () => window.clearInterval(interval);
  }, [refreshSupportWorkspace]);

  useEffect(() => {
    if (selectedSupportTicket) {
      setShowNewConversation(false);
    }
  }, [selectedSupportTicket]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ block: "end" });
  }, [selectedSupportTicket?.id, ticketMessages.length]);

  const startNewConversation = () => {
    setSelectedSupportTicket(null);
    setSupportReply("");
    setShowNewConversation(true);
    if (supportFilter !== "active") {
      void loadSupportTickets("active");
    }
  };

  const returnToConversationList = () => {
    setSelectedSupportTicket(null);
    setSupportReply("");
    setShowNewConversation(false);
  };

  const selectFilter = (filter: "active" | "archived") => {
    setSelectedSupportTicket(null);
    setSupportReply("");
    setShowNewConversation(false);
    void loadSupportTickets(filter);
  };

  return (
    <section className="business-support" aria-label="Soporte NODO">
      <header className="business-support__header">
        <div>
          <Text className="business-card__label">Ayuda para tu negocio</Text>
          <Title level="3" className="business-shell__title">Soporte NODO</Title>
        </div>
        {!showNewConversation ? (
          <Button mode="outline" size="s" type="button" disabled={creatingSupportTicket} onClick={startNewConversation}>
            Nueva conversacion
          </Button>
        ) : null}
      </header>

      {showNewConversation && !selectedSupportTicket ? (
        <form
          className="business-support-new"
          onSubmit={(event) => {
            event.preventDefault();
            void submitSupportTicket();
          }}
        >
          <div className="business-support-new__heading">
            <div>
              <Text className="business-card__label">Nuevo tema</Text>
              <strong>Cuéntanos que necesitas</strong>
            </div>
            <Button mode="outline" size="s" type="button" disabled={creatingSupportTicket} onClick={returnToConversationList}>Cancelar</Button>
          </div>
          <div className="business-grid">
            <label className="business-field">
              <span>Tipo</span>
              <select disabled={creatingSupportTicket} value={supportForm.scope} onChange={(event) => setSupportForm((current) => ({ ...current, scope: event.target.value as typeof supportForm.scope }))}>
                <option value="business_general">Soporte general</option>
                <option value="business_order">Orden</option>
                <option value="business_ad">Anuncio</option>
                <option value="business_credit">Creditos</option>
              </select>
            </label>
            <label className="business-field">
              <span>Categoria</span>
              <select disabled={creatingSupportTicket} value={supportForm.category} onChange={(event) => setSupportForm((current) => ({ ...current, category: event.target.value as typeof supportForm.category }))}>
                <option value="technical_issue">Problema tecnico</option>
                <option value="business_access">Acceso negocio</option>
                <option value="credits_help">Creditos</option>
                <option value="order_help">Orden</option>
                <option value="other">Otro</option>
              </select>
            </label>
          </div>
          <label className="business-field">
            <span>Asunto</span>
            <input disabled={creatingSupportTicket} maxLength={140} value={supportForm.subject} onChange={(event) => setSupportForm((current) => ({ ...current, subject: event.target.value }))} />
          </label>
          <label className="business-field">
            <span>Mensaje</span>
            <textarea disabled={creatingSupportTicket} maxLength={2000} rows={4} value={supportForm.message} onChange={(event) => setSupportForm((current) => ({ ...current, message: event.target.value }))} />
          </label>
          <Button mode="filled" size="s" type="submit" disabled={creatingSupportTicket || loadingSupportTickets || supportForm.subject.trim().length < 3 || supportForm.message.trim().length < 3}>
            {creatingSupportTicket ? "Creando..." : "Crear conversacion"}
          </Button>
        </form>
      ) : null}

      {selectedSupportTicket ? (
        <div className="business-support-thread">
          <div className="business-support-thread__header">
            <button className="business-support-back" type="button" aria-label="Volver a conversaciones" onClick={returnToConversationList}>
              <span aria-hidden="true">&larr;</span>
            </button>
            <div>
              <Title level="3" className="business-shell__title">{selectedSupportTicket.subject}</Title>
              <span className={selectedArchived ? "business-support-status business-support-status--archived" : "business-support-status"}>
                {supportStatusLabel(selectedSupportTicket.status)}
              </span>
            </div>
          </div>

          <div className="business-support-messages" aria-label="Mensajes de soporte" aria-live="polite">
            {ticketMessages.length === 0 ? <Text>Aun no hay mensajes en esta conversacion.</Text> : null}
            {ticketMessages.map((message) => {
              const isMine = message.sender_role === "business_owner";
              return (
                <article className={isMine ? "business-support-message business-support-message--mine" : "business-support-message"} key={message.id}>
                  <span>{supportSenderLabel(message.sender_role)}</span>
                  <p>{message.body}</p>
                  {message.attachments?.length ? <small>{message.attachments.length} adjunto(s)</small> : null}
                  <small>{supportTimestamp(message.created_at)}</small>
                </article>
              );
            })}
            <div ref={messagesEndRef} />
          </div>

          {selectedArchived ? (
            <div className="business-support-archived-note">
              <strong>Conversacion archivada</strong>
              <span>Puedes consultar el historial, pero este caso ya no recibe respuestas.</span>
            </div>
          ) : (
            <div className="business-support-composer">
              <textarea
                aria-label="Mensaje para Soporte NODO"
                disabled={sendingSupportReply}
                maxLength={2000}
                placeholder="Escribe un mensaje"
                rows={2}
                value={supportReply}
                onChange={(event) => setSupportReply(event.target.value)}
              />
              <div className="business-support-composer__actions">
                <label className="business-support-attachment">
                  <span>{uploadingSupportAttachment ? "Subiendo..." : "Adjuntar"}</span>
                  <input accept="image/jpeg,image/png,image/webp,application/pdf" disabled={uploadingSupportAttachment || sendingSupportReply} type="file" onChange={(event) => void uploadTicketAttachment(event.target.files?.[0] || null)} />
                </label>
                <Button mode="filled" size="s" disabled={sendingSupportReply || uploadingSupportAttachment || !supportReply.trim()} onClick={() => void submitSupportReply()}>
                  {sendingSupportReply ? "Enviando..." : "Enviar"}
                </Button>
              </div>
            </div>
          )}
        </div>
      ) : null}

      {!selectedSupportTicket && !showNewConversation ? (
        <>
          <div className="business-support-tabs" role="tablist" aria-label="Conversaciones de soporte">
            <button className={supportFilter === "active" ? "is-active" : ""} type="button" role="tab" aria-selected={supportFilter === "active"} disabled={loadingSupportFilter === "active"} onClick={() => selectFilter("active")}>
              {loadingSupportFilter === "active" ? "Cargando..." : "Activas"}
            </button>
            <button className={supportFilter === "archived" ? "is-active" : ""} type="button" role="tab" aria-selected={supportFilter === "archived"} disabled={loadingSupportFilter === "archived"} onClick={() => selectFilter("archived")}>
              {loadingSupportFilter === "archived" ? "Cargando..." : "Archivadas"}
            </button>
          </div>

          <div className="business-support-ticket-list" aria-busy={loadingSupportTickets}>
            {supportTickets.length === 0 && !loadingSupportTickets ? <Text className="business-support-empty">{emptyCopy}</Text> : null}
            {supportTickets.map((ticket) => (
              <button className="business-support-ticket" disabled={openingSupportTicketId === ticket.id} key={ticket.id} type="button" onClick={() => void openSupportTicket(ticket.id)}>
                <span className={ticket.status === "resolved" || ticket.status === "closed" ? "business-support-status business-support-status--archived" : "business-support-status"}>
                  {supportStatusLabel(ticket.status)}
                </span>
                <strong>{ticket.subject}</strong>
                <small>{openingSupportTicketId === ticket.id ? "Abriendo..." : `${supportCategoryLabel(ticket.category)} - ${supportTimestamp(ticket.last_message_at || ticket.updated_at)}`}</small>
              </button>
            ))}
          </div>
        </>
      ) : null}
    </section>
  );
}
