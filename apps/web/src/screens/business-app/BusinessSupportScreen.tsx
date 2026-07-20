import { Button, Text, Title } from "@telegram-apps/telegram-ui";
import type { BusinessMiniAppModel } from "../../hooks/useBusinessMiniAppModel";
import { humanizeSenderRole } from "../../hooks/business-mini-app/helpers";

export function BusinessSupportScreen({ model }: { model: BusinessMiniAppModel }) {
  const {
    creatingSupportTicket,
    loadingSupportTickets,
    loadSupportTickets,
    openSupportTicket,
    openingSupportTicketId,
    selectedSupportTicket,
    sendingSupportReply,
    setSelectedSupportTicket,
    setSupportForm,
    supportForm,
    supportReply,
    supportTickets,
    setSupportReply,
    submitSupportReply,
    submitSupportTicket,
    uploadingSupportAttachment,
    uploadTicketAttachment
  } = model;
  const ticketMessages = selectedSupportTicket?.messages || [];

  return (
    <div className="business-card">
      <Text className="business-card__label">Soporte negocio</Text>
      <Title level="3" className="business-shell__title">Ayuda operativa</Title>
      <Text className="auth-entry__session-meta">
        Soporte ayuda a revisar casos y evidencia. No aprueba pagos, no mueve fondos y no reemplaza una disputa formal.
      </Text>

      {!selectedSupportTicket ? (
        <>
          <div className="business-grid">
            <label className="business-field">
              <span>Tipo</span>
              <select value={supportForm.scope} onChange={(event) => setSupportForm((current) => ({ ...current, scope: event.target.value as typeof supportForm.scope }))}>
                <option value="business_general">Soporte general</option>
                <option value="business_order">Orden</option>
                <option value="business_ad">Anuncio</option>
                <option value="business_credit">Creditos</option>
              </select>
            </label>
            <label className="business-field">
              <span>Categoria</span>
              <select value={supportForm.category} onChange={(event) => setSupportForm((current) => ({ ...current, category: event.target.value as typeof supportForm.category }))}>
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
            <input value={supportForm.subject} onChange={(event) => setSupportForm((current) => ({ ...current, subject: event.target.value }))} />
          </label>
          <label className="business-field">
            <span>Mensaje</span>
            <textarea value={supportForm.message} onChange={(event) => setSupportForm((current) => ({ ...current, message: event.target.value }))} />
          </label>
          <div className="business-shell__tabs">
            <Button mode="filled" size="s" disabled={creatingSupportTicket || supportForm.subject.trim().length < 3 || supportForm.message.trim().length < 3} onClick={() => void submitSupportTicket()}>
              {creatingSupportTicket ? "Creando..." : "Crear conversacion"}
            </Button>
            <Button mode="outline" size="s" disabled={loadingSupportTickets} onClick={() => void loadSupportTickets()}>
              {loadingSupportTickets ? "Cargando..." : "Ver conversaciones"}
            </Button>
          </div>
        </>
      ) : null}

      {selectedSupportTicket ? (
        <div className="business-card business-support-thread">
          <div className="business-support-thread__header">
            <div>
              <Text className="business-card__label">Conversacion con soporte</Text>
              <Title level="3" className="business-shell__title">{selectedSupportTicket.subject}</Title>
              <Text className="auth-entry__session-meta">Estado: {selectedSupportTicket.status}</Text>
            </div>
            <Button mode="outline" size="s" onClick={() => setSelectedSupportTicket(null)}>Nueva conversacion</Button>
          </div>
          <div className="business-support-messages" aria-label="Mensajes de soporte">
            {ticketMessages.length === 0 ? <Text>Aun no hay mensajes en esta conversacion.</Text> : null}
            {ticketMessages.map((message) => {
              const isMine = message.sender_role === "business_owner";
              return (
                <div className={isMine ? "business-support-message business-support-message--mine" : "business-support-message"} key={message.id}>
                  <span>{humanizeSenderRole(message.sender_role)}</span>
                  <p>{message.body}</p>
                  {message.attachments?.length ? <small>{message.attachments.length} adjunto(s)</small> : null}
                  <small>{new Date(message.created_at).toLocaleString()}</small>
                </div>
              );
            })}
          </div>
          <label className="business-field">
            <span>Responder en esta conversacion</span>
            <textarea value={supportReply} onChange={(event) => setSupportReply(event.target.value)} />
          </label>
          <label className="business-upload">
            <span>Adjunto privado</span>
            <input accept="image/jpeg,image/png,image/webp,application/pdf" disabled={uploadingSupportAttachment} type="file" onChange={(event) => void uploadTicketAttachment(event.target.files?.[0] || null)} />
            {uploadingSupportAttachment ? <small>Subiendo...</small> : null}
          </label>
          <Button mode="filled" size="s" disabled={sendingSupportReply || !supportReply.trim()} onClick={() => void submitSupportReply()}>
            {sendingSupportReply ? "Enviando..." : "Enviar mensaje"}
          </Button>
        </div>
      ) : null}

      <div className="business-list">
        {supportTickets.length === 0 && !loadingSupportTickets ? <Text>Aun no tienes conversaciones de soporte.</Text> : null}
        {supportTickets.map((ticket) => (
          <button className="business-row ad-row" disabled={openingSupportTicketId === ticket.id} key={ticket.id} type="button" onClick={() => void openSupportTicket(ticket.id)}>
            <span>{ticket.status}</span>
            <span>{ticket.subject}</span>
            <span>{openingSupportTicketId === ticket.id ? "Abriendo..." : ticket.scope}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
