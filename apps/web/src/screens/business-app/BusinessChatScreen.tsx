import { Button, Text } from "@telegram-apps/telegram-ui";
import { CHAT_DISPUTE_COPY } from "../../constants/copy";
import { humanizeSenderRole } from "../../hooks/business-mini-app/helpers";
import type { BusinessMiniAppModel } from "../../hooks/useBusinessMiniAppModel";

export function BusinessChatScreen({ model }: { model: BusinessMiniAppModel }) {
  const {
    chatAttachments,
    chatBody,
    chatCapabilities,
    chatMessages,
    chatOrderId,
    disputeReason,
    openOrderDispute,
    openingOrderDispute,
    refreshChat,
    refreshingChat,
    sendChatMessage,
    sendingChatMessage,
    setChatBody,
    setDisputeReason,
    uploadingChatAttachment,
    uploadChatAttachment
  } = model;

  return (
    <div className="business-card">
      <Text className="business-card__label">Chat de orden</Text>
      <Text className="auth-entry__session-meta">{CHAT_DISPUTE_COPY}</Text>
      <div className="business-grid">
        <Text>{chatOrderId ? "Orden vinculada" : "Sin orden seleccionada"}</Text>
        <Button mode="outline" size="s" disabled={refreshingChat || !chatOrderId} onClick={() => void refreshChat()}>
          {refreshingChat ? "Recargando..." : "Recargar"}
        </Button>
      </div>
      <div className="business-list">
        {chatMessages.length === 0 ? <Text>Aun no hay mensajes.</Text> : null}
        {chatMessages.map((message) => (
          <div className="business-row ad-row" key={message.id}>
            <span>{humanizeSenderRole(message.sender_role)}</span>
            <span>{message.body || "Adjunto privado"}</span>
            <span>{new Date(message.created_at).toLocaleString()}</span>
            <span>{message.attachments.length ? `${message.attachments.length} archivo(s)` : "sin adjuntos"}</span>
          </div>
        ))}
      </div>
      <label className="business-field">
        <span>Mensaje</span>
        <textarea disabled={!chatCapabilities.can_send_message || sendingChatMessage} value={chatBody} onChange={(event) => setChatBody(event.target.value)} />
      </label>
      <label className="business-upload">
        <span>Adjunto privado</span>
        <input accept="image/jpeg,image/png,image/webp,application/pdf" disabled={!chatCapabilities.can_send_message || uploadingChatAttachment} type="file" onChange={(event) => void uploadChatAttachment(event.target.files?.[0] || null)} />
        {chatAttachments.length ? <small>{chatAttachments.length} archivo(s) listo(s)</small> : null}
        {uploadingChatAttachment ? <small>Subiendo...</small> : null}
      </label>
      <div className="business-shell__tabs">
        <Button mode="filled" size="s" disabled={sendingChatMessage || !chatCapabilities.can_send_message || (!chatBody.trim() && chatAttachments.length === 0)} onClick={() => void sendChatMessage()}>
          {sendingChatMessage ? "Enviando..." : "Enviar"}
        </Button>
      </div>
      {chatCapabilities.can_open_dispute ? (
        <div className="business-grid">
          <label className="business-field">
            <span>Motivo del caso</span>
            <select value={disputeReason} onChange={(event) => setDisputeReason(event.target.value)}>
              <option value="business_no_payment_confirmation">Pago no confirmado</option>
              <option value="business_confirmed_payment_but_not_delivered">Pago confirmado sin envio</option>
              <option value="payment_mobile_not_received">Pago movil no recibido</option>
              <option value="amount_incorrect">Monto incorrecto</option>
              <option value="wrong_receiver_data">Datos de receptor incorrectos</option>
              <option value="other">Otro</option>
            </select>
          </label>
          <Button mode="outline" size="s" disabled={openingOrderDispute} onClick={() => void openOrderDispute()}>
            {openingOrderDispute ? "Abriendo..." : "Abrir caso"}
          </Button>
        </div>
      ) : <Text className="auth-entry__session-meta">Abrir caso no esta disponible en este estado.</Text>}
    </div>
  );
}
