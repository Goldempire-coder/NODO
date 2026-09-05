import { useEffect, useRef } from "react";
import { Button, Text } from "@telegram-apps/telegram-ui";
import { PaperclipIcon, SendIcon } from "../../components/nodo/ChatComposerIcons";
import type { ClientWorkspaceModel } from "../../hooks/useClientWorkspaceModel";
import { useClientOrderChatSync } from "../../hooks/workspace/useClientOrderChatSync";
import { ClientChatMessageList } from "./chat/ClientChatMessageList";
import { ClientOrderRatingBubble } from "./chat/ClientOrderRatingBubble";
import { ClientPaymentDetailsBubble } from "./chat/ClientPaymentDetailsBubble";
import { ClientReceiverDetailsBubble } from "./chat/ClientReceiverDetailsBubble";

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
    chatMessagesNextCursor,
    chatOrderId,
    loadMoreChatMessages,
    loadingMoreChatMessages,
    loadingPaymentInstructions,
    openChatAttachment,
    openPaymentReport,
    paymentEvidence,
    paymentInstructions,
    confirmOrderReceived,
    confirmingOrderReceived,
    dismissChatAttachmentLink,
    refreshChat,
    receiverDetailsForm,
    receiverDetailsMasked,
    selectedRatingStars,
    sendChatMessage,
    sendingChatMessage,
    setSelectedRatingStars,
    submitOrderRating,
    submitPaymentReport,
    submittingPaymentReport,
    submittingRatingOrderId,
    setChatBody,
    setReceiverDetailsForm,
    shareReceiverDetails,
    sharingReceiverDetails,
    uploadPaymentEvidence,
    uploadingPaymentEvidence,
    uploadChatAttachment,
    uploadingChatAttachment
  } = model;
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const paymentEvidenceInputRef = useRef<HTMLInputElement | null>(null);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  const skipNextAutoScrollRef = useRef(false);
  const canSend = chatCapabilities.can_send_message && !sendingChatMessage && !uploadingChatAttachment;
  const canSubmitMessage = canSend && (chatBody.trim().length > 0 || chatAttachments.length > 0);
  const selectedChatOrder = model.selectedOrder?.id === chatOrderId ? model.selectedOrder : null;
  const currentPaymentInstructions = paymentInstructions?.order.id === chatOrderId ? paymentInstructions : null;
  const paymentReportMethod = currentPaymentInstructions?.payment_instructions.method_type || selectedChatOrder?.payment_method_snapshot;
  const chatIsTerminal = selectedChatOrder?.status === "cancelled" || selectedChatOrder?.status === "completed";
  const canReportPayment = chatCapabilities.can_report_payment && selectedChatOrder?.status === "waiting_payment";
  const canConfirmReceived = chatCapabilities.can_confirm_received && selectedChatOrder?.status === "delivered";
  const canShareReceiverDetails = selectedChatOrder?.status === "payment_confirmed"
    && !chatCapabilities.receiver_details_shared;
  const completedRating = selectedChatOrder?.status === "completed" ? selectedChatOrder.rating : undefined;
  const submittingRating = submittingRatingOrderId === selectedChatOrder?.id;
  const hasActionDock = canConfirmReceived || (canReportPayment && Boolean(chatOrderId));

  useClientOrderChatSync({
    canReportPayment,
    chatOrderId,
    hasPaymentInstructions: Boolean(currentPaymentInstructions),
    openPaymentReport,
    refreshChat,
    sendingChatMessage,
    uploadingChatAttachment,
    view: model.view
  });

  useEffect(() => {
    setSelectedRatingStars(completedRating?.stars || 0);
  }, [completedRating?.already_rated, completedRating?.stars, selectedChatOrder?.id, setSelectedRatingStars]);

  useEffect(() => {
    if (skipNextAutoScrollRef.current) {
      skipNextAutoScrollRef.current = false;
      return;
    }
    messagesEndRef.current?.scrollIntoView({ block: "end" });
  }, [chatOrderId, chatMessages.length, chatAttachments.length, currentPaymentInstructions?.order.id]);

  return (
    <section className={hasActionDock ? "business-order-chat business-order-chat--has-actions" : "business-order-chat"} aria-label="Chat con negocio">
      <div className="business-order-chat-messages" aria-label="Mensajes de la orden" aria-live="polite">
        <article className="business-order-chat-message business-order-chat-message--system business-order-chat-system-bubble">
          <span className="business-order-chat-message__sender">NODO</span>
          <p>Solicitud abierta con {selectedChatOrder?.business_name || "el negocio"}</p>
          <strong>{orderLabel(model)}</strong>
        </article>
        {paymentReportMethod === "usdt_trc20" ? (
          <article className="business-order-chat-message business-order-chat-message--system">
            <span className="business-order-chat-message__sender">NODO</span>
            <p>Confirma con el negocio la red exacta antes de realizar cualquier pago directo.</p>
          </article>
        ) : null}
        {chatMessagesNextCursor ? (
          <div className="business-order-chat-history">
            <Button
              mode="outline"
              size="s"
              disabled={loadingMoreChatMessages}
              onClick={() => {
                skipNextAutoScrollRef.current = true;
                void loadMoreChatMessages();
              }}
            >
              {loadingMoreChatMessages ? "Cargando..." : "Ver mensajes anteriores"}
            </Button>
          </div>
        ) : null}
        <ClientChatMessageList
          messages={chatMessages}
          paymentInstructions={currentPaymentInstructions}
          openAttachment={openChatAttachment}
        />
        {currentPaymentInstructions ? (
          <ClientPaymentDetailsBubble instructions={currentPaymentInstructions} />
        ) : null}
        {selectedChatOrder?.status === "payment_reported" ? (
          <article className="business-order-chat-message business-order-chat-message--system">
            <span className="business-order-chat-message__sender">NODO</span>
            <p>Pago reportado. Esperando confirmacion del negocio.</p>
          </article>
        ) : null}
        <ClientReceiverDetailsBubble
          canShare={canShareReceiverDetails}
          capabilities={chatCapabilities}
          form={receiverDetailsForm}
          masked={receiverDetailsMasked}
          setForm={setReceiverDetailsForm}
          share={shareReceiverDetails}
          sharing={sharingReceiverDetails}
        />
        {selectedChatOrder?.status === "waiting_payment" && !chatCapabilities.payment_details_shared ? (
            <Text className="auth-entry__session-meta business-order-chat-note">
              No realices ningun pago directo hasta que el negocio comparta sus datos.
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
            {uploadingChatAttachment ? "Subiendo adjunto..." : `${chatAttachments.length} adjunto(s) listo(s)`}
          </small>
        ) : null}
        {paymentEvidence && canReportPayment ? (
          <small className="business-order-chat-attachment-ready">Comprobante listo para reportar.</small>
        ) : null}
        {completedRating && selectedChatOrder ? (
          <ClientOrderRatingBubble
            orderId={selectedChatOrder.id}
            rating={completedRating}
            selectedStars={selectedRatingStars}
            setSelectedStars={setSelectedRatingStars}
            submit={submitOrderRating}
            submitting={submittingRating}
          />
        ) : null}
        {chatIsTerminal ? (
          <Text className="auth-entry__session-meta business-order-chat-note">
            Esta orden esta cerrada. El historial queda disponible como registro de la conversacion.
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
          {canReportPayment && chatOrderId ? (
            <button
              className="business-order-chat-payment-action"
              type="button"
              disabled={submittingPaymentReport || uploadingPaymentEvidence || loadingPaymentInstructions}
              onClick={() => void submitPaymentReport()}
            >
              {submittingPaymentReport || loadingPaymentInstructions
                ? "Procesando..."
                : paymentReportMethod === "usdt_trc20" ? "Reportar USDT" : "Reportar Zelle"}
            </button>
          ) : null}
          {canConfirmReceived ? (
            <button
              className="business-order-chat-payment-action"
              type="button"
              disabled={confirmingOrderReceived}
              onClick={() => void confirmOrderReceived()}
            >
              {confirmingOrderReceived ? "Confirmando..." : "Confirmar recepcion"}
            </button>
          ) : null}
        </div>
      ) : null}

      <input
        ref={paymentEvidenceInputRef}
        className="business-support-file-input"
        accept="image/jpeg,image/png,image/webp"
        disabled={uploadingPaymentEvidence || submittingPaymentReport || loadingPaymentInstructions}
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
              ? uploadingPaymentEvidence || submittingPaymentReport || loadingPaymentInstructions
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
            accept="image/jpeg,image/png,image/webp"
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
