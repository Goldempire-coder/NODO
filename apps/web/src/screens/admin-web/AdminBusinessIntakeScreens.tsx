import type { AdminBusinessIntakeDetail, AdminBusinessIntakeSummary, AdminWebModel } from "../../hooks/useAdminWebModel";
import { dateText, Empty, Header, ReasonBox, Table } from "./AdminWebPrimitives";

function intakeName(item: AdminBusinessIntakeSummary) {
  return item.business_name || item.responsible_name || "Solicitud de negocio";
}

function listText(items?: string[] | null) {
  return items && items.length > 0 ? items.join(", ") : "-";
}

function fileSizeText(bytes: number) {
  if (bytes < 1024) {
    return `${bytes} B`;
  }
  if (bytes < 1024 * 1024) {
    return `${(bytes / 1024).toFixed(1)} KB`;
  }
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function documentKindLabel(kind?: string | null) {
  switch (kind) {
    case "identity_document":
      return "Identidad";
    case "rif_document":
      return "RIF o registro";
    case "local_image":
      return "Foto del negocio";
    case "reference_document":
      return "Referencia";
    default:
      return kind || "Documento";
  }
}

function reviewChecklist(detail: AdminBusinessIntakeDetail) {
  const intake = detail.intake;
  return [
    { label: "WhatsApp recibido", ok: Boolean(intake.contact_phone_masked) },
    { label: "Nombre y responsable", ok: Boolean(intake.business_name && intake.responsible_name) },
    { label: "Ciudad y telefono del negocio", ok: Boolean(intake.city && intake.business_phone_masked) },
    { label: "Operacion y metodos", ok: Boolean(intake.operation && intake.methods?.length) },
    { label: "Bancos declarados", ok: Boolean(intake.banks?.length) },
    { label: "Rango autorizado", ok: Boolean(intake.min_amount_usd && intake.max_amount_usd) },
    { label: "Horario y referencias", ok: Boolean(intake.schedule && intake.references?.length) },
    { label: "Documentos adjuntos", ok: detail.documents.length > 0 }
  ];
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
  const checklist = reviewChecklist(detail);
  const missing = checklist.filter((item) => !item.ok).map((item) => item.label);
  const canReview = model.adminMutable && missing.length === 0 && ["submitted", "accepted"].includes(intake.status);
  const decisionText = missing.length === 0
    ? "Lista para revision admin. Revisa documentos y motivo antes de aprobar."
    : `No apruebes todavia. Faltan: ${missing.join(", ")}.`;
  return (
    <section className="admin-web-split admin-web-intake-layout">
      <div className="admin-web-panel">
        <Header title="Solicitud de negocio" action={<button type="button" onClick={() => void model.loadBusinessIntakes(model.intakeFilter)}>Volver a solicitudes</button>} />
        <div className="admin-web-intake-hero">
          <div>
            <span>{intake.status}</span>
            <strong>{intakeName(intake)}</strong>
            <small>{intake.city || "Ciudad pendiente"} - {intake.contact_phone_masked || "WhatsApp pendiente"}</small>
          </div>
          <div>
            <span>Rango declarado</span>
            <strong>{intake.min_amount_usd || "-"} - {intake.max_amount_usd || "-"} USD</strong>
            <small>{listText(intake.methods)}</small>
          </div>
        </div>

        <div className="admin-web-detail-grid">
          <div className="admin-web-row"><span>Responsable</span><strong>{intake.responsible_name || "-"}</strong></div>
          <div className="admin-web-row"><span>Telefono negocio</span><strong>{intake.business_phone_masked || "-"}</strong></div>
          <div className="admin-web-row"><span>Operacion</span><strong>{intake.operation || "-"}</strong></div>
          <div className="admin-web-row"><span>Horario</span><strong>{intake.schedule || "-"}</strong></div>
          <div className="admin-web-row"><span>Bancos</span><strong>{listText(intake.banks)}</strong></div>
          <div className="admin-web-row"><span>Referencias</span><strong>{listText(intake.references)}</strong></div>
          <div className="admin-web-row"><span>Paso bot</span><strong>{intake.last_step}</strong></div>
          <div className="admin-web-row"><span>Negocio creado</span><strong>{intake.created_business_id || "-"}</strong></div>
        </div>

        <h3>Checklist para aprobar</h3>
        <p className="admin-web-muted">Esta pantalla sirve para decidir si el negocio puede operar sin poner en riesgo a clientes: identidad, responsable, referencias, rango y documentos deben cuadrar.</p>
        <div className="admin-web-checklist">
          {checklist.map((item) => (
            <div className={item.ok ? "is-ok" : "is-missing"} key={item.label}>
              <span>{item.ok ? "Listo" : "Falta"}</span>
              <strong>{item.label}</strong>
            </div>
          ))}
        </div>
        {intake.status === "draft" ? (
          <p className="admin-web-warning">Este registro todavia no fue finalizado desde Telegram. No deberia aprobarse hasta completarlo.</p>
        ) : null}
      </div>

      <aside className="admin-web-panel admin-web-action-panel">
        <h3>Documentos</h3>
        <p className="admin-web-muted">Abre cada archivo en una URL temporal. La accion queda auditada y necesitas escribir un motivo.</p>
        {detail.documents.length === 0 ? <Empty text="Sin documentos adjuntos." /> : null}
        <div className="admin-web-document-list">
          {detail.documents.map((file) => (
            <div className="admin-web-document-card" key={file.id}>
              <div>
                <strong>{documentKindLabel(file.document_kind || file.file_type)}</strong>
                <small>{file.mime_type} - {fileSizeText(file.size_bytes)} - {dateText(file.created_at)}</small>
              </div>
              <button className="admin-web-document-button" disabled={!model.adminMutable} type="button" onClick={() => model.openBusinessIntakeDocument(file.id)}>
                Ver / descargar
              </button>
            </div>
          ))}
        </div>

        <div className="admin-web-review-box">
          <h3>Antes de aprobar</h3>
          <p>Verifica que el responsable, el WhatsApp, los documentos y las referencias tengan sentido para el monto que va a operar.</p>
          <div className={missing.length === 0 ? "admin-web-action-status is-ok" : "admin-web-action-status is-warning"}>
            {decisionText}
          </div>
          {missing.length > 0 ? <p className="admin-web-warning">Faltan datos para aprobar: {missing.join(", ")}.</p> : null}
        </div>

        <label className="admin-web-field">
          <span>Nombre publico en la app</span>
          <input
            value={model.intakePublicBusinessName}
            onChange={(event) => model.setIntakePublicBusinessName(event.target.value)}
            placeholder="Ej. Casa Cambio Centro"
          />
        </label>
        <ReasonBox model={model} label="Motivo de revision" />
        <div className="admin-web-actions vertical">
          <button disabled={!canReview || Boolean(intake.created_business_id)} type="button" onClick={() => model.createBusinessFromIntake()}>
            Crear negocio pendiente
          </button>
          <button disabled={!canReview} type="button" onClick={() => model.approveBusinessFromIntake()}>
            Crear, aprobar y avisar
          </button>
          <button className="danger" disabled={!model.adminMutable} type="button" onClick={() => model.deleteBusinessIntake()}>
            Borrar registro
          </button>
        </div>
      </aside>
    </section>
  );
}
