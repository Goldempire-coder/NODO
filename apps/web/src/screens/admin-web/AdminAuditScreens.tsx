import type { AdminWebModel } from "../../hooks/useAdminWebModel";
import type { AdminAuditLog } from "../../types/admin";
import { dateText, Empty, Header, Table } from "./AdminWebPrimitives";

export function AuditLogs({ model }: { model: AdminWebModel }) {
  return (
    <section className="admin-web-panel admin-web-audit-logs-panel">
      <Header title="A-11 Audit logs" action={<button onClick={() => void model.loadAuditLogs()} type="button">Filtrar</button>} />
      <div className="admin-web-toolbar">
        <label><span>Evento</span><input value={model.auditFilter} onChange={(event) => model.setAuditFilter(event.target.value)} placeholder="event_type" /></label>
      </div>
      <div className="admin-web-audit-logs-list-scroll" role="region" aria-label="Lista de audit logs admin" tabIndex={0}>
        <Table headers={["Evento", "Actor", "Recurso", "Fecha"]}>
          {model.auditLogs.map((item: AdminAuditLog, index) => (
            <tr key={`${item.event_type}_${item.created_at}_${index}`}>
              <td>{item.event_type}</td>
              <td>{item.actor_role || "-"}</td>
              <td>{item.resource_type}</td>
              <td>{dateText(item.created_at)}</td>
            </tr>
          ))}
        </Table>
      </div>
      {model.auditLogs.length === 0 ? <Empty text="Sin eventos audit para el filtro actual." /> : null}
    </section>
  );
}
