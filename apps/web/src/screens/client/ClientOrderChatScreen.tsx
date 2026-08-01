import { useEffect, useRef, useState } from "react";
import { Text } from "@telegram-apps/telegram-ui";
import { CHAT_DISPUTE_COPY } from "../../constants/copy";
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

function humanizeClientOrderStatus(status: string): string {
  const labels: Record<string, string> = {
    waiting_payment: "Esperando pago",
    payment_reported: "Pago reportado",
    payment_rejected: "Reporte rechazado",
    payment_confirmed: "Pago confirmado",
    delivered: "Enviado",
    completed: "Completada",
    disputed: "En revision",
    cancelled: "Cancelada"
  };
  return labels[status] || status.replaceAll("_", " ");
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

function orderCode(model: ClientWorkspaceModel): string {
  if (model.selectedOrder?.id === model.chatOrderId && model.selectedOrder.public_order_code) {
    return model.selectedOrder.public_order_code;
  }
  return model.chatOrderId ? `Orden ${model.chatOrderId.slice(0, 8)}` : "Sin orden";
}

function orderStatus(model: ClientWorkspaceModel): string {
  if (model.selectedOrder?.id === model.chatOrderId) {
    return humanizeClientOrderStatus(model.selectedOrder.status);
  }
  return "Chat operativo";
}

function PaperclipIcon() {
  return (
    <svg aria-hidden="true" className="business-support-icon-svg" focusable="false" viewBox="0 0 24 24">
      <path d="m21.4 11.6-8.9 8.9a6 6 0 0 1-8.5-8.5l9.6-9.6a4 4 0 0 1 5.7 5.7l-9.6 9.6a2 2 0 0 1-2.8-2.8l8.9-8.9" />
    </svg>
  );
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

export function ClientOrderChatScreen({ model }: { model: ClientWorkspaceModel }) {
  const {
    chatAttachments,
    chatAttachmentLink,
    chatBody,
    chatCapabilities,
    chatMessages,
    chatOrderId,
    disputeReason,
    loadingPaymentInstructions,
    openOrderDispute,
    openingOrderDispute,
    openChatAttachment,
    paymentEvidence,
    paymentInstructions,
    paymentReportForm,
    confirmOrderReceived,
    confirmingOrderReceived,
    dismissChatAttachmentLink,
    refreshChat,
    refreshingChat,
    sendChatMessage,
    sendingChatMessage,
    submitPaymentReport,
    submittingPaymentReport,
    setChatBody,
    setDisputeReason,
    setPaymentReportForm,
    uploadPaymentEvidence,
    uploadingPaymentEvidence,
    uploadChatAttachment,
    uploadingChatAttachment
  } = model;
  const [composerFocused, setComposerFocused] = useState(false);
  const composerRef = useRef<HTMLFormElement | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const paymentEvidenceInputRef = useRef<HTMLInputElement | null>(null);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  const canSend = chatCapabilities.can_send_message && !sendingChatMessage && !uploadingChatAttachment;
  const canSubmitMessage = canSend && (chatBody.trim().length > 0 || chatAttachments.length > 0);
  const selectedChatOrder = model.selectedOrder?.id === chatOrderId ? model.selectedOrder : null;
  const paymentReportMethod = paymentInstructions?.payment_instructions.method_type || selectedChatOrder?.payment_method_snapshot;
  const paymentReportAmount = paymentInstructions?.order.amount_usd || selectedChatOrder?.amount_usd;

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

  const scrollMessagesToEnd = () => {
    messagesEndRef.current?.scrollIntoView({ block: "end" });
  };

  const focusComposer = () => {
    setComposerFocused(true);
    window.requestAnimationFrame(scrollMessagesToEnd);
    window.setTimeout(scrollMessagesToEnd, 260);
  };

  const blurComposer = () => {
    window.setTimeout(() => {
      if (!composerRef.current?.contains(document.activeElement)) {
        setComposerFocused(false);
      }
    }, 120);
  };

  return (
    <section className={composerFocused ? "business-order-chat business-order-chat--typing" : "business-order-chat"} aria-label="Chat con negocio">
      <div className="business-order-chat__summary">
        <div className="business-order-chat__compact-heading">
          <Text className="business-card__label">Chat con negocio</Text>
          <strong className="business-order-chat__compact-code">{orderCode(model)}</strong>
          <small>{model.selectedOrder?.business_name || orderStatus(model)}</small>
        </div>
        <button className="business-support-icon-button" type="button" aria-label="Actualizar chat" disabled={refreshingChat || !chatOrderId} onClick={() => void refreshChat()}>
          <RefreshIcon />
        </button>
      </div>

      <div className="business-order-chat-messages" aria-label="Mensajes de la orden" aria-live="polite">
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
        <div ref={messagesEndRef} />
      </div>

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

      {selectedChatOrder?.status === "payment_confirmed" && !chatCapabilities.receiver_details_shared ? (
        <Text className="auth-entry__session-meta business-order-chat-note">
          Escribe tu Pago Movil en el chat.
        </Text>
      ) : null}

      {chatCapabilities.can_confirm_received ? (
        <button
          className="business-order-chat-payment-action"
          type="button"
          disabled={confirmingOrderReceived}
          onClick={() => void confirmOrderReceived()}
        >
          {confirmingOrderReceived ? "Confirmando..." : "Recibi el pago"}
        </button>
      ) : null}

      {chatCapabilities.can_report_payment && chatOrderId ? (
        <div className="business-order-chat-payment-bar" aria-label="Reportar Zelle enviado">
          <span>
            Adjunta el comprobante
            {paymentReportAmount ? ` - ${paymentReportAmount} USD` : ""}
          </span>
          {paymentReportMethod === "usdt_trc20" ? (
            <input
              className="business-order-chat-payment-bar__hash"
              aria-label="Tx hash"
              placeholder="Tx hash"
              value={paymentReportForm.tx_hash}
              onChange={(event) => setPaymentReportForm((current) => ({ ...current, tx_hash: event.target.value }))}
            />
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
          <button
            className="business-order-chat-payment-action"
            type="button"
            disabled={uploadingPaymentEvidence || submittingPaymentReport}
            onClick={() => paymentEvidenceInputRef.current?.click()}
          >
            {uploadingPaymentEvidence ? "..." : paymentEvidence ? "Cambiar" : "Foto"}
          </button>
          <button
            className="business-order-chat-payment-action"
            type="button"
            disabled={submittingPaymentReport || uploadingPaymentEvidence || !paymentEvidence || loadingPaymentInstructions}
            onClick={() => void submitPaymentReport()}
          >
            {submittingPaymentReport || loadingPaymentInstructions ? "..." : "Zelle enviado"}
          </button>
        </div>
      ) : selectedChatOrder?.status === "waiting_payment"
        && selectedChatOrder.payment_method_snapshot === "zelle"
        && !chatCapabilities.payment_details_shared ? (
          <Text className="auth-entry__session-meta business-order-chat-note">
            No envies Zelle hasta que el negocio comparta sus datos.
          </Text>
        ) : null}

      <form
        ref={composerRef}
        className="business-order-chat-composer"
        onSubmit={(event) => {
          event.preventDefault();
          void sendChatMessage();
        }}
      >
        <button
          className="business-support-clip"
          type="button"
          aria-label="Adjuntar comprobante o soporte"
          disabled={!chatCapabilities.can_send_message || uploadingChatAttachment || sendingChatMessage}
          onClick={() => fileInputRef.current?.click()}
        >
          <PaperclipIcon />
        </button>
        <textarea
          className="business-order-chat-composer__input"
          aria-label="Mensaje para negocio"
          disabled={!chatCapabilities.can_send_message || sendingChatMessage}
          maxLength={2000}
          placeholder={uploadingChatAttachment ? "Subiendo adjunto..." : "Escribir mensaje..."}
          rows={2}
          value={chatBody}
          onBlur={blurComposer}
          onChange={(event) => setChatBody(event.target.value)}
          onFocus={focusComposer}
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
        <button className="business-support-send" type="submit" disabled={!canSubmitMessage}>
          {sendingChatMessage ? "..." : "Enviar"}
        </button>
      </form>

      {chatAttachments.length || uploadingChatAttachment ? (
        <small className="business-order-chat-attachment-ready">
          {uploadingChatAttachment ? "Subiendo adjunto..." : `${chatAttachments.length} adjunto(s) listo(s) para enviar`}
        </small>
      ) : null}

      {chatCapabilities.can_open_dispute ? (
        <div className="business-order-chat-actions">
          <label>
            <span>Si algo no cuadra</span>
            <select value={disputeReason} onChange={(event) => setDisputeReason(event.target.value)}>
              <option value="business_no_payment_confirmation">Pago no confirmado</option>
              <option value="business_confirmed_payment_but_not_delivered">Pago confirmado sin envio</option>
              <option value="payment_mobile_not_received">Pago movil no recibido</option>
              <option value="amount_incorrect">Monto incorrecto</option>
              <option value="wrong_receiver_data">Datos de receptor incorrectos</option>
              <option value="other">Otro</option>
            </select>
          </label>
          <button className="business-order-chat-dispute" type="button" disabled={openingOrderDispute} onClick={() => void openOrderDispute()}>
            {openingOrderDispute ? "Abriendo..." : "Abrir caso"}
          </button>
        </div>
      ) : (
        <Text className="auth-entry__session-meta business-order-chat-note">{CHAT_DISPUTE_COPY}</Text>
      )}
    </section>
  );
}
