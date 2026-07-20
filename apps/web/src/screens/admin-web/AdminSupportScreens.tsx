import type { AdminWebModel } from "../../hooks/useAdminWebModel";
import type { SupportTicket } from "../../types/support";
import { dateText, Empty, Header } from "./AdminWebPrimitives";

const STATUS_LABELS: Record<SupportTicket["status"], string> = {
  open: "Abierto",
  waiting_support: "Por responder",
  waiting_user: "Esperando negocio",
  escalated: "Escalado",
  resolved: "Archivado",
  closed: "Cerrado"
};

function statusLabel(status: SupportTicket["status"]): string {
  return STATUS_LABELS[status] || status;
}

function isAdminMessage(senderRole: string): boolean {
  return senderRole === "admin" || senderRole === "support" || senderRole === "super_admin";
}

function contextLine(ticket: SupportTicket): string {
  const refs = [
    ticket.business_id ? `Negocio ${ticket.business_id}` : "",
    ticket.order_id ? `Orden ${ticket.order_id}` : "",
    ticket.credit_purchase_id ? `Credito ${ticket.credit_purchase_id}` : ""
  ].filter(Boolean);
  return refs.length > 0 ? refs.join(" / ") : ticket.scope;
}

export function SupportTickets({ model }: { model: AdminWebModel }) {
  const selected = model.selectedSupportTicket;
  const selectedMessages = selected?.messages || [];
  const selectedArchived = selected?.status === "resolved" || selected?.status === "closed";
  const selectedCanClose = selected?.status === "resolved";

  return (
    <section className="admin-web-split admin-web-support-layout">
      <div className="admin-web-panel admin-web-support-list-panel">
        <Header
          title="Soporte"
          action={
            <button className="admin-web-button" type="button" onClick={() => void model.loadSupportTickets(model.supportFilter)}>
              Actualizar
            </button>
          }
        />

        <div className="admin-web-toolbar">
          <label>
            <span>Vista</span>
            <select value={model.supportFilter} onChange={(event) => void model.loadSupportTickets(event.target.value)}>
              <option value="active">Activos</option>
              <option value="waiting_support">Por responder</option>
              <option value="waiting_user">Esperando negocio</option>
              <option value="escalated">Escalados</option>
              <option value="archived">Archivados</option>
              <option value="all">Todos</option>
            </select>
          </label>
        </div>

        <div className="admin-web-support-list" aria-label="Tickets de soporte">
          {model.supportTickets.length === 0 ? (
            <Empty text="No hay tickets en esta vista." />
          ) : (
            model.supportTickets.map((ticket) => (
              <button
                className={`admin-web-support-ticket${selected?.id === ticket.id ? " is-selected" : ""}`}
                key={ticket.id}
                type="button"
                onClick={() => void model.openSupportTicket(ticket.id)}
              >
                <span className="admin-web-support-ticket__top">
                  <strong>{ticket.subject}</strong>
                  <span>{statusLabel(ticket.status)}</span>
                </span>
                <small>{contextLine(ticket)}</small>
                <span className="admin-web-support-ticket__meta">
                  <span>{ticket.priority}</span>
                  <time>{dateText(ticket.updated_at)}</time>
                </span>
              </button>
            ))
          )}
        </div>
      </div>

      <div className="admin-web-panel admin-web-support-thread-panel">
        {!selected ? (
          <Empty text="Selecciona un ticket para responder sin abrir una pantalla gigante." />
        ) : (
          <div className="admin-web-support-thread">
            <Header
              title={selected.subject}
              action={
                <button className="admin-web-button" type="button" onClick={() => void model.refreshSelectedSupportTicket()}>
                  Actualizar hilo
                </button>
              }
            />

            <div className="admin-web-support-thread__summary">
              <span>{statusLabel(selected.status)}</span>
              <span>{selected.priority}</span>
              <span>{contextLine(selected)}</span>
              <span>{selected.requester_role}</span>
            </div>

            <div className="admin-web-support-chat" aria-label="Conversacion de soporte">
              {selectedMessages.length === 0 ? (
                <Empty text="Este ticket aun no tiene mensajes." />
              ) : (
                selectedMessages.map((message) => (
                  <article className={`admin-web-support-message${isAdminMessage(message.sender_role) ? " admin-web-support-message--admin" : ""}`} key={message.id}>
                    <span>
                      <strong>{isAdminMessage(message.sender_role) ? "Soporte NODO" : message.sender_role}</strong>
                      <time>{dateText(message.created_at)}</time>
                    </span>
                    <p>{message.body}</p>
                    {(message.attachments || []).length > 0 ? (
                      <div className="admin-web-support-attachments">
                        {(message.attachments || []).map((file) => (
                          <button className="admin-web-link" key={file.id} type="button" onClick={() => void model.openSupportAttachment(file.id, model.reason || "admin_support_review")}>
                            Ver adjunto
                          </button>
                        ))}
                      </div>
                    ) : null}
                  </article>
                ))
              )}
            </div>

            <div className="admin-web-support-composer">
              {model.supportAttachmentUrl ? (
                <p className="admin-web-muted">URL temporal generada. No se guarda como dato permanente.</p>
              ) : null}

              {selectedArchived ? (
                <div className="admin-web-support-admin-actions">
                  <p className="admin-web-muted">Este ticket ya esta archivado. Puedes consultarlo desde la vista Archivados.</p>
                  {selectedCanClose ? (
                    <button className="admin-web-button danger" type="button" onClick={() => void model.changeSupportStatus("close", model.reason || "admin_support_closed")}>
                      Cerrar definitivo
                    </button>
                  ) : null}
                </div>
              ) : (
                <>
                  <label className="admin-web-field">
                    <span>Respuesta</span>
                    <textarea value={model.supportReply} onChange={(event) => model.setSupportReply(event.target.value)} />
                  </label>
                  <button className="admin-web-button" type="button" disabled={!model.supportReply.trim()} onClick={() => void model.replySupportTicket()}>
                    Responder
                  </button>

                  <div className="admin-web-support-admin-actions">
                    <label className="admin-web-field">
                      <span>Nota interna opcional</span>
                      <textarea value={model.reason} onChange={(event) => model.setReason(event.target.value)} />
                    </label>
                    <label className="admin-web-field">
                      <span>Asignar a user id support</span>
                      <input value={model.supportAssigneeId} onChange={(event) => model.setSupportAssigneeId(event.target.value)} />
                    </label>
                    <div className="admin-web-actions">
                      <button className="admin-web-button" type="button" onClick={() => void model.assignSupportTicket(model.reason || "admin_support_assignment")}>
                        Asignar
                      </button>
                      <button className="admin-web-button" type="button" onClick={() => void model.changeSupportStatus("escalate", model.reason || "admin_support_escalation")}>
                        Escalar
                      </button>
                      <button className="admin-web-button" type="button" onClick={() => void model.changeSupportStatus("resolve", model.reason || "admin_support_resolved")}>
                        Resolver y archivar
                      </button>
                    </div>
                  </div>
                </>
              )}
            </div>
          </div>
        )}
      </div>
    </section>
  );
}
