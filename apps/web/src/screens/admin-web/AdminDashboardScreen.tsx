import type { AdminWebModel } from "../../hooks/useAdminWebModel";
import type { AdminDashboard } from "../../types/admin";
import { dateText, ReasonBox } from "./AdminWebPrimitives";

function AdminDashboardKpiGrid({ data }: { data: AdminDashboard }) {
  const items = [
    { label: "Ordenes activas", value: data.orders.active_count },
    { label: "Disputas abiertas", value: data.queues.open_disputes },
    { label: "Entregas sin cierre", value: data.orders.delivered_waiting_close_count },
    { label: "Negocios pendientes", value: data.queues.pending_businesses },
    { label: "Solicitudes intake", value: data.queues.pending_business_intakes ?? 0 },
    { label: "Negocios en revision", value: data.risk.businesses_under_review }
  ];

  return (
    <div className="admin-dashboard-kpi-grid" aria-label="Resumen operativo">
      {items.map((item) => (
        <article className="admin-dashboard-kpi" key={item.label}>
          <span>{item.label}</span>
          <strong>{item.value}</strong>
        </article>
      ))}
    </div>
  );
}

function AdminDashboardQueueList({ data, model }: { data: AdminDashboard; model: AdminWebModel }) {
  const items = [
    {
      actionLabel: "Revisar intake",
      count: data.queues.pending_business_intakes ?? 0,
      detail: "Solicitudes de alta por revisar",
      label: "Intake",
      onOpen: () => void model.loadBusinessIntakes("submitted")
    },
    {
      actionLabel: "Revisar negocios",
      count: data.queues.pending_businesses,
      detail: "Perfiles pendientes de decision",
      label: "Negocios",
      onOpen: () => void model.loadPendingBusinesses()
    },
    {
      actionLabel: "Pagos manuales",
      count: data.queues.pending_credit_purchases,
      detail: "Compras de credito en revision",
      label: "Creditos",
      onOpen: () => void model.loadCreditPurchases("pending_manual_review")
    },
    {
      actionLabel: "Abrir disputas",
      count: data.queues.open_disputes,
      detail: "Casos abiertos o en revision",
      label: "Disputas",
      onOpen: () => void model.loadDisputes("open")
    }
  ];

  return (
    <section className="admin-web-panel admin-dashboard-queue-panel" aria-labelledby="admin-dashboard-queues-title">
      <div className="admin-dashboard-section-heading">
        <div>
          <h3 id="admin-dashboard-queues-title">Colas operativas</h3>
          <p>Conteos actuales del backend, sin prioridad inferida.</p>
        </div>
      </div>
      <div className="admin-dashboard-queue-list" role="list">
        {items.map((item) => (
          <div className="admin-dashboard-queue-row" key={item.label} role="listitem">
            <div>
              <strong>{item.label}</strong>
              <span>{item.detail}</span>
            </div>
            <b aria-label={`${item.count} pendientes`}>{item.count}</b>
            <button type="button" onClick={item.onOpen}>{item.actionLabel}</button>
          </div>
        ))}
      </div>
    </section>
  );
}

function AdminDashboardQuickActions({ model }: { model: AdminWebModel }) {
  return (
    <section className="admin-web-panel admin-dashboard-quick-actions" aria-labelledby="admin-dashboard-actions-title">
      <div className="admin-dashboard-section-heading">
        <div>
          <h3 id="admin-dashboard-actions-title">Accesos rapidos</h3>
          <p>Herramientas operativas existentes.</p>
        </div>
      </div>
      <div className="admin-dashboard-action-grid">
        <button type="button" onClick={() => void model.loadAuditLogs()}>Audit logs</button>
        <button type="button" onClick={() => void model.loadMetrics()}>Metricas</button>
        <button type="button" onClick={() => void model.loadIncidentConsole()}>Incidentes</button>
        <button type="button" onClick={() => void model.loadJobs()}>Jobs</button>
      </div>
      <div className="admin-dashboard-telegram-alerts">
        <div>
          <strong>Alertas Telegram Admin</strong>
          <span>Genera un codigo temporal y envialo al bot Admin con /start CODIGO.</span>
        </div>
        <button disabled={!model.adminMutable || model.busy} type="button" onClick={() => void model.requestAdminTelegramAlertLinkCode()}>
          Generar codigo
        </button>
        {model.adminTelegramAlertLinkCode ? (
          <p role="status">
            Codigo: <strong>{model.adminTelegramAlertLinkCode.code}</strong>
            <small>Vence: {dateText(model.adminTelegramAlertLinkCode.expires_at)}</small>
          </p>
        ) : null}
      </div>
    </section>
  );
}

function AdminEmergencyModePanel({ data, model }: { data: AdminDashboard; model: AdminWebModel }) {
  const emergencyEnabled = Boolean(data.emergency_mode?.enabled);

  return (
    <section className="admin-web-panel admin-dashboard-emergency" aria-labelledby="admin-dashboard-emergency-title">
      <div className="admin-dashboard-section-heading">
        <div>
          <span className="admin-dashboard-eyebrow">Control critico</span>
          <h3 id="admin-dashboard-emergency-title">Modo emergencia</h3>
        </div>
        <div className="admin-dashboard-emergency-heading-actions">
          <span className={emergencyEnabled ? "admin-dashboard-status is-active" : "admin-dashboard-status"}>
            {emergencyEnabled ? "Activo" : "Normal"}
          </span>
          <button type="button" onClick={() => void model.loadEmergencyMode()}>Recargar</button>
        </div>
      </div>
      <p>
        {emergencyEnabled
          ? "NODO bloquea operaciones nuevas mientras el equipo resuelve el incidente."
          : "Las operaciones nuevas estan permitidas."}
      </p>
      <dl className="admin-dashboard-emergency-facts">
        <div>
          <dt>Ultimo cambio</dt>
          <dd>{dateText(data.emergency_mode?.updated_at || null)}</dd>
        </div>
        <div>
          <dt>Razon vigente</dt>
          <dd>{data.emergency_mode?.reason || "Sin razon activa"}</dd>
        </div>
      </dl>
      {data.emergency_mode?.message ? <p className="admin-dashboard-emergency-message">Mensaje visible: {data.emergency_mode.message}</p> : null}
      <div className="admin-dashboard-emergency-form">
        <ReasonBox
          model={model}
          label="Razon obligatoria"
          placeholder="Escribe el motivo operativo para auditar esta accion."
        />
        <label className="admin-web-field">
          Mensaje para usuarios
          <textarea
            disabled={!model.adminMutable || emergencyEnabled}
            maxLength={280}
            onChange={(event) => model.setEmergencyMessage(event.target.value)}
            value={model.emergencyMessage}
          />
        </label>
      </div>
      <div className="admin-web-actions admin-dashboard-emergency-actions">
        <button disabled={!model.adminMutable || emergencyEnabled} onClick={() => model.activateEmergencyMode()} type="button">
          Activar emergencia
        </button>
        <button disabled={!model.adminMutable || !emergencyEnabled} onClick={() => model.deactivateEmergencyMode()} type="button">
          Desactivar emergencia
        </button>
      </div>
    </section>
  );
}

function AdminDashboardLoading({ model }: { model: AdminWebModel }) {
  return (
    <section className="admin-dashboard" aria-busy={model.busy}>
      <div className="admin-web-panel admin-dashboard-loading">
        <span className="admin-dashboard-eyebrow">Operacion</span>
        <h2>Resumen operativo</h2>
        <p>{model.busy ? "Cargando datos del dashboard..." : "El resumen operativo aun no esta disponible."}</p>
        <div className="admin-dashboard-kpi-grid" aria-hidden="true">
          {Array.from({ length: 6 }, (_, index) => <span className="admin-dashboard-skeleton" key={index} />)}
        </div>
        <button disabled={model.busy} type="button" onClick={() => void model.loadDashboard()}>
          {model.busy ? "Cargando..." : "Reintentar"}
        </button>
      </div>
    </section>
  );
}

export function Dashboard({ model }: { model: AdminWebModel }) {
  const data = model.dashboard;
  if (!data) {
    return <AdminDashboardLoading model={model} />;
  }

  return (
    <section className="admin-dashboard" aria-labelledby="admin-dashboard-title">
      <header className="admin-dashboard-header">
        <div>
          <span className="admin-dashboard-eyebrow">Operacion</span>
          <h2 id="admin-dashboard-title">Resumen operativo</h2>
          <p>Colas y estados calculados por el backend.</p>
        </div>
        <button className="admin-dashboard-refresh" type="button" onClick={() => void model.loadDashboard()}>Recargar dashboard</button>
      </header>
      <AdminDashboardKpiGrid data={data} />
      <div className="admin-dashboard-body">
        <AdminDashboardQueueList data={data} model={model} />
        <AdminDashboardQuickActions model={model} />
      </div>
      <AdminEmergencyModePanel data={data} model={model} />
    </section>
  );
}
