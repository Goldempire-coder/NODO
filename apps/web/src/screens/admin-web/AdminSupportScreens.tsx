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

function isOptimisticMessage(message: { id: string }): boolean {
  return message.id.startsWith("optimistic_");
}

function businessDisplayName(ticket: SupportTicket): string {
  const businessName = ticket.business_name?.trim();
  if (businessName) {
    return `Negocio ${businessName}`;
  }
  return ticket.business_id ? `Negocio ${ticket.business_id}` : "";
}

function contextLine(ticket: SupportTicket): string {
  const refs = [
    businessDisplayName(ticket),
    ticket.order_id ? `Orden ${ticket.order_id}` : "",
    ticket.credit_purchase_id ? `Credito ${ticket.credit_purchase_id}` : ""
  ].filter(Boolean);
  return refs.length > 0 ? refs.join(" / ") : ticket.scope;
}

function attachmentLabel(mimeType: string): string {
  if (mimeType.startsWith("image/")) {
    return "Foto";
  }
  if (mimeType === "application/pdf") {
    return "PDF";
  }
  return "Adjunto";
}

export function SupportTickets({ model }: { model: AdminWebModel }) {
  const selected = model.selectedSupportTicket;
  const selectedMessages = selected?.messages || [];
  const selectedArchived = selected?.status === "resolved" || selected?.status === "closed";
  const selectedCanClose = selected?.status === "resolved" && (model.user.role === "admin" || model.user.role === "super_admin");

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
            <div className="admin-web-support-thread__headline">
              <div>
                <span>Ticket de soporte</span>
                <h2>{selected.subject}</h2>
                <p>{contextLine(selected)}</p>
              </div>
              <strong>{statusLabel(selected.status)}</strong>
            </div>

            <div className="admin-web-support-thread__summary">
              <span>{selected.priority}</span>
              <span>{selected.requester_role}</span>
              <span>{dateText(selected.updated_at)}</span>
              <button className="admin-web-button" type="button" onClick={() => void model.refreshSelectedSupportTicket()}>
                Actualizar hilo
              </button>
            </div>

            <div className="admin-web-support-quick-actions">
              {selectedArchived ? (
                <>
                  <p className="admin-web-muted">Este ticket ya esta archivado. Puedes consultarlo desde la vista Archivados.</p>
                  {selectedCanClose ? (
                    <button className="admin-web-button danger" type="button" onClick={() => void model.changeSupportStatus("close", model.reason || "admin_support_closed")}>
                      Cerrar definitivo
                    </button>
                  ) : null}
                </>
              ) : (
                <>
                  <button className="admin-web-button" type="button" onClick={() => void model.changeSupportStatus("escalate", model.reason || "admin_support_escalation")}>
                    Escalar
                  </button>
                  <button className="admin-web-button" type="button" onClick={() => void model.changeSupportStatus("resolve", model.reason || "admin_support_resolved")}>
                    Finalizar ticket
                  </button>
                </>
              )}
            </div>

            <div className="admin-web-support-chat" aria-label="Conversacion de soporte">
              {selectedMessages.length === 0 ? (
                <Empty text="Este ticket aun no tiene mensajes." />
              ) : (
                selectedMessages.map((message) => {
                  const pending = isOptimisticMessage(message);
                  return (
                    <article className={`admin-web-support-message${isAdminMessage(message.sender_role) ? " admin-web-support-message--admin" : ""}${pending ? " admin-web-support-message--pending" : ""}`} key={message.id}>
                      <span>
                        <strong>{isAdminMessage(message.sender_role) ? "Soporte NODO" : message.sender_role}</strong>
                        {pending ? <em>Enviando...</em> : <time>{dateText(message.created_at)}</time>}
                      </span>
                      <p>{message.body}</p>
                      {(message.attachments || []).length > 0 ? (
                        <div className="admin-web-support-attachments">
                          {(message.attachments || []).map((file) => (
                            <span className="admin-web-support-attachment-actions" key={file.id}>
                              <button className="admin-web-link" type="button" onClick={() => void model.openSupportAttachment(file.id, model.reason || "admin_support_review", "view")}>
                                Abrir {attachmentLabel(file.mime_type)}
                              </button>
                              <button className="admin-web-link" type="button" onClick={() => void model.openSupportAttachment(file.id, model.reason || "admin_support_review", "download")}>
                                Descargar
                              </button>
                            </span>
                          ))}
                        </div>
                      ) : null}
                    </article>
                  );
                })
              )}
            </div>

            <div className="admin-web-support-composer">
              {model.supportAttachmentLink ? (
                <div className="admin-web-support-attachment-ready">
                  <span>Adjunto temporal listo por {model.supportAttachmentLink.expiresInSeconds}s.</span>
                  <a href={model.supportAttachmentLink.url} target="_blank" rel="noopener noreferrer">
                    Abrir
                  </a>
                  <a href={model.supportAttachmentLink.url} download={model.supportAttachmentLink.downloadFilename} target="_blank" rel="noopener noreferrer">
                    Descargar
                  </a>
                </div>
              ) : null}

              {selectedArchived ? (
                <div className="admin-web-support-admin-actions">
                  <p className="admin-web-muted">No recibe mas respuestas.</p>
                </div>
              ) : (
                <div className="admin-web-support-composer-bar">
                  <label className="admin-web-field">
                    <span>Respuesta</span>
                    <textarea disabled={model.sendingSupportReply} value={model.supportReply} onChange={(event) => model.setSupportReply(event.target.value)} />
                  </label>
                  <button className="admin-web-button" type="button" disabled={model.sendingSupportReply || !model.supportReply.trim()} onClick={() => void model.replySupportTicket()}>
                    {model.sendingSupportReply ? "Enviando..." : "Responder"}
                  </button>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </section>
  );
}
