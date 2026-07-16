import { Button, Text, Title } from "@telegram-apps/telegram-ui";
import type { ClientWorkspaceModel } from "../../hooks/useClientWorkspaceModel";

export function ClientSupportScreen({ model }: { model: ClientWorkspaceModel }) {
  const {
    busy,
    loadSupportTickets,
    openSupportTicket,
    selectedSupportTicket,
    setSupportForm,
    supportForm,
    supportReply,
    supportTickets,
    setSupportReply,
    submitSupportReply,
    submitSupportTicket,
    uploadTicketAttachment
  } = model;

  return (
    <div className="business-card">
      <Text className="business-card__label">Soporte NODO</Text>
      <Title level="3" className="business-shell__title">Centro de ayuda</Title>
      <Text className="auth-entry__session-meta">
        Este soporte no cambia estados de orden ni reemplaza una disputa formal. NODO registra y organiza la evidencia del caso.
      </Text>
      <div className="business-grid">
        <label className="business-field">
          <span>Tipo</span>
          <select value={supportForm.scope} onChange={(event) => setSupportForm((current) => ({ ...current, scope: event.target.value as typeof supportForm.scope }))}>
            <option value="client_general">Soporte general</option>
            <option value="client_order">Soporte por orden</option>
          </select>
        </label>
        <label className="business-field">
          <span>Categoria</span>
          <select value={supportForm.category} onChange={(event) => setSupportForm((current) => ({ ...current, category: event.target.value as typeof supportForm.category }))}>
            <option value="technical_issue">Problema tecnico</option>
            <option value="account_access">Acceso a cuenta</option>
            <option value="order_help">Ayuda con orden</option>
            <option value="payment_report_help">Reporte de pago</option>
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
        <Button mode="filled" size="s" disabled={busy || supportForm.subject.trim().length < 3 || supportForm.message.trim().length < 3} onClick={() => void submitSupportTicket()}>
          Crear ticket
        </Button>
        <Button mode="outline" size="s" disabled={busy} onClick={() => void loadSupportTickets()}>
          Ver mis tickets
        </Button>
      </div>
      <div className="business-list">
        {supportTickets.length === 0 ? <Text>Aun no tienes tickets abiertos.</Text> : null}
        {supportTickets.map((ticket) => (
          <button className="business-row ad-row" key={ticket.id} type="button" onClick={() => void openSupportTicket(ticket.id)}>
            <span>{ticket.status}</span>
            <span>{ticket.subject}</span>
            <span>{ticket.scope}</span>
          </button>
        ))}
      </div>
      {selectedSupportTicket ? (
        <div className="business-card">
          <Text className="business-card__label">Ticket seleccionado</Text>
          <Title level="3" className="business-shell__title">{selectedSupportTicket.subject}</Title>
          <Text>Estado: {selectedSupportTicket.status}</Text>
          <div className="business-list">
            {(selectedSupportTicket.messages || []).map((message) => (
              <div className="business-row ad-row" key={message.id}>
                <span>{message.sender_role}</span>
                <span>{message.body}</span>
                <span>{new Date(message.created_at).toLocaleString()}</span>
              </div>
            ))}
          </div>
          <label className="business-field">
            <span>Responder</span>
            <textarea value={supportReply} onChange={(event) => setSupportReply(event.target.value)} />
          </label>
          <label className="business-upload">
            <span>Adjunto privado</span>
            <input accept="image/jpeg,image/png,image/webp,application/pdf" disabled={busy} type="file" onChange={(event) => void uploadTicketAttachment(event.target.files?.[0] || null)} />
          </label>
          <Button mode="filled" size="s" disabled={busy || !supportReply.trim()} onClick={() => void submitSupportReply()}>
            Enviar respuesta
          </Button>
        </div>
      ) : null}
    </div>
  );
}
