import type { Ref } from "react";
import { useRef } from "react";
import { Button, Text } from "@telegram-apps/telegram-ui";
import { PaperclipIcon, SendIcon } from "../../components/nodo/ChatComposerIcons";
import type { SupportTicket } from "../../types/support";

const SUPPORT_STATUS_LABELS: Record<string, string> = {
  open: "Soporte revisa",
  waiting_support: "Soporte revisa",
  escalated: "En revision",
  resolved: "Archivado",
  closed: "Archivado"
};

const SUPPORT_CATEGORY_LABELS: Record<string, string> = {
  technical_issue: "Problema tecnico",
  account_access: "Acceso",
  business_access: "Acceso negocio",
  credits_help: "Creditos",
  order_help: "Orden",
  payment_report_help: "Pago",
  suspicious_activity: "Actividad sospechosa",
  other: "Otro"
};

function supportStatusLabel(status: string, waitingUserLabel: string): string {
  return status === "waiting_user" ? waitingUserLabel : SUPPORT_STATUS_LABELS[status] || status.replaceAll("_", " ");
}

function supportCategoryLabel(category: string): string {
  return SUPPORT_CATEGORY_LABELS[category] || category.replaceAll("_", " ");
}

function supportSenderLabel(senderRole: string, ownRole: string): string {
  if (senderRole === ownRole) {
    return "Tu";
  }
  if (senderRole === "admin" || senderRole === "support" || senderRole === "super_admin") {
    return "Soporte NODO";
  }
  const labels: Record<string, string> = { remitter: "Cliente", business_owner: "Negocio" };
  return labels[senderRole] || senderRole.replaceAll("_", " ");
}

function supportTimestamp(value: string | null): string {
  return value ? new Date(value).toLocaleString() : "Sin mensajes";
}

function RefreshIcon() {
  return (
    <svg aria-hidden="true" className="surface-support-icon-svg" focusable="false" viewBox="0 0 24 24">
      <path d="M21 12a9 9 0 0 1-15.1 6.6" />
      <path d="M3 12A9 9 0 0 1 18.1 5.4" />
      <path d="M18 2v4h-4" />
      <path d="M6 22v-4h4" />
    </svg>
  );
}

export function SurfaceSupportComposer({
  reply,
  sending,
  uploading,
  onReplyChange,
  onSend,
  onUpload
}: {
  reply: string;
  sending: boolean;
  uploading: boolean;
  onReplyChange: (value: string) => void;
  onSend: () => void;
  onUpload: (file: File | null) => void;
}) {
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  return (
    <form
      className="surface-support-composer"
      onSubmit={(event) => {
        event.preventDefault();
        onSend();
      }}
    >
      <button
        className="surface-support-clip"
        type="button"
        aria-label="Adjuntar archivo"
        disabled={uploading || sending}
        onClick={() => fileInputRef.current?.click()}
      >
        <PaperclipIcon />
      </button>
      <textarea
        className="surface-support-composer__input"
        aria-label="Mensaje para Soporte NODO"
        disabled={sending}
        maxLength={2000}
        placeholder={uploading ? "Subiendo adjunto..." : "Escribir respuesta..."}
        rows={1}
        value={reply}
        onChange={(event) => onReplyChange(event.target.value)}
      />
      <input
        ref={fileInputRef}
        className="surface-support-file-input"
        accept="image/jpeg,image/png,image/webp"
        disabled={uploading || sending}
        type="file"
        onChange={(event) => {
          const file = event.currentTarget.files?.[0] || null;
          event.currentTarget.value = "";
          onUpload(file);
        }}
      />
      <button className="surface-support-send" type="submit" aria-label="Enviar" disabled={sending || uploading || !reply.trim()}>
        {sending ? "..." : <SendIcon />}
      </button>
    </form>
  );
}

export function SurfaceSupportThread({
  archivedBody,
  archivedTitle,
  closing,
  emptyMessagesCopy,
  messagesEndRef,
  loadingOlderMessages,
  notice,
  ownRole,
  reply,
  sending,
  ticket,
  uploading,
  waitingUserLabel,
  onClose,
  onLoadOlderMessages,
  onReplyChange,
  onSend,
  onUpload
}: {
  archivedBody: string;
  archivedTitle: string;
  closing: boolean;
  emptyMessagesCopy: string;
  messagesEndRef: Ref<HTMLDivElement>;
  loadingOlderMessages: boolean;
  notice: string;
  ownRole: "remitter" | "business_owner";
  reply: string;
  sending: boolean;
  ticket: SupportTicket;
  uploading: boolean;
  waitingUserLabel: string;
  onClose: () => void;
  onLoadOlderMessages: () => void;
  onReplyChange: (value: string) => void;
  onSend: () => void;
  onUpload: (file: File | null) => void;
}) {
  const archived = ticket.status === "resolved" || ticket.status === "closed";
  const messages = ticket.messages || [];
  return (
    <div className="surface-support-thread">
      <div className="surface-support-messages" aria-label="Mensajes de soporte" aria-live="polite">
        <article className="surface-support-message surface-support-message--system surface-support-system-bubble">
          <span className="surface-support-message__sender">Soporte NODO</span>
          <p>{ticket.subject}</p>
          <small>Conversacion de soporte</small>
          <span className={archived ? "surface-support-status surface-support-status--archived" : "surface-support-status"}>
            {supportStatusLabel(ticket.status, waitingUserLabel)}
          </span>
          {!archived ? (
            <button className="mini-action-button" type="button" disabled={closing} onClick={onClose}>
              {closing ? "Cerrando..." : ownRole === "remitter" ? "Cerrar ticket" : "Cerrar conversacion"}
            </button>
          ) : null}
        </article>
        {ticket.messages_next_cursor ? (
          <button className="mini-action-button" type="button" disabled={loadingOlderMessages} onClick={onLoadOlderMessages}>
            {loadingOlderMessages ? "Cargando..." : "Cargar mensajes anteriores"}
          </button>
        ) : null}
        {messages.length === 0 ? <Text>{emptyMessagesCopy}</Text> : null}
        {messages.map((message) => (
          <article className={message.sender_role === ownRole ? "surface-support-message surface-support-message--mine" : "surface-support-message"} key={message.id}>
            <span className="surface-support-message__sender">{supportSenderLabel(message.sender_role, ownRole)}</span>
            <p>{message.body}</p>
            {message.attachments?.length ? <small>{message.attachments.length} adjunto(s)</small> : null}
            <small>{supportTimestamp(message.created_at)}</small>
          </article>
        ))}
        {archived ? (
          <div className="surface-support-archived-note">
            <strong>{archivedTitle}</strong>
            <span>{archivedBody}</span>
          </div>
        ) : null}
        {notice ? <div className="native-chat-inline-notice" role="status"><span>{notice}</span></div> : null}
        <div ref={messagesEndRef} />
      </div>
      {!archived ? (
        <SurfaceSupportComposer
          reply={reply}
          sending={sending}
          uploading={uploading}
          onReplyChange={onReplyChange}
          onSend={onSend}
          onUpload={onUpload}
        />
      ) : null}
    </div>
  );
}

export function SurfaceSupportInbox({
  activeLabel,
  archivedLabel,
  collectionLabel,
  conversationLabel,
  creating,
  emptyCopy,
  filter,
  loading,
  loadingMore,
  nextCursor,
  openingTicketId,
  tickets,
  waitingUserLabel,
  onFilterChange,
  onLoadMore,
  onNew,
  onOpen,
  onRefresh
}: {
  activeLabel: string;
  archivedLabel: string;
  collectionLabel: string;
  conversationLabel: string;
  creating: boolean;
  emptyCopy: string;
  filter: "active" | "archived";
  loading: boolean;
  loadingMore: boolean;
  nextCursor: string | null;
  openingTicketId: string | null;
  tickets: SupportTicket[];
  waitingUserLabel: string;
  onFilterChange: (filter: "active" | "archived") => void;
  onLoadMore: () => void;
  onNew: () => void;
  onOpen: (ticketId: string) => void;
  onRefresh: () => void;
}) {
  return (
    <div className="surface-support-inbox">
      <div className="surface-support-inbox__actions">
        <label className="surface-support-thread-selector">
          <span>Ver {collectionLabel}</span>
          <select aria-label={`Ver ${collectionLabel}`} disabled={loading} value={filter} onChange={(event) => onFilterChange(event.target.value as "active" | "archived")}>
            <option value="active">{activeLabel}</option>
            <option value="archived">{archivedLabel}</option>
          </select>
        </label>
        <div className="surface-support-inbox__buttons">
          <button className="surface-support-icon-button" type="button" aria-label={`Actualizar ${collectionLabel}`} onClick={onRefresh}>
            <RefreshIcon />
          </button>
          <Button className="surface-support-new-button" mode="outline" size="s" type="button" disabled={creating} onClick={onNew}>
            Nuevo
          </Button>
        </div>
      </div>
      <small className="surface-support-inbox__hint">{conversationLabel}</small>
      <div className="surface-support-ticket-list" aria-busy={loading}>
        {tickets.length === 0 && !loading ? <Text className="surface-support-empty">{emptyCopy}</Text> : null}
        {tickets.map((ticket) => (
          <button className="surface-support-ticket" disabled={openingTicketId === ticket.id} key={ticket.id} type="button" onClick={() => onOpen(ticket.id)}>
            <span className={ticket.status === "resolved" || ticket.status === "closed" ? "surface-support-status surface-support-status--archived" : "surface-support-status"}>
              {supportStatusLabel(ticket.status, waitingUserLabel)}
            </span>
            <strong>{ticket.subject}</strong>
            <small>{openingTicketId === ticket.id ? "Abriendo conversacion..." : `${supportCategoryLabel(ticket.category)} - ${supportTimestamp(ticket.last_message_at || ticket.updated_at)}`}</small>
          </button>
        ))}
        {nextCursor ? (
          <Button mode="outline" size="s" disabled={loadingMore} onClick={onLoadMore}>
            {loadingMore ? "Cargando..." : "Cargar mas"}
          </Button>
        ) : null}
      </div>
    </div>
  );
}
