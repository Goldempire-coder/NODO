import type { RefObject } from "react";
import { Text } from "@telegram-apps/telegram-ui";
import { humanizeSenderRole } from "../../../hooks/business-mini-app/helpers";
import type { ChatAttachmentLink } from "../../../hooks/business-mini-app/chat/businessChatShared";
import type { ChatCapabilities, ChatMessage } from "../../../types/chat";
import type { BusinessOrderSummary, ReceiverDetails } from "../../../types/orders";
import { BusinessReceiverDetailsBubble } from "./BusinessReceiverDetailsBubble";

function chatSenderLabel(senderRole: string): string {
  if (senderRole === "business_owner") {
    return "Tu";
  }
  if (senderRole === "remitter" || senderRole === "client") {
    return "Cliente";
  }
  if (senderRole === "admin" || senderRole === "support" || senderRole === "super_admin") {
    return "Soporte NODO";
  }
  if (senderRole === "system") {
    return "NODO";
  }
  return humanizeSenderRole(senderRole);
}

function chatTimestamp(value: string): string {
  return new Date(value).toLocaleString();
}

function attachmentLabel(mimeType: string): string {
  if (mimeType.startsWith("image/")) {
    return "Ver imagen";
  }
  if (mimeType === "application/pdf") {
    return "Abrir PDF";
  }
  return "Abrir adjunto";
}

function attachmentMeta(mimeType: string, sizeBytes: number): string {
  const sizeKb = Math.max(1, Math.round(sizeBytes / 1024));
  if (mimeType.startsWith("image/")) {
    return `Imagen PNG/JPG - ${sizeKb} KB`;
  }
  if (mimeType === "application/pdf") {
    return `PDF - ${sizeKb} KB`;
  }
  return `${sizeKb} KB`;
}

export function BusinessChatMessageList({
  orderLabel,
  currentOrder,
  chatMessages,
  chatCapabilities,
  receiverDetails,
  revealingReceiverDetails,
  chatAttachmentLink,
  attachmentCount,
  uploadingChatAttachment,
  chatRefreshError,
  notice,
  messagesEndRef,
  openChatAttachment,
  revealReceiverDetails,
  dismissChatAttachmentLink,
  refreshChat
}: {
  orderLabel: string;
  currentOrder: BusinessOrderSummary | null;
  chatMessages: ChatMessage[];
  chatCapabilities: ChatCapabilities;
  receiverDetails: ReceiverDetails | null;
  revealingReceiverDetails: boolean;
  chatAttachmentLink: ChatAttachmentLink | null;
  attachmentCount: number;
  uploadingChatAttachment: boolean;
  chatRefreshError: string;
  notice: string;
  messagesEndRef: RefObject<HTMLDivElement>;
  openChatAttachment: (attachmentId: string, mimeType?: string) => Promise<void>;
  revealReceiverDetails: () => Promise<void>;
  dismissChatAttachmentLink: () => void;
  refreshChat: (options?: { silent?: boolean }) => Promise<boolean>;
}) {
  const chatIsTerminal = currentOrder?.status === "cancelled" || currentOrder?.status === "completed";

  return (
    <div className="business-order-chat-messages" aria-label="Mensajes de la orden" aria-live="polite">
      <article className="business-order-chat-message business-order-chat-message--system business-order-chat-system-bubble">
        <span className="business-order-chat-message__sender">NODO</span>
        <p>Solicitud abierta con cliente</p>
        <strong>{orderLabel}</strong>
      </article>

      {chatMessages.length === 0 ? <Text className="business-order-chat-empty">Aun no hay mensajes en esta orden.</Text> : null}
      {chatMessages.map((message) => {
        const isMine = message.sender_role === "business_owner";
        const isSystem = message.sender_role === "system";
        return (
          <article
            className={
              isSystem
                ? "business-order-chat-message business-order-chat-message--system"
                : isMine
                  ? "business-order-chat-message business-order-chat-message--mine"
                  : "business-order-chat-message"
            }
            key={message.id}
          >
            <span className="business-order-chat-message__sender">{chatSenderLabel(message.sender_role)}</span>
            {message.body ? <p>{message.body}</p> : null}
            {message.attachments.length ? (
              <div className="business-order-chat-attachments" aria-label="Adjuntos del mensaje">
                {message.attachments.map((attachment) => (
                  <button
                    className="business-order-chat-attachment__button"
                    type="button"
                    key={attachment.id}
                    onClick={() => void openChatAttachment(attachment.id, attachment.mime_type)}
                  >
                    <span>{attachmentLabel(attachment.mime_type)}</span>
                    <small>{attachmentMeta(attachment.mime_type, attachment.size_bytes)}</small>
                  </button>
                ))}
              </div>
            ) : null}
            <small>{chatTimestamp(message.created_at)}</small>
          </article>
        );
      })}

      {currentOrder?.status === "payment_reported" ? (
        <article className="business-order-chat-message business-order-chat-message--system">
          <span className="business-order-chat-message__sender">NODO</span>
          <p>El cliente reporto un ingreso directo. Verifica solo cuando este visible en tu cuenta.</p>
        </article>
      ) : null}

      {currentOrder?.status === "payment_confirmed" && !chatCapabilities.receiver_details_shared ? (
        <Text className="auth-entry__session-meta business-order-chat-note">
          Entrega pendiente. Espera a que el cliente comparta sus datos.
        </Text>
      ) : null}

      {chatCapabilities.receiver_details_shared ? (
        <BusinessReceiverDetailsBubble
          key={currentOrder?.id ?? "receiver-details"}
          receiverDetails={receiverDetails}
          canReveal={chatCapabilities.can_reveal_receiver_details}
          revealing={revealingReceiverDetails}
          revealReceiverDetails={revealReceiverDetails}
        />
      ) : null}

      {chatAttachmentLink ? (
        <div className="business-order-chat-attachment-preview" role="status">
          <div className="business-order-chat-attachment-preview__copy">
            <strong>{chatAttachmentLink.mimeType.startsWith("image/") ? "Imagen lista" : "Adjunto listo"}</strong>
            <small>Disponible por {chatAttachmentLink.expiresInSeconds}s.</small>
          </div>
          {chatAttachmentLink.mimeType.startsWith("image/") ? (
            <a href={chatAttachmentLink.url} target="_blank" rel="noopener noreferrer" aria-label="Abrir imagen">
              <img src={chatAttachmentLink.url} alt="Vista previa del adjunto" referrerPolicy="no-referrer" />
            </a>
          ) : null}
          <div className="business-order-chat-attachment-preview__actions">
            <a href={chatAttachmentLink.url} target="_blank" rel="noopener noreferrer">
              {chatAttachmentLink.mimeType.startsWith("image/") ? "Abrir imagen" : "Abrir adjunto"}
            </a>
            <button type="button" onClick={dismissChatAttachmentLink}>Cerrar</button>
          </div>
        </div>
      ) : null}

      {attachmentCount || uploadingChatAttachment ? (
        <small className="business-order-chat-attachment-ready">
          {uploadingChatAttachment ? "Subiendo adjunto..." : `${attachmentCount} adjunto(s) listo(s) para enviar`}
        </small>
      ) : null}

      {chatIsTerminal ? (
        <Text className="auth-entry__session-meta business-order-chat-note">
          Esta orden esta cerrada. El historial queda disponible como registro de la conversacion.
        </Text>
      ) : null}

      {chatRefreshError ? (
        <div className="native-chat-inline-notice" role="alert">
          <span>{chatRefreshError}</span>
          <button type="button" onClick={() => void refreshChat()}>Actualizar</button>
        </div>
      ) : null}

      {notice ? (
        <div className="native-chat-inline-notice" role="status">
          <span>{notice}</span>
          {notice.startsWith("No ") ? <button type="button" onClick={() => void refreshChat()}>Actualizar</button> : null}
        </div>
      ) : null}
      <div ref={messagesEndRef} />
    </div>
  );
}
