import type { AdminBusinessIntakeSummary, AdminWebModel } from "../../hooks/useAdminWebModel";
import { dateText, Empty, Header, ReasonBox, Table } from "./AdminWebPrimitives";

function intakeName(item: AdminBusinessIntakeSummary) {
  return item.business_name || item.responsible_name || "Solicitud de negocio";
}

export function BusinessIntake({ model }: { model: AdminWebModel }) {
  return (
    <section className="admin-web-panel">
      <Header title="Intake de negocios" action={<button onClick={() => void model.loadBusinessIntakes(model.intakeFilter)} type="button">Aplicar filtro</button>} />
      <div className="admin-web-toolbar">
        <label><span>Filtro</span><input value={model.intakeFilter} onChange={(event) => model.setIntakeFilter(event.target.value)} placeholder="all, submitted, draft..." /></label>
        <button type="button" onClick={() => void model.loadBusinessIntakes("all")}>Todas</button>
        <button type="button" onClick={() => void model.loadBusinessIntakes("submitted")}>En revision</button>
        <button type="button" onClick={() => void model.loadBusinessIntakes("draft")}>Borradores</button>
        <button type="button" onClick={() => void model.loadBusinessIntakes("accepted")}>Aceptadas</button>
      </div>
      <p className="admin-web-muted">Si un negocio empezo el registro pero no lo finalizo, aparece como borrador.</p>
      <Table headers={["Solicitud", "Status", "Telefono", "Ciudad", "Fecha", ""]}>
        {model.businessIntakes.map((item) => (
          <tr key={item.id}>
            <td>{intakeName(item)}</td>
            <td>{item.status}</td>
            <td>{item.contact_phone_masked || "-"}</td>
            <td>{item.city || "-"}</td>
            <td>{dateText(item.submitted_at || item.updated_at || item.created_at)}</td>
            <td><button type="button" onClick={() => void model.openBusinessIntake(item.id)}>Abrir</button></td>
          </tr>
        ))}
      </Table>
      {model.businessIntakes.length === 0 ? <Empty text="No hay solicitudes para el filtro actual. Prueba con Todas para ver registros incompletos." /> : null}
    </section>
  );
}

export function BusinessIntakeDetail({ model }: { model: AdminWebModel }) {
  const detail = model.selectedBusinessIntake;
  if (!detail) {
    return <Empty text="Selecciona una solicitud de negocio." />;
  }
  const intake = detail.intake;
  return (
    <section className="admin-web-split">
      <div className="admin-web-panel">
        <h2>Solicitud de negocio</h2>
        <dl className="admin-web-dl">
          <dt>Status</dt><dd>{intake.status}</dd>
          <dt>Paso</dt><dd>{intake.last_step}</dd>
          <dt>Negocio</dt><dd>{intake.business_name || "-"}</dd>
          <dt>Responsable</dt><dd>{intake.responsible_name || "-"}</dd>
          <dt>Ciudad</dt><dd>{intake.city || "-"}</dd>
          <dt>Contacto</dt><dd>{intake.contact_phone_masked || "-"}</dd>
          <dt>Operacion</dt><dd>{intake.operation || "-"}</dd>
          <dt>Rango</dt><dd>{intake.min_amount_usd || "-"} - {intake.max_amount_usd || "-"}</dd>
          <dt>Horario</dt><dd>{intake.schedule || "-"}</dd>
          <dt>Negocio creado</dt><dd>{intake.created_business_id || "-"}</dd>
        </dl>
        {intake.status === "draft" ? (
          <p className="admin-web-muted">Este registro todavia no fue finalizado desde Telegram. Sirve para revisar que el bot recibio datos, pero no deberia aprobarse hasta completarlo.</p>
        ) : null}
      </div>
      <div className="admin-web-panel">
        <h3>Documentos y control</h3>
        {detail.documents.length === 0 ? <Empty text="Sin documentos." /> : null}
        {detail.documents.map((file) => (
          <div className="admin-web-row" key={file.id}>
            <span>{file.document_kind || file.file_type}</span>
            <small>{file.mime_type} - {file.size_bytes} bytes</small>
          </div>
        ))}
        <div className="admin-web-form-row">
          <label>
            <span>Nombre publico en la app</span>
            <input
              value={model.intakePublicBusinessName}
              onChange={(event) => model.setIntakePublicBusinessName(event.target.value)}
              placeholder="Ej. Casa Cambio Centro"
            />
          </label>
        </div>
        <ReasonBox model={model} label="Reason para crear negocio" />
        <button disabled={!model.adminMutable || Boolean(intake.created_business_id)} type="button" onClick={() => model.createBusinessFromIntake()}>
          Crear negocio pendiente
        </button>
        <button disabled={!model.adminMutable} type="button" onClick={() => model.approveBusinessFromIntake()}>
          Crear, aprobar y avisar
        </button>
        <p className="admin-web-muted">El segundo boton crea o aprueba el negocio, crea el acceso y envia el boton de NODO Negocio por Telegram.</p>
        <ReasonBox model={model} label="Reason para borrar" />
        <button className="danger" disabled={!model.adminMutable} type="button" onClick={() => model.deleteBusinessIntake()}>
          Borrar registro
        </button>
        <p className="admin-web-muted">Borra la solicitud del panel si el negocio la hizo mal. Los audit logs se preservan.</p>
      </div>
    </section>
  );
}
