import type { AdminBusinessIntakeDetail, AdminBusinessIntakeSummary, AdminWebModel } from "../../hooks/useAdminWebModel";
import { dateText, Empty, Header, ReasonBox, Table } from "./AdminWebPrimitives";

function intakeName(item: AdminBusinessIntakeSummary) {
  return item.business_name || item.responsible_name || "Solicitud de negocio";
}

function listText(items?: string[] | null) {
  return items && items.length > 0 ? items.join(", ") : "-";
}

function referenceHref(reference: string) {
  const value = reference.trim();
  if (/^https?:\/\//i.test(value)) {
    return value;
  }
  return null;
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

function readinessText(item: AdminBusinessIntakeSummary) {
  if (item.ready_for_review) {
    return "Lista";
  }
  const missing = item.review_missing_count || 0;
  return missing > 0 ? `Faltan ${missing}` : "Faltan datos";
}

function reviewChecklist(detail: AdminBusinessIntakeDetail) {
  const intake = detail.intake;
  return [
    { label: "Codigo invitacion", ok: Boolean(intake.referral_code) },
    { label: "WhatsApp recibido", ok: Boolean(intake.contact_phone || intake.contact_phone_masked) },
    { label: "Nombre del negocio", ok: Boolean(intake.business_name) },
    { label: "Responsable", ok: Boolean(intake.responsible_name) },
    { label: "Cedula responsable", ok: Boolean(intake.responsible_id_number) },
    { label: "RIF negocio", ok: Boolean(intake.business_tax_id) },
    { label: "Telefono negocio", ok: Boolean(intake.business_phone || intake.business_phone_masked) },
    { label: "Minimo y maximo", ok: Boolean(intake.min_amount_usd && intake.max_amount_usd) },
    { label: "Limite diario", ok: Boolean(intake.daily_limit_usd) },
    { label: "Redes sociales", ok: Boolean(intake.references && intake.references.length > 0) },
    { label: "Documentos adjuntos", ok: detail.documents.length > 0 }
  ];
}

export function BusinessIntake({ model }: { model: AdminWebModel }) {
  return (
    <section className="admin-web-panel admin-web-business-intake-panel">
      <Header title="Intake de negocios" action={<button onClick={() => void model.loadBusinessIntakes(model.intakeFilter)} type="button">Aplicar filtro</button>} />
      <div className="admin-web-toolbar">
        <label><span>Filtro</span><input value={model.intakeFilter} onChange={(event) => model.setIntakeFilter(event.target.value)} placeholder="submitted o draft" /></label>
        <label>
          <span>Prioridad</span>
          <select value={model.intakeReadinessFilter} onChange={(event) => model.setIntakeReadinessFilter(event.target.value as typeof model.intakeReadinessFilter)}>
            <option value="all">Listas primero</option>
            <option value="ready">Solo listas</option>
            <option value="needs_info">Faltan datos</option>
          </select>
        </label>
        <button type="button" onClick={() => void model.loadBusinessIntakes("submitted")}>En revision</button>
        <button type="button" onClick={() => void model.loadBusinessIntakes("submitted", "ready")}>Solo listas</button>
        <button type="button" onClick={() => void model.loadBusinessIntakes("draft")}>Borradores</button>
      </div>
      <p className="admin-web-muted">Intake muestra negocios que estan intentando entrar. Las solicitudes completas salen primero; los aprobados pasan a Negocios.</p>
      <div className="admin-web-business-intake-list-scroll" role="region" aria-label="Lista de intake de negocios admin" tabIndex={0}>
        <Table headers={["Solicitud", "Status", "Prioridad", "Codigo", "WhatsApp", "Ciudad", "Fecha", ""]}>
          {model.businessIntakes.map((item) => (
            <tr key={item.id}>
              <td>{intakeName(item)}</td>
              <td>{item.status}</td>
              <td><span className={item.ready_for_review ? "admin-web-intake-ready" : "admin-web-intake-missing"}>{readinessText(item)}</span></td>
              <td>{item.referral_code || "-"}</td>
              <td>{item.contact_phone || item.contact_phone_masked || "-"}</td>
              <td>{item.city || "-"}</td>
              <td>{dateText(item.submitted_at || item.updated_at || item.created_at)}</td>
              <td><button type="button" onClick={() => void model.openBusinessIntake(item.id)}>Abrir</button></td>
            </tr>
          ))}
        </Table>
      </div>
      {model.businessIntakesNextCursor ? (
        <div className="admin-web-orders-list-actions">
          <button type="button" onClick={() => void model.loadMoreBusinessIntakes()}>Cargar mas</button>
        </div>
      ) : null}
      {model.businessIntakes.length === 0 ? <Empty text="No hay solicitudes activas en este filtro." /> : null}
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
  const contactPhone = intake.contact_phone || intake.contact_phone_masked || "-";
  const businessPhone = intake.business_phone || intake.business_phone_masked || "-";
  const canManualEdit = model.adminMutable && !intake.created_business_id && intake.status !== "accepted";
  const draft = model.intakeEditDraft;
  const minAmount = intake.min_amount_usd || "20.00";
  const maxAmount = intake.max_amount_usd || "100.00";
  const dailyLimit = intake.daily_limit_usd || "1000.00";
  const updateDraft = (patch: Partial<typeof draft>) => {
    model.setIntakeEditDraft({ ...draft, ...patch });
  };
  const publicName = model.intakePublicBusinessName.trim();
  const reviewStatusReady = ["submitted", "accepted"].includes(intake.status);
  const baseReviewBlockers = [
    !model.adminMutable ? "Tu rol no puede aprobar negocios." : "",
    !reviewStatusReady ? "La solicitud todavia no esta en revision." : "",
    missing.length > 0 ? `Faltan datos: ${missing.join(", ")}.` : "",
  ].filter(Boolean);
  const createBusinessBlockers = [
    ...baseReviewBlockers,
    intake.created_business_id ? "Esta solicitud ya tiene ficha creada." : "",
    publicName.length < 2 ? "Falta el nombre publico del negocio." : "",
  ].filter(Boolean);
  const approveBusinessBlockers = [
    ...baseReviewBlockers,
    !intake.created_business_id && publicName.length < 2 ? "Falta el nombre publico del negocio." : "",
  ].filter(Boolean);
  const canCreateBusiness = createBusinessBlockers.length === 0;
  const canApproveBusiness = approveBusinessBlockers.length === 0;
  const decisionText = missing.length === 0
    ? "Lista para revision admin. Revisa documentos y referencias antes de aprobar."
    : `No apruebes todavia. Faltan: ${missing.join(", ")}.`;
  return (
    <section className="admin-web-split admin-web-intake-layout">
      {model.adminCanGoBack ? (
        <div className="admin-web-detail-backbar span-2">
          <button type="button" onClick={() => model.goBackAdminView()}>{model.adminBackLabel}</button>
        </div>
      ) : null}
      <div className="admin-web-panel admin-web-intake-column">
        <Header title="Solicitud de negocio" action={<button type="button" onClick={() => void model.loadBusinessIntakes(model.intakeFilter)}>Volver a solicitudes</button>} />
        <div className="admin-web-intake-scroll">
        <div className="admin-web-intake-hero">
          <div>
            <span>{intake.status}</span>
            <strong>{intakeName(intake)}</strong>
            <small>{intake.city || "Ciudad pendiente"} - {contactPhone}</small>
          </div>
          <div>
            <span>Montos autorizados</span>
            <strong>{minAmount} - {maxAmount} USD</strong>
            <small>Limite diario: {dailyLimit} USD</small>
          </div>
        </div>

        <div className="admin-web-detail-grid">
          <div className="admin-web-row"><span>Codigo invitacion</span><strong>{intake.referral_code || "-"}</strong></div>
          <div className="admin-web-row"><span>WhatsApp solicitante</span><strong>{contactPhone}</strong></div>
          <div className="admin-web-row"><span>Responsable</span><strong>{intake.responsible_name || "-"}</strong></div>
          <div className="admin-web-row"><span>Cedula responsable</span><strong>{intake.responsible_id_number || "-"}</strong></div>
          <div className="admin-web-row"><span>RIF negocio</span><strong>{intake.business_tax_id || "-"}</strong></div>
          <div className="admin-web-row"><span>Telefono negocio</span><strong>{businessPhone}</strong></div>
          <div className="admin-web-row"><span>Operacion declarada</span><strong>{intake.operation || "-"}</strong></div>
          <div className="admin-web-row"><span>Metodos declarados</span><strong>{listText(intake.methods)}</strong></div>
          <div className="admin-web-row">
            <span>Redes sociales</span>
            {intake.references && intake.references.length > 0 ? (
              <div className="admin-web-reference-list">
                {intake.references.map((reference) => {
                  const href = referenceHref(reference);
                  return href ? (
                    <a href={href} key={reference} target="_blank" rel="noreferrer">{reference}</a>
                  ) : (
                    <strong key={reference}>{reference}</strong>
                  );
                })}
              </div>
            ) : <strong>-</strong>}
          </div>
          <div className="admin-web-row"><span>Paso bot</span><strong>{intake.last_step}</strong></div>
          <div className="admin-web-row"><span>Negocio creado</span><strong>{intake.created_business_id || "-"}</strong></div>
        </div>

        <div className="admin-web-intake-edit">
          <div className="admin-web-section-title">
            <div>
              <h3>Completar ficha manualmente</h3>
              <p className="admin-web-muted">Usa esto si hablaste con el negocio por WhatsApp y quieres corregir o completar datos antes de aprobar.</p>
            </div>
            <span>{canManualEdit ? "Editable" : "Bloqueado"}</span>
          </div>
          <div className="admin-web-form-grid intake-edit">
            <label>
              <span>Codigo invitacion</span>
              <input disabled={!canManualEdit} value={draft.referral_code} onChange={(event) => updateDraft({ referral_code: event.target.value })} placeholder="Codigo referido" />
            </label>
            <label>
              <span>WhatsApp solicitante</span>
              <input disabled={!canManualEdit} value={draft.contact_phone} onChange={(event) => updateDraft({ contact_phone: event.target.value })} placeholder="+58..." />
            </label>
            <label>
              <span>Nombre negocio</span>
              <input disabled={!canManualEdit} value={draft.business_name} onChange={(event) => updateDraft({ business_name: event.target.value })} placeholder="Casa Cambio Centro" />
            </label>
            <label>
              <span>RIF negocio</span>
              <input disabled={!canManualEdit} value={draft.business_tax_id} onChange={(event) => updateDraft({ business_tax_id: event.target.value })} placeholder="J-12345678-9" />
            </label>
            <label>
              <span>Responsable</span>
              <input disabled={!canManualEdit} value={draft.responsible_name} onChange={(event) => updateDraft({ responsible_name: event.target.value })} placeholder="Nombre y apellido" />
            </label>
            <label>
              <span>Cedula responsable</span>
              <input disabled={!canManualEdit} value={draft.responsible_id_number} onChange={(event) => updateDraft({ responsible_id_number: event.target.value })} placeholder="V-12345678" />
            </label>
            <label>
              <span>Ciudad</span>
              <input disabled={!canManualEdit} value={draft.city} onChange={(event) => updateDraft({ city: event.target.value })} placeholder="Caracas" />
            </label>
            <label>
              <span>Telefono negocio</span>
              <input disabled={!canManualEdit} value={draft.business_phone} onChange={(event) => updateDraft({ business_phone: event.target.value })} placeholder="+58..." />
            </label>
            <label>
              <span>Operacion</span>
              <select disabled={!canManualEdit} value={draft.operation} onChange={(event) => updateDraft({ operation: event.target.value })}>
                <option value="">Seleccionar</option>
                <option value="buy_usd">Compra USD</option>
                <option value="sell_usd">Vende USD</option>
                <option value="both">Compra y vende</option>
              </select>
            </label>
            <label>
              <span>Metodos</span>
              <input disabled={!canManualEdit} value={draft.methods} onChange={(event) => updateDraft({ methods: event.target.value })} placeholder="Zelle, USDT" />
            </label>
            <label>
              <span>Bancos</span>
              <input disabled={!canManualEdit} value={draft.banks} onChange={(event) => updateDraft({ banks: event.target.value })} placeholder="Banesco, Mercantil" />
            </label>
            <label>
              <span>Min USD</span>
              <input disabled={!canManualEdit} inputMode="decimal" value={draft.min_amount_usd} onChange={(event) => updateDraft({ min_amount_usd: event.target.value })} placeholder="20" />
            </label>
            <label>
              <span>Max USD</span>
              <input disabled={!canManualEdit} inputMode="decimal" value={draft.max_amount_usd} onChange={(event) => updateDraft({ max_amount_usd: event.target.value })} placeholder="100" />
            </label>
            <label>
              <span>Limite diario USD</span>
              <input disabled={!canManualEdit} inputMode="decimal" value={draft.daily_limit_usd} onChange={(event) => updateDraft({ daily_limit_usd: event.target.value })} placeholder="1000" />
            </label>
            <label className="span-3">
              <span>Redes sociales / referencias publicas</span>
              <textarea disabled={!canManualEdit} value={draft.references} onChange={(event) => updateDraft({ references: event.target.value })} placeholder="Instagram, TikTok, Google Maps o web. Obligatorio; separa varias con coma." />
            </label>
          </div>
          <div className="admin-web-actions">
            <button disabled={!canManualEdit} type="button" onClick={() => model.saveBusinessIntakeManual(false)}>
              Guardar ficha
            </button>
            <button disabled={!canManualEdit} type="button" onClick={() => model.saveBusinessIntakeManual(true)}>
              Guardar y poner en revision
            </button>
          </div>
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
      </div>

      <aside className="admin-web-panel admin-web-action-panel">
        <h3>Documentos</h3>
        <p className="admin-web-muted">Abre cada archivo en una URL temporal. La accion queda auditada automaticamente.</p>
        {detail.documents.length === 0 ? <Empty text="Sin documentos adjuntos." /> : null}
        <div className="admin-web-document-list">
          {detail.documents.map((file) => (
            <div className="admin-web-document-card" key={file.id}>
              <div>
                <strong>{documentKindLabel(file.document_kind || file.file_type)}</strong>
                <small>{file.mime_type} - {fileSizeText(file.size_bytes)} - {dateText(file.created_at)}</small>
              </div>
              <div className="admin-web-document-actions">
                <button className="admin-web-document-button" disabled={!model.adminMutable} type="button" onClick={() => model.openBusinessIntakeDocument(file.id, "view")}>
                  Ver
                </button>
                <button className="admin-web-document-button" disabled={!model.adminMutable} type="button" onClick={() => model.openBusinessIntakeDocument(file.id, "download")}>
                  Descargar
                </button>
              </div>
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
        <ReasonBox model={model} label="Nota interna opcional" />
        <div className={approveBusinessBlockers.length === 0 ? "admin-web-action-status is-ok" : "admin-web-action-status is-warning"}>
          <strong>Estado de aprobacion</strong>
          {approveBusinessBlockers.length === 0 ? (
            <p>Lista para confirmar. Al aprobar, el bot avisa al negocio.</p>
          ) : (
            <ul>
              {approveBusinessBlockers.map((item) => <li key={item}>{item}</li>)}
            </ul>
          )}
        </div>
        <div className="admin-web-actions vertical">
          <button disabled={!canCreateBusiness} title={createBusinessBlockers[0] || "Crear negocio pendiente"} type="button" onClick={() => model.createBusinessFromIntake()}>
            Crear negocio pendiente
          </button>
          <button disabled={!canApproveBusiness} title={approveBusinessBlockers[0] || "Crear/aprobar y avisar por Telegram"} type="button" onClick={() => model.approveBusinessFromIntake()}>
            Crear, aprobar y avisar
          </button>
          <button className="danger" disabled={!model.adminMutable} type="button" onClick={() => model.deleteBusinessIntake()}>
            Borrar y reiniciar onboarding
          </button>
        </div>
        <p className="admin-web-muted">Crear negocio pendiente lo mueve a Negocios sin dar acceso. Aprobar y avisar confirma acceso y envia el boton por Telegram.</p>
      </aside>
    </section>
  );
}
