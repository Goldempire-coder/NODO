import { Button, Text } from "@telegram-apps/telegram-ui";
import { CHAT_DISPUTE_COPY } from "../../constants/copy";
import type { ClientWorkspaceModel } from "../../hooks/useClientWorkspaceModel";
import { ClientSupportScreen } from "./ClientSupportScreen";
import { RemitterScreens } from "./RemitterScreens";

export function ClientScreens({ model }: { model: ClientWorkspaceModel }) {
  const {
    view,
    busy,
    chatOrderId,
    chatMessages,
    chatCapabilities,
    chatBody,
    setChatBody,
    chatAttachments,
    disputeReason,
    setDisputeReason,
    refreshChat,
    uploadChatAttachment,
    sendChatMessage,
    openOrderDispute
  } = model;

  return (
    <>
      <RemitterScreens model={model} />

      {view === "support" ? <ClientSupportScreen model={model} /> : null}

      {view === "order-chat" ? (
        <div className="business-card">
          <Text className="business-card__label">Chat de la orden</Text>
          <Text className="auth-entry__session-meta">{CHAT_DISPUTE_COPY}</Text>
          <div className="business-grid">
            <Text>Coordina aqui cualquier detalle de la orden.</Text>
            <Text>Orden: {chatOrderId || "sin seleccionar"}</Text>
          </div>
          <div className="business-list">
            {chatMessages.length === 0 ? <Text>Aun no hay mensajes.</Text> : null}
            {chatMessages.map((message) => (
              <div className="business-row ad-row" key={message.id}>
                <span>{message.sender_role}</span>
                <span>{message.body || "Adjunto privado"}</span>
                <span>{new Date(message.created_at).toLocaleString()}</span>
                <span>{message.attachments.length ? `${message.attachments.length} archivo(s)` : "sin adjuntos"}</span>
              </div>
            ))}
          </div>
          <label className="business-field">
            <span>Mensaje</span>
            <textarea disabled={!chatCapabilities.can_send_message || busy} value={chatBody} onChange={(event) => setChatBody(event.target.value)} />
          </label>
          <label className="business-upload">
            <span>Adjunto privado</span>
            <input accept="image/jpeg,image/png,image/webp,application/pdf" disabled={!chatCapabilities.can_send_message || busy} type="file" onChange={(event) => void uploadChatAttachment(event.target.files?.[0] || null)} />
            {chatAttachments.length ? <small>{chatAttachments.length} archivo(s) listo(s)</small> : null}
          </label>
          <div className="business-shell__tabs">
            <Button mode="filled" size="s" disabled={busy || !chatCapabilities.can_send_message || (!chatBody.trim() && chatAttachments.length === 0)} onClick={() => void sendChatMessage()}>
              Enviar
            </Button>
            <Button mode="outline" size="s" disabled={busy || !chatOrderId} onClick={() => void refreshChat()}>
              Recargar
            </Button>
          </div>
          {chatCapabilities.can_open_dispute ? (
            <div className="business-grid">
              <label className="business-field">
                <span>Motivo disputa</span>
                <select value={disputeReason} onChange={(event) => setDisputeReason(event.target.value)}>
                  <option value="business_no_payment_confirmation">Negocio no confirma pago</option>
                  <option value="business_confirmed_payment_but_not_delivered">Pago confirmado sin envio</option>
                  <option value="payment_mobile_not_received">Pago movil no recibido</option>
                  <option value="amount_incorrect">Monto incorrecto</option>
                  <option value="wrong_receiver_data">Datos de receptor incorrectos</option>
                  <option value="other">Otro</option>
                </select>
              </label>
              <Button mode="outline" size="s" disabled={busy} onClick={() => void openOrderDispute()}>
                Abrir disputa
              </Button>
            </div>
          ) : (
            <Text className="auth-entry__session-meta">La disputa no esta disponible en el estado actual de la orden.</Text>
          )}
        </div>
      ) : null}
    </>
  );
}
