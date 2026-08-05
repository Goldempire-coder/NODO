import { Text } from "@telegram-apps/telegram-ui";
import type { ChatMessage } from "../../../types/chat";
import type { PaymentInstructions } from "../../../types/payments";

function senderLabel(senderRole: string): string {
  if (senderRole === "remitter" || senderRole === "client") {
    return "Tu";
  }
  if (senderRole === "business_owner") {
    return "Negocio";
  }
  if (senderRole === "admin" || senderRole === "support" || senderRole === "super_admin") {
    return "Soporte NODO";
  }
  return senderRole === "system" ? "NODO" : senderRole.replaceAll("_", " ");
}

function attachmentLabel(mimeType: string): string {
  if (mimeType.startsWith("image/")) {
    return "Ver imagen";
  }
  return mimeType === "application/pdf" ? "Abrir PDF" : "Abrir adjunto";
}

function attachmentMeta(mimeType: string, sizeBytes: number): string {
  const sizeKb = Math.max(1, Math.round(sizeBytes / 1024));
  if (mimeType.startsWith("image/")) {
    return `Imagen PNG/JPG - ${sizeKb} KB`;
  }
  return mimeType === "application/pdf" ? `PDF - ${sizeKb} KB` : `${sizeKb} KB`;
}

export function ClientChatMessageList({
  messages,
  paymentInstructions,
  openAttachment
}: {
  messages: ChatMessage[];
  paymentInstructions: PaymentInstructions | null;
  openAttachment: (attachmentId: string, mimeType: string) => void | Promise<void>;
}) {
  if (messages.length === 0) {
    return <Text className="business-order-chat-empty">Aun no hay mensajes en esta orden.</Text>;
  }

  return messages.map((message) => {
    const isAutomaticZelleDetails = paymentInstructions?.payment_instructions.method_type === "zelle"
      && message.sender_role === "business_owner"
      && message.body?.startsWith(
        `Zelle del negocio: ${paymentInstructions.payment_instructions.account_value}`
      );
    if (isAutomaticZelleDetails) {
      return null;
    }
    const isMine = message.sender_role === "remitter" || message.sender_role === "client";
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
        <span className="business-order-chat-message__sender">{senderLabel(message.sender_role)}</span>
        {message.body ? <p>{message.body}</p> : null}
        {message.attachments.length ? (
          <div className="business-order-chat-attachments" aria-label="Adjuntos del mensaje">
            {message.attachments.map((attachment) => (
              <button
                className="business-order-chat-attachment__button"
                type="button"
                key={attachment.id}
                onClick={() => void openAttachment(attachment.id, attachment.mime_type)}
              >
                <span>{attachmentLabel(attachment.mime_type)}</span>
                <small>{attachmentMeta(attachment.mime_type, attachment.size_bytes)}</small>
              </button>
            ))}
          </div>
        ) : null}
        <small>{new Date(message.created_at).toLocaleString()}</small>
      </article>
    );
  });
}
