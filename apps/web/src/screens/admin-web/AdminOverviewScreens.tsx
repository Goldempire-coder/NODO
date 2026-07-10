import type { AdminWebJobRun, AdminWebModel } from "../../hooks/useAdminWebModel";
import { dateText, Empty, Header, Metric, ReasonBox, Table } from "./AdminWebPrimitives";

export function Dashboard({ model }: { model: AdminWebModel }) {
  const data = model.dashboard;
  return (
    <section className="admin-web-grid">
      <div className="admin-web-panel span-2">
        <h2>A-01 Dashboard</h2>
        <p>Colas operativas calculadas desde backend. No hay metricas falsas.</p>
        <div className="admin-web-metrics">
          <Metric label="Negocios pendientes" value={data?.queues.pending_businesses} />
          <Metric label="Pagos credito" value={data?.queues.pending_credit_purchases} />
          <Metric label="Disputas abiertas" value={data?.queues.open_disputes} />
          <Metric label="Ordenes activas" value={data?.orders.active_count} />
          <Metric label="Delivered sin cierre" value={data?.orders.delivered_waiting_close_count} />
          <Metric label="Clientes con telefono" value={data?.users?.client_profiles_with_phone} />
        </div>
      </div>
      <div className="admin-web-panel">
        <h3>Accesos rapidos</h3>
        <div className="admin-web-actions vertical">
          <button type="button" onClick={() => void model.loadPendingBusinesses()}>Revisar negocios</button>
          <button type="button" onClick={() => void model.loadCreditPurchases("pending_manual_review")}>Pagos manuales</button>
          <button type="button" onClick={() => void model.loadDisputes("open")}>Disputas abiertas</button>
          <button type="button" onClick={() => void model.loadAuditLogs()}>Audit logs</button>
        </div>
      </div>
    </section>
  );
}

export function Metrics({ model }: { model: AdminWebModel }) {
  const metrics = model.metrics;
  return (
    <section className="admin-web-panel">
      <h2>A-12 Metricas</h2>
      <p>Read-model calculado; no crea tabla dedicada en MVP.</p>
      {metrics ? (
        <div className="admin-web-metrics">
          {Object.entries(metrics.businesses || {}).map(([key, value]) => <Metric key={`b_${key}`} label={`Business ${key}`} value={value} />)}
          {Object.entries(metrics.orders || {}).map(([key, value]) => <Metric key={`o_${key}`} label={`Order ${key}`} value={value} />)}
          {Object.entries(metrics.disputes || {}).map(([key, value]) => <Metric key={`d_${key}`} label={`Dispute ${key}`} value={value} />)}
          {Object.entries(metrics.credits || {}).map(([key, value]) => <Metric key={`c_${key}`} label={`Credit ${key}`} value={value} />)}
        </div>
      ) : <Empty text="Carga metricas desde la navegacion." />}
    </section>
  );
}

export function Jobs({ model }: { model: AdminWebModel }) {
  return (
    <section className="admin-web-panel">
      <Header title="Jobs admin" action={<button onClick={() => void model.loadJobs()} type="button">Recargar</button>} />
      <ReasonBox model={model} label="Reason para dry-run" />
      <button disabled={!model.adminMutable} type="button" onClick={() => model.dryRunJobs()}>Dry-run expire/escalate</button>
      <Table headers={["Tipo", "Status", "Inicio", "Fin"]}>
        {model.jobRuns.map((item: AdminWebJobRun) => (
          <tr key={item.id}>
            <td>{item.job_type}</td>
            <td>{item.status}</td>
            <td>{dateText(item.started_at || item.created_at)}</td>
            <td>{dateText(item.finished_at)}</td>
          </tr>
        ))}
      </Table>
      {model.jobRuns.length === 0 ? <Empty text="Sin job runs." /> : null}
    </section>
  );
}
