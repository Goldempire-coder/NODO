import { useEffect } from "react";
import { Button, Text, Title } from "@telegram-apps/telegram-ui";
import type { ClientWorkspaceModel } from "../../hooks/useClientWorkspaceModel";

function supportStatusLabel(status: string): string {
  const labels: Record<string, string> = {
    open: "Abierto",
    waiting_support: "Soporte revisa",
    waiting_user: "Tu respuesta pendiente",
    escalated: "Escalado",
    resolved: "Archivado",
    closed: "Cerrado"
  };
  return labels[status] || status;
}

export function ClientSupportScreen({ model }: { model: ClientWorkspaceModel }) {
  const {
    creatingSupportTicket,
    loadSupportTickets,
    loadingSupportTickets,
    openSupportTicket,
    openingSupportTicketId,
    refreshSupportWorkspace,
    selectedSupportTicket,
    setSupportForm,
    supportForm,
    supportFilter,
    supportReply,
    supportTickets,
    setSupportReply,
    sendingSupportReply,
    submitSupportReply,
    submitSupportTicket,
    uploadingSupportAttachment,
    uploadTicketAttachment
  } = model;
  const selectedArchived = selectedSupportTicket?.status === "resolved" || selectedSupportTicket?.status === "closed";
  const emptyCopy = supportFilter === "archived" ? "No tienes tickets archivados." : "No tienes tickets activos.";

  useEffect(() => {
    void loadSupportTickets(supportFilter);
    const interval = window.setInterval(() => {
      void refreshSupportWorkspace();
    }, 12000);
    return () => window.clearInterval(interval);
  }, [loadSupportTickets, refreshSupportWorkspace, supportFilter]);

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
        <Button mode="filled" size="s" disabled={creatingSupportTicket || supportForm.subject.trim().length < 3 || supportForm.message.trim().length < 3} onClick={() => void submitSupportTicket()}>
          {creatingSupportTicket ? "Creando..." : "Crear ticket"}
        </Button>
        <Button mode="outline" size="s" disabled={loadingSupportTickets} onClick={() => void loadSupportTickets("active")}>
          {loadingSupportTickets ? "Cargando..." : "Ver mis tickets"}
        </Button>
      </div>
      <div className="business-shell__tabs business-shell__tabs--two">
        <Button mode={supportFilter === "active" ? "filled" : "outline"} size="s" disabled={loadingSupportTickets} onClick={() => void loadSupportTickets("active")}>
          Activos
        </Button>
        <Button mode={supportFilter === "archived" ? "filled" : "outline"} size="s" disabled={loadingSupportTickets} onClick={() => void loadSupportTickets("archived")}>
          Archivados
        </Button>
      </div>
      <div className="business-list business-list--scrollable">
        {supportTickets.length === 0 && !loadingSupportTickets ? <Text>{emptyCopy}</Text> : null}
        {supportTickets.map((ticket) => (
          <button className="business-row ad-row" disabled={openingSupportTicketId === ticket.id} key={ticket.id} type="button" onClick={() => void openSupportTicket(ticket.id)}>
            <span>{supportStatusLabel(ticket.status)}</span>
            <span>{ticket.subject}</span>
            <span>{openingSupportTicketId === ticket.id ? "Abriendo..." : ticket.scope}</span>
          </button>
        ))}
      </div>
      {selectedSupportTicket ? (
        <div className="business-card">
          <Text className="business-card__label">Ticket seleccionado</Text>
          <Title level="3" className="business-shell__title">{selectedSupportTicket.subject}</Title>
          <Text>Estado: {supportStatusLabel(selectedSupportTicket.status)}</Text>
          <div className="business-support-messages" aria-label="Mensajes de soporte">
            {(selectedSupportTicket.messages || []).map((message) => (
              <div className={message.sender_role === "remitter" ? "business-support-message business-support-message--mine" : "business-support-message"} key={message.id}>
                <span>{message.sender_role}</span>
                <p>{message.body}</p>
                <small>{new Date(message.created_at).toLocaleString()}</small>
              </div>
            ))}
          </div>
          {selectedArchived ? (
            <Text className="auth-entry__session-meta">Este ticket esta archivado. Puedes verlo cuando lo necesites, pero ya no recibe respuestas.</Text>
          ) : (
            <>
              <label className="business-field">
                <span>Responder</span>
                <textarea value={supportReply} onChange={(event) => setSupportReply(event.target.value)} />
              </label>
              <label className="business-upload">
                <span>Adjunto privado</span>
                <input accept="image/jpeg,image/png,image/webp,application/pdf" disabled={uploadingSupportAttachment} type="file" onChange={(event) => void uploadTicketAttachment(event.target.files?.[0] || null)} />
                {uploadingSupportAttachment ? <small>Subiendo adjunto...</small> : null}
              </label>
              <Button mode="filled" size="s" disabled={sendingSupportReply || !supportReply.trim()} onClick={() => void submitSupportReply()}>
                {sendingSupportReply ? "Enviando..." : "Enviar respuesta"}
              </Button>
            </>
          )}
        </div>
      ) : null}
    </div>
  );
}
