import { useEffect, useRef, useState } from "react";
import { Button, Text } from "@telegram-apps/telegram-ui";
import { PaperclipIcon, SendIcon } from "../../components/nodo/ChatComposerIcons";
import type { ClientWorkspaceModel } from "../../hooks/useClientWorkspaceModel";
import { humanizeSenderRole } from "../../hooks/business-mini-app/helpers";

const CLIENT_SUPPORT_REFRESH_MS = 8000;

function supportStatusLabel(status: string): string {
  const labels: Record<string, string> = {
    open: "Soporte revisa",
    waiting_support: "Soporte revisa",
    waiting_user: "Tu respuesta pendiente",
    escalated: "En revision",
    resolved: "Archivado",
    closed: "Archivado"
  };
  return labels[status] || status;
}

function supportCategoryLabel(category: string): string {
  const labels: Record<string, string> = {
    technical_issue: "Problema tecnico",
    account_access: "Acceso",
    order_help: "Orden",
    payment_report_help: "Pago",
    other: "Otro"
  };
  return labels[category] || category;
}

function supportSenderLabel(senderRole: string): string {
  if (senderRole === "remitter") {
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

export function ClientSupportScreen({ model }: { model: ClientWorkspaceModel }) {
  const {
    creatingSupportTicket,
    closingSupportTicketId,
    loadSupportTickets,
    loadingSupportTickets,
    openSupportTicket,
    openingSupportTicketId,
    refreshSupportWorkspace,
    selectedSupportTicket,
    setSelectedSupportTicket,
    setSupportForm,
    supportForm,
    supportFilter,
    supportReply,
    supportTickets,
    setSupportReply,
    sendingSupportReply,
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
  const emptyCopy = supportFilter === "archived" ? "No tienes tickets archivados." : "No tienes tickets activos.";
  const conversationLabel = loadingSupportTickets ? "Actualizando..." : supportFilter === "archived" ? "Archivados" : "Activos";

  useEffect(() => {
    void loadSupportTickets("active");
  }, [loadSupportTickets]);

  useEffect(() => {
    const interval = window.setInterval(() => {
      void refreshSupportWorkspace();
    }, CLIENT_SUPPORT_REFRESH_MS);
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
    setSupportForm((current) => ({ ...current, scope: "client_general", subject: "", message: "", order_id: null }));
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
              <Text className="business-card__label">Nuevo ticket</Text>
              <strong>Cuentanos que necesitas</strong>
            </div>
            <Button mode="outline" size="s" type="button" disabled={creatingSupportTicket} onClick={returnToConversationList}>Cancelar</Button>
          </div>
          <label className="business-field">
            <span>Categoria</span>
            <select disabled={creatingSupportTicket} value={supportForm.category} onChange={(event) => setSupportForm((current) => ({ ...current, category: event.target.value as typeof supportForm.category }))}>
              <option value="technical_issue">Problema tecnico</option>
              <option value="account_access">Acceso a cuenta</option>
              <option value="order_help">Ayuda con orden</option>
              <option value="payment_report_help">Reporte de pago</option>
              <option value="other">Otro</option>
            </select>
          </label>
          <label className="business-field">
            <span>Asunto</span>
            <input disabled={creatingSupportTicket} maxLength={140} value={supportForm.subject} onChange={(event) => setSupportForm((current) => ({ ...current, subject: event.target.value }))} />
          </label>
          <label className="business-field">
            <span>Mensaje</span>
            <textarea disabled={creatingSupportTicket} maxLength={2000} rows={4} value={supportForm.message} onChange={(event) => setSupportForm((current) => ({ ...current, message: event.target.value }))} />
          </label>
          <Text className="auth-entry__session-meta">
            Soporte revisa el caso sin cambiar automaticamente el estado de la orden o del pago.
          </Text>
          <Button mode="filled" size="s" type="submit" disabled={creatingSupportTicket || loadingSupportTickets || supportForm.subject.trim().length < 3 || supportForm.message.trim().length < 3}>
            {creatingSupportTicket ? "Creando..." : "Crear ticket"}
          </Button>
        </form>
      ) : null}

      {selectedSupportTicket ? (
        <div className="business-support-thread">
          <div className="business-support-messages" aria-label="Mensajes de soporte" aria-live="polite">
            <article className="business-support-message business-support-message--system business-support-system-bubble">
              <span className="business-support-message__sender">Soporte NODO</span>
              <p>{selectedSupportTicket.subject}</p>
              <small>Conversacion de soporte</small>
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
                  {closingSupportTicketId === selectedSupportTicket.id ? "Cerrando..." : "Cerrar ticket"}
                </button>
              ) : null}
            </article>
            {ticketMessages.length === 0 ? <Text>Aun no hay mensajes en este ticket.</Text> : null}
            {ticketMessages.map((message) => {
              const isMine = message.sender_role === "remitter";
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
                <strong>Este ticket esta archivado.</strong>
                <span>Puedes verlo cuando lo necesites, pero ya no recibe respuestas.</span>
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
              <span>Ver tickets</span>
              <select aria-label="Ver tickets" disabled={loadingSupportTickets} value={supportFilter} onChange={(event) => selectFilter(event.target.value as "active" | "archived")}>
                <option value="active">Activos</option>
                <option value="archived">Archivados</option>
              </select>
            </label>
            <div className="business-support-inbox__buttons">
              <button className="business-support-icon-button" type="button" aria-label="Actualizar tickets" onClick={() => void refreshSupportWorkspace()}>
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
                <small>{openingSupportTicketId === ticket.id ? "Abriendo conversacion..." : `${supportCategoryLabel(ticket.category)} - ${supportTimestamp(ticket.last_message_at || ticket.updated_at)}`}</small>
              </button>
            ))}
          </div>
        </div>
      ) : null}
    </section>
  );
}
