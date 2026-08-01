import { useEffect, useRef, useState } from "react";
import { Button, Text } from "@telegram-apps/telegram-ui";
import { PaperclipIcon, SendIcon } from "../../components/nodo/ChatComposerIcons";
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

function supportTicketCode(id: string): string {
  return `SP-${id.slice(0, 8).toUpperCase()}`;
}

function RefreshIcon() {
  return (
    <svg aria-hidden="true" className="business-support-icon-svg" focusable="false" viewBox="0 0 24 24">
      <path d="M21 12a9 9 0 0 1-15.1 6.6" />
      <path d="M3 12A9 9 0 0 1 18.1 5.4" />
      <path d="M18 2v4h-4" />
      <path d="M6 22v-4h4" />
    </svg>
  );
}

export function BusinessSupportScreen({ model }: { model: BusinessMiniAppModel }) {
  const {
    creatingSupportTicket,
    closingSupportTicketId,
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
    closeOwnSupportTicket,
    uploadingSupportAttachment,
    uploadTicketAttachment
  } = model;
  const [showNewConversation, setShowNewConversation] = useState(false);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  const ticketMessages = selectedSupportTicket?.messages || [];
  const selectedArchived = selectedSupportTicket?.status === "resolved" || selectedSupportTicket?.status === "closed";
  const emptyCopy = supportFilter === "archived" ? "No tienes conversaciones archivadas." : "No tienes conversaciones activas.";
  const conversationLabel = loadingSupportFilter === supportFilter ? "Actualizando..." : supportFilter === "archived" ? "Archivadas" : "Activas";

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
              <strong>Cuentanos que necesitas</strong>
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
          <div className="business-support-messages" aria-label="Mensajes de soporte" aria-live="polite">
            <article className="business-support-message business-support-message--system business-support-system-bubble">
              <span className="business-support-message__sender">Soporte NODO</span>
              <p>{selectedSupportTicket.subject}</p>
              <small>Ticket #{supportTicketCode(selectedSupportTicket.id)}</small>
              <span className={selectedArchived ? "business-support-status business-support-status--archived" : "business-support-status"}>
                {supportStatusLabel(selectedSupportTicket.status)}
              </span>
              {!selectedArchived ? (
                <button
                  className="mini-action-button"
                  type="button"
                  disabled={closingSupportTicketId === selectedSupportTicket.id}
                  onClick={() => void closeOwnSupportTicket()}
                >
                  {closingSupportTicketId === selectedSupportTicket.id ? "Cerrando..." : "Cerrar conversacion"}
                </button>
              ) : null}
            </article>
            {ticketMessages.length === 0 ? <Text>Aun no hay mensajes en esta conversacion.</Text> : null}
            {ticketMessages.map((message) => {
              const isMine = message.sender_role === "business_owner";
              return (
                <article className={isMine ? "business-support-message business-support-message--mine" : "business-support-message"} key={message.id}>
                  <span className="business-support-message__sender">{supportSenderLabel(message.sender_role)}</span>
                  <p>{message.body}</p>
                  {message.attachments?.length ? <small>{message.attachments.length} adjunto(s)</small> : null}
                  <small>{supportTimestamp(message.created_at)}</small>
                </article>
              );
            })}
            {selectedArchived ? (
              <div className="business-support-archived-note">
                <strong>Conversacion archivada</strong>
                <span>Puedes consultar el historial, pero este caso ya no recibe respuestas.</span>
              </div>
            ) : null}
            {model.notice ? (
              <div className="native-chat-inline-notice" role="status">
                <span>{model.notice}</span>
                {model.notice.startsWith("No ") ? <button type="button" onClick={() => void refreshSupportWorkspace()}>Actualizar</button> : null}
              </div>
            ) : null}
            <div ref={messagesEndRef} />
          </div>

          {!selectedArchived ? (
            <form
              className="business-support-composer"
              onSubmit={(event) => {
                event.preventDefault();
                void submitSupportReply();
              }}
            >
              <button
                className="business-support-clip"
                type="button"
                aria-label="Adjuntar archivo"
                disabled={uploadingSupportAttachment || sendingSupportReply}
                onClick={() => fileInputRef.current?.click()}
              >
                <PaperclipIcon />
              </button>
              <textarea
                className="business-support-composer__input"
                aria-label="Mensaje para Soporte NODO"
                disabled={sendingSupportReply}
                maxLength={2000}
                placeholder={uploadingSupportAttachment ? "Subiendo adjunto..." : "Escribir respuesta..."}
                rows={1}
                value={supportReply}
                onChange={(event) => setSupportReply(event.target.value)}
              />
              <input
                ref={fileInputRef}
                className="business-support-file-input"
                accept="image/*,application/pdf"
                disabled={uploadingSupportAttachment || sendingSupportReply}
                type="file"
                onChange={(event) => {
                  const file = event.currentTarget.files?.[0] || null;
                  event.currentTarget.value = "";
                  void uploadTicketAttachment(file);
                }}
              />
              <button className="business-support-send" type="submit" aria-label="Enviar" disabled={sendingSupportReply || uploadingSupportAttachment || !supportReply.trim()}>
                {sendingSupportReply ? "..." : <SendIcon />}
              </button>
            </form>
          ) : null}
        </div>
      ) : null}

      {!showNewConversation && !selectedSupportTicket ? (
        <div className="business-support-inbox">
          <div className="business-support-inbox__actions">
            <label className="business-support-thread-selector">
              <span>Ver conversaciones</span>
              <select aria-label="Ver conversaciones" disabled={loadingSupportTickets} value={supportFilter} onChange={(event) => selectFilter(event.target.value as "active" | "archived")}>
                <option value="active">Activas</option>
                <option value="archived">Archivadas</option>
              </select>
            </label>
            <div className="business-support-inbox__buttons">
              <button className="business-support-icon-button" type="button" aria-label="Actualizar conversaciones" onClick={() => void refreshSupportWorkspace()}>
                <RefreshIcon />
              </button>
              <Button className="business-support-new-button" mode="outline" size="s" type="button" disabled={creatingSupportTicket} onClick={startNewConversation}>
                Nuevo
              </Button>
            </div>
          </div>
          <small className="business-support-inbox__hint">{conversationLabel}</small>

          <div className="business-support-ticket-list" aria-busy={loadingSupportTickets}>
            {supportTickets.length === 0 && !loadingSupportTickets ? <Text className="business-support-empty">{emptyCopy}</Text> : null}
            {supportTickets.map((ticket) => (
              <button className="business-support-ticket" disabled={openingSupportTicketId === ticket.id} key={ticket.id} type="button" onClick={() => void openSupportTicket(ticket.id)}>
                <span className={ticket.status === "resolved" || ticket.status === "closed" ? "business-support-status business-support-status--archived" : "business-support-status"}>
                  {supportStatusLabel(ticket.status)}
                </span>
                <strong>{ticket.subject}</strong>
                <small>#{supportTicketCode(ticket.id)} - {openingSupportTicketId === ticket.id ? "Abriendo..." : `${supportCategoryLabel(ticket.category)} - ${supportTimestamp(ticket.last_message_at || ticket.updated_at)}`}</small>
              </button>
            ))}
          </div>
        </div>
      ) : null}
    </section>
  );
}
