import type { AdminWebJobRun, AdminWebModel } from "../../hooks/useAdminWebModel";
import { dateText, Empty, Header, Metric, ReasonBox, ScrollableTable } from "./AdminWebPrimitives";

function statusText(status?: string) {
  if (status === "healthy") {
    return "Sano";
  }
  if (status === "attention") {
    return "Atencion";
  }
  if (status === "degraded") {
    return "Degradado";
  }
  if (status === "critical") {
    return "Critico";
  }
  return "Sin cargar";
}

export function IncidentConsole({ model }: { model: AdminWebModel }) {
  const data = model.incidentConsole;
  const checks = Object.entries(data?.dependencies.checks || {});
  const notificationProblems = data?.notifications.recent_problems || [];
  return (
    <section className="admin-web-grid">
      <div className="admin-web-panel span-2">
        <Header title="Centro de incidentes" action={<button type="button" onClick={() => void model.loadIncidentConsole()}>Recargar</button>} />
        <p>{data?.disclaimer || "Carga el centro de incidentes para ver el estado operativo."}</p>
        <div className="admin-web-metrics">
          <div className="admin-web-metric">
            <span>Estado general</span>
            <strong>{statusText(data?.status)}</strong>
          </div>
          <div className="admin-web-metric">
            <span>Entorno</span>
            <strong>{data?.environment || "-"}</strong>
          </div>
          <div className="admin-web-metric">
            <span>Build</span>
            <strong>{data?.build_id || "-"}</strong>
          </div>
          <div className="admin-web-metric">
            <span>Emergencia</span>
            <strong>{data?.emergency_mode.enabled ? "Activa" : "Normal"}</strong>
          </div>
        </div>
      </div>

      <div className="admin-web-panel span-2">
        <h3>Dependencias</h3>
        {checks.length ? (
          <ScrollableTable label="Checks de dependencias" headers={["Componente", "Estado", "Detalle"]}>
            {checks.map(([name, check]) => (
              <tr key={name}>
                <td>{name}</td>
                <td>{check.ok === false ? "Falla" : "OK"}</td>
                <td>{check.message || check.code || "-"}</td>
              </tr>
            ))}
          </ScrollableTable>
        ) : <Empty text="Sin checks cargados." />}
      </div>

      <div className="admin-web-panel">
        <h3>Colas</h3>
        <div className="admin-web-metrics">
          {Object.entries(data?.queues || {}).map(([key, value]) => <Metric key={key} label={key} value={value} />)}
          <Metric label="notificaciones vencidas" value={data?.notifications.pending_due} />
        </div>
      </div>

      <div className="admin-web-panel">
        <h3>Acciones sugeridas</h3>
        {data?.recommended_actions.length ? (
          <ul>
            {data.recommended_actions.map((item) => <li key={item}>{item}</li>)}
          </ul>
        ) : <Empty text="Sin acciones sugeridas." />}
      </div>

      <div className="admin-web-panel span-2">
        <h3>Jobs recientes con problemas</h3>
        {data?.jobs.recent_failed.length ? (
          <ScrollableTable label="Jobs recientes con problemas" headers={["Tipo", "Estado", "Error", "Fecha"]}>
            {data.jobs.recent_failed.map((item) => (
              <tr key={item.id}>
                <td>{item.job_type}</td>
                <td>{item.status}</td>
                <td>{item.error_code || item.error_message_safe || "-"}</td>
                <td>{dateText(item.finished_at || item.created_at)}</td>
              </tr>
            ))}
          </ScrollableTable>
        ) : <Empty text="Sin jobs fallidos visibles." />}
      </div>

      <div className="admin-web-panel span-2">
        <h3>Notificaciones con problemas</h3>
        {notificationProblems.length ? (
          <ScrollableTable label="Notificaciones con problemas" headers={["Tipo", "Estado", "Intentos", "Orden", "Error"]}>
            {notificationProblems.map((item) => (
              <tr key={item.id}>
                <td>{item.notification_type}</td>
                <td>{item.status}</td>
                <td>{item.attempts}</td>
                <td>{item.order_id || "-"}</td>
                <td>{item.last_error_code || "-"}</td>
              </tr>
            ))}
          </ScrollableTable>
        ) : <Empty text="Sin notificaciones fallidas visibles." />}
      </div>

      <div className="admin-web-panel span-2">
        <h3>Actividad reciente</h3>
        {data?.recent_audit.length ? (
          <ScrollableTable label="Actividad reciente" headers={["Evento", "Actor", "Recurso", "Fecha"]}>
            {data.recent_audit.map((item) => (
              <tr key={`${item.event_type}_${item.resource_id}_${item.created_at}`}>
                <td>{item.event_type}</td>
                <td>{item.actor_role || "-"}</td>
                <td>{item.resource_type}</td>
                <td>{dateText(item.created_at)}</td>
              </tr>
            ))}
          </ScrollableTable>
        ) : <Empty text="Sin actividad reciente." />}
      </div>
    </section>
  );
}

export function UXFriction({ model }: { model: AdminWebModel }) {
  const data = model.uxFriction;
  return (
    <section className="admin-web-grid">
      <div className="admin-web-panel span-2">
        <Header title="Friccion UX" action={<button type="button" onClick={() => void model.loadUXFriction()}>Recargar</button>} />
        <p>{data?.disclaimer || "Carga este panel para ver donde cliente y negocio se traban mas."}</p>
        <div className="admin-web-metrics">
          <div className="admin-web-metric">
            <span>Ingesta</span>
            <strong>{data?.ingest_enabled ? "Activa" : "Apagada"}</strong>
          </div>
          <Metric label="Eventos" value={data?.total_events} />
          <Metric label="Sesiones" value={data?.unique_sessions} />
          <Metric label="Friccion" value={data?.friction_events} />
        </div>
      </div>

      <div className="admin-web-panel span-2">
        <h3>Por superficie</h3>
        {data?.surfaces.length ? (
          <ScrollableTable label="UX por superficie" headers={["Superficie", "Eventos", "Friccion", "Pantallas", "API fallas", "Lentos"]}>
            {data.surfaces.map((item) => (
              <tr key={item.surface}>
                <td>{item.surface}</td>
                <td>{item.event_count}</td>
                <td>{item.friction_count}</td>
                <td>{item.screen_views}</td>
                <td>{item.api_failures}</td>
                <td>{item.slow_events}</td>
              </tr>
            ))}
          </ScrollableTable>
        ) : <Empty text="Sin eventos por superficie." />}
      </div>

      <div className="admin-web-panel span-2">
        <h3>Pantallas con mas friccion</h3>
        {data?.top_screens.length ? (
          <ScrollableTable label="Pantallas con mas friccion" headers={["Pantalla", "Superficie", "Vistas", "Friccion", "Fallos", "p95 ms"]}>
            {data.top_screens.map((item) => (
              <tr key={`${item.surface}_${item.screen}`}>
                <td>{item.screen}</td>
                <td>{item.surface}</td>
                <td>{item.views}</td>
                <td>{item.friction_count}</td>
                <td>{item.failure_count}</td>
                <td>{item.p95_duration_ms ?? "-"}</td>
              </tr>
            ))}
          </ScrollableTable>
        ) : <Empty text="Sin pantallas con friccion." />}
      </div>

      <div className="admin-web-panel span-2">
        <h3>Acciones con problemas</h3>
        {data?.top_actions.length ? (
          <ScrollableTable label="Acciones con problemas" headers={["Accion", "Superficie", "Inicios", "Completadas", "Fallidas", "Lentas", "p95 ms"]}>
            {data.top_actions.map((item) => (
              <tr key={`${item.surface}_${item.action}`}>
                <td>{item.action}</td>
                <td>{item.surface}</td>
                <td>{item.started}</td>
                <td>{item.completed}</td>
                <td>{item.failed}</td>
                <td>{item.slow_count}</td>
                <td>{item.p95_duration_ms ?? "-"}</td>
              </tr>
            ))}
          </ScrollableTable>
        ) : <Empty text="Sin acciones con problemas." />}
      </div>

      <div className="admin-web-panel span-2">
        <h3>Errores API visibles al usuario</h3>
        {data?.api_failures.length ? (
          <ScrollableTable label="Errores API visibles al usuario" headers={["Ruta", "Superficie", "Cantidad", "Codigos"]}>
            {data.api_failures.map((item) => (
              <tr key={`${item.surface}_${item.route_template}`}>
                <td>{item.route_template}</td>
                <td>{item.surface}</td>
                <td>{item.count}</td>
                <td>{Object.entries(item.error_codes).map(([code, count]) => `${code}:${count}`).join(", ")}</td>
              </tr>
            ))}
          </ScrollableTable>
        ) : <Empty text="Sin errores API visibles." />}
      </div>

      <div className="admin-web-panel">
        <h3>Acciones sugeridas</h3>
        {data?.recommended_actions.length ? (
          <ul>
            {data.recommended_actions.map((item) => <li key={item}>{item}</li>)}
          </ul>
        ) : <Empty text="Sin acciones sugeridas." />}
      </div>

      <div className="admin-web-panel">
        <h3>Friccion reciente</h3>
        {data?.recent_friction.length ? (
          <ScrollableTable label="Friccion reciente" headers={["Evento", "Pantalla", "Accion", "Error"]}>
            {data.recent_friction.map((item, index) => (
              <tr key={`${item.event_type}_${item.screen}_${item.action}_${index}`}>
                <td>{item.event_type}</td>
                <td>{item.screen || "-"}</td>
                <td>{item.action || item.route_template || "-"}</td>
                <td>{item.error_code || item.status_code || "-"}</td>
              </tr>
            ))}
          </ScrollableTable>
        ) : <Empty text="Sin friccion reciente." />}
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
      <ScrollableTable label="Jobs admin" headers={["Tipo", "Status", "Inicio", "Fin"]}>
        {model.jobRuns.map((item: AdminWebJobRun) => (
          <tr key={item.id}>
            <td>{item.job_type}</td>
            <td>{item.status}</td>
            <td>{dateText(item.started_at || item.created_at)}</td>
            <td>{dateText(item.finished_at)}</td>
          </tr>
        ))}
      </ScrollableTable>
      {model.jobRuns.length === 0 ? <Empty text="Sin job runs." /> : null}
    </section>
  );
}
