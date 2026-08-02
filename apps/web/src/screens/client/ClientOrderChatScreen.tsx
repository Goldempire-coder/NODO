import { useEffect, useRef } from "react";
import { Text } from "@telegram-apps/telegram-ui";
import { PaperclipIcon, SendIcon } from "../../components/nodo/ChatComposerIcons";
import type { ClientWorkspaceModel } from "../../hooks/useClientWorkspaceModel";

const CLIENT_ORDER_CHAT_REFRESH_MS = 5000;

function chatSenderLabel(senderRole: string): string {
  if (senderRole === "remitter" || senderRole === "client") {
    return "Tu";
  }
  if (senderRole === "business_owner") {
    return "Negocio";
  }
  if (senderRole === "admin" || senderRole === "support" || senderRole === "super_admin") {
    return "Soporte NODO";
  }
  if (senderRole === "system") {
    return "NODO";
  }
  return senderRole.replaceAll("_", " ");
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

function orderLabel(model: ClientWorkspaceModel): string {
  if (model.selectedOrder?.id === model.chatOrderId && model.selectedOrder.public_order_code) {
    return `Orden ${model.selectedOrder.public_order_code}`;
  }
  return "Orden en curso";
}

export function ClientOrderChatScreen({ model }: { model: ClientWorkspaceModel }) {
  const {
    chatAttachments,
    chatAttachmentLink,
    chatBody,
    chatCapabilities,
    chatMessages,
    chatOrderId,
    loadingPaymentInstructions,
    openChatAttachment,
    paymentEvidence,
    paymentInstructions,
    paymentReportForm,
    confirmOrderReceived,
    confirmingOrderReceived,
    dismissChatAttachmentLink,
    refreshChat,
    sendChatMessage,
    sendingChatMessage,
    submitPaymentReport,
    submittingPaymentReport,
    setChatBody,
    setPaymentReportForm,
    uploadPaymentEvidence,
    uploadingPaymentEvidence,
    uploadChatAttachment,
    uploadingChatAttachment
  } = model;
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const paymentEvidenceInputRef = useRef<HTMLInputElement | null>(null);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  const canSend = chatCapabilities.can_send_message && !sendingChatMessage && !uploadingChatAttachment;
  const canSubmitMessage = canSend && (chatBody.trim().length > 0 || chatAttachments.length > 0);
  const selectedChatOrder = model.selectedOrder?.id === chatOrderId ? model.selectedOrder : null;
  const paymentReportMethod = paymentInstructions?.payment_instructions.method_type || selectedChatOrder?.payment_method_snapshot;
  const chatIsTerminal = selectedChatOrder?.status === "cancelled" || selectedChatOrder?.status === "completed";
  const canReportPayment = chatCapabilities.can_report_payment && selectedChatOrder?.status === "waiting_payment";
  const canConfirmReceived = chatCapabilities.can_confirm_received && selectedChatOrder?.status === "delivered";
  const hasActionDock = canConfirmReceived || (canReportPayment && Boolean(chatOrderId));

  useEffect(() => {
    if (!chatOrderId || model.view !== "order-chat") {
      return;
    }
    const interval = window.setInterval(() => {
      if (
        document.visibilityState !== "visible"
        || sendingChatMessage
        || uploadingChatAttachment
      ) {
        return;
      }
      void refreshChat({ silent: true });
    }, CLIENT_ORDER_CHAT_REFRESH_MS);
    return () => window.clearInterval(interval);
  }, [
    chatOrderId,
    model.view,
    refreshChat,
    sendingChatMessage,
    uploadingChatAttachment
  ]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ block: "end" });
  }, [chatOrderId, chatMessages.length, chatAttachments.length]);

  return (
    <section className={hasActionDock ? "business-order-chat business-order-chat--has-actions" : "business-order-chat"} aria-label="Chat con negocio">
      <div className="business-order-chat-messages" aria-label="Mensajes de la orden" aria-live="polite">
        <article className="business-order-chat-message business-order-chat-message--system business-order-chat-system-bubble">
          <span className="business-order-chat-message__sender">NODO</span>
          <p>Negociacion abierta con {selectedChatOrder?.business_name || "el negocio"}</p>
          <strong>{orderLabel(model)}</strong>
        </article>
        {chatMessages.length === 0 ? <Text className="business-order-chat-empty">Aun no hay mensajes en esta orden.</Text> : null}
        {chatMessages.map((message) => {
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
        {selectedChatOrder?.status === "payment_reported" ? (
          <article className="business-order-chat-message business-order-chat-message--system">
            <span className="business-order-chat-message__sender">NODO</span>
            <p>Pago reportado. Esperando confirmacion del negocio.</p>
          </article>
        ) : null}
        {selectedChatOrder?.status === "payment_confirmed" && !chatCapabilities.receiver_details_shared ? (
          <Text className="auth-entry__session-meta business-order-chat-note">
            Escribe tu Pago Movil en el chat.
          </Text>
        ) : null}
        {selectedChatOrder?.status === "waiting_payment"
          && selectedChatOrder.payment_method_snapshot === "zelle"
          && !chatCapabilities.payment_details_shared ? (
            <Text className="auth-entry__session-meta business-order-chat-note">
              No envies Zelle hasta que el negocio comparta sus datos.
            </Text>
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
        {chatAttachments.length || uploadingChatAttachment ? (
          <small className="business-order-chat-attachment-ready">
            {uploadingChatAttachment ? "Subiendo adjunto..." : `${chatAttachments.length} adjunto(s) listo(s) para enviar`}
          </small>
        ) : null}
        {paymentEvidence && canReportPayment ? (
          <small className="business-order-chat-attachment-ready">Comprobante listo para reportar.</small>
        ) : null}
        {chatIsTerminal ? (
          <Text className="auth-entry__session-meta business-order-chat-note">
            Esta negociacion esta cerrada. El historial queda disponible como respaldo.
          </Text>
        ) : null}
        {model.notice ? (
          <div className="native-chat-inline-notice" role="status">
            <span>{model.notice}</span>
            {model.notice.startsWith("No ") ? <button type="button" onClick={() => void refreshChat()}>Actualizar</button> : null}
          </div>
        ) : null}
        <div ref={messagesEndRef} />
      </div>

      {hasActionDock ? (
        <div className="business-order-chat-action-dock" aria-label="Acciones de la orden">
          {paymentReportMethod === "usdt_trc20" ? (
            <input
              className="business-order-chat-action-dock__hash"
              aria-label="Identificador de transaccion"
              placeholder="Identificador de transaccion"
              value={paymentReportForm.tx_hash}
              onChange={(event) => setPaymentReportForm((current) => ({ ...current, tx_hash: event.target.value }))}
            />
          ) : null}
          {canReportPayment && chatOrderId ? (
            <button
              className="business-order-chat-payment-action"
              type="button"
              disabled={submittingPaymentReport || uploadingPaymentEvidence || loadingPaymentInstructions}
              onClick={() => void submitPaymentReport()}
            >
              {submittingPaymentReport || loadingPaymentInstructions ? "Procesando..." : "Zelle enviado"}
            </button>
          ) : null}
          {canConfirmReceived ? (
            <button
              className="business-order-chat-payment-action"
              type="button"
              disabled={confirmingOrderReceived}
              onClick={() => void confirmOrderReceived()}
            >
              {confirmingOrderReceived ? "Confirmando..." : "Recibi el pago"}
            </button>
          ) : null}
        </div>
      ) : null}

      <input
        ref={paymentEvidenceInputRef}
        className="business-support-file-input"
        accept="image/jpeg,image/png,image/webp,application/pdf"
        disabled={uploadingPaymentEvidence || submittingPaymentReport}
        type="file"
        onChange={(event) => {
          const file = event.currentTarget.files?.[0] || null;
          event.currentTarget.value = "";
          void uploadPaymentEvidence(file);
        }}
      />

      {!chatIsTerminal ? (
        <form
          className="business-order-chat-composer"
          onSubmit={(event) => {
            event.preventDefault();
            void sendChatMessage();
          }}
        >
          <button
            className="business-support-clip"
            type="button"
            aria-label={canReportPayment ? "Adjuntar comprobante opcional" : "Adjuntar comprobante o soporte"}
            disabled={canReportPayment
              ? uploadingPaymentEvidence || submittingPaymentReport
              : !chatCapabilities.can_send_message || uploadingChatAttachment || sendingChatMessage}
            onClick={() => {
              if (canReportPayment) {
                paymentEvidenceInputRef.current?.click();
                return;
              }
              fileInputRef.current?.click();
            }}
          >
            <PaperclipIcon />
          </button>
          <textarea
            className="business-order-chat-composer__input"
            aria-label="Mensaje para negocio"
            disabled={!chatCapabilities.can_send_message || sendingChatMessage}
            maxLength={2000}
            placeholder={uploadingChatAttachment ? "Subiendo adjunto..." : "Escribir mensaje..."}
            rows={1}
            value={chatBody}
            onChange={(event) => setChatBody(event.target.value)}
          />
          <input
            ref={fileInputRef}
            className="business-support-file-input"
            accept="image/*,application/pdf"
            disabled={!chatCapabilities.can_send_message || uploadingChatAttachment || sendingChatMessage}
            type="file"
            onChange={(event) => {
              const file = event.currentTarget.files?.[0] || null;
              event.currentTarget.value = "";
              void uploadChatAttachment(file);
            }}
          />
          <button className="business-support-send" type="submit" aria-label="Enviar" disabled={!canSubmitMessage}>
            {sendingChatMessage ? "..." : <SendIcon />}
          </button>
        </form>
      ) : null}
    </section>
  );
}
