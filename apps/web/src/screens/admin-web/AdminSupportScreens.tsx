import type { AdminWebModel } from "../../hooks/useAdminWebModel";
import { dateText, Empty, Header, ReasonBox, Table } from "./AdminWebPrimitives";

export function SupportTickets({ model }: { model: AdminWebModel }) {
  const selected = model.selectedSupportTicket;

  return (
    <section className="admin-web-split">
      <div className="admin-web-panel">
        <Header
          title="Soporte"
          action={
            <button className="admin-web-button" type="button" onClick={() => void model.loadSupportTickets(model.supportFilter)}>
              Actualizar
            </button>
          }
        />
        <label className="admin-web-field">
          <span>Filtro estado</span>
          <select value={model.supportFilter} onChange={(event) => model.setSupportFilter(event.target.value)}>
            <option value="">Todos</option>
            <option value="open">Open</option>
            <option value="waiting_support">Waiting support</option>
            <option value="waiting_user">Waiting user</option>
            <option value="escalated">Escalated</option>
            <option value="resolved">Resolved</option>
            <option value="closed">Closed</option>
          </select>
        </label>
        {model.supportTickets.length === 0 ? (
          <Empty text="No hay tickets con ese filtro." />
        ) : (
          <Table headers={["Estado", "Scope", "Asunto", "Actualizado", ""]}>
            {model.supportTickets.map((ticket) => (
              <tr key={ticket.id}>
                <td>{ticket.status}</td>
                <td>{ticket.scope}</td>
                <td>{ticket.subject}</td>
                <td>{dateText(ticket.updated_at)}</td>
                <td>
                  <button className="admin-web-link" type="button" onClick={() => void model.openSupportTicket(ticket.id)}>
                    Abrir
                  </button>
                </td>
              </tr>
            ))}
          </Table>
        )}
      </div>

      <div className="admin-web-panel">
        {!selected ? (
          <Empty text="Selecciona un ticket para ver mensajes, adjuntos y acciones." />
        ) : (
          <>
            <Header title={selected.subject} />
            <div className="admin-web-detail-grid">
              <span>Status: {selected.status}</span>
              <span>Priority: {selected.priority}</span>
              <span>Scope: {selected.scope}</span>
              <span>Requester: {selected.requester_role}</span>
              <span>Order: {selected.order_id || "-"}</span>
              <span>Business: {selected.business_id || "-"}</span>
            </div>
            <p className="admin-web-muted">{selected.disclaimer}</p>

            <h3>Mensajes</h3>
            <div className="admin-web-feed">
              {(selected.messages || []).map((message) => (
                <article className="admin-web-feed-item" key={message.id}>
                  <strong>{message.sender_role}</strong>
                  <p>{message.body}</p>
                  <small>{dateText(message.created_at)}</small>
                  {(message.attachments || []).map((file) => (
                    <button className="admin-web-link" key={file.id} type="button" onClick={() => void model.openSupportAttachment(file.id, model.reason || "admin_support_review")}>
                      Ver adjunto privado
                    </button>
                  ))}
                </article>
              ))}
            </div>

            {model.supportAttachmentUrl ? (
              <p className="admin-web-muted">URL temporal generada. No se persiste en auditoria ni en la UI.</p>
            ) : null}

            <label className="admin-web-field">
              <span>Respuesta</span>
              <textarea value={model.supportReply} onChange={(event) => model.setSupportReply(event.target.value)} />
            </label>
            <button className="admin-web-button" type="button" disabled={!model.supportReply.trim()} onClick={() => void model.replySupportTicket()}>
              Responder
            </button>

            <ReasonBox model={model} label="Reason requerido" />
            <label className="admin-web-field">
              <span>Asignar a user id support</span>
              <input value={model.supportAssigneeId} onChange={(event) => model.setSupportAssigneeId(event.target.value)} />
            </label>
            <div className="admin-web-actions">
              <button className="admin-web-button" type="button" onClick={() => void model.assignSupportTicket(model.reason)}>
                Asignar
              </button>
              <button className="admin-web-button" type="button" onClick={() => void model.changeSupportStatus("escalate", model.reason)}>
                Escalar
              </button>
              <button className="admin-web-button" type="button" onClick={() => void model.changeSupportStatus("resolve", model.reason)}>
                Resolver
              </button>
              <button className="admin-web-button" type="button" onClick={() => void model.changeSupportStatus("close", model.reason)}>
                Cerrar
              </button>
            </div>
          </>
        )}
      </div>
    </section>
  );
}
