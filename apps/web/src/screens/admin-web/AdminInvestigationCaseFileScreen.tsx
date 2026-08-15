import type { ReactNode } from "react";
import type { AdminWebModel } from "../../hooks/useAdminWebModel";
import type { AdminInvestigationCaseFilePage, AdminInvestigationCaseFileSectionName } from "../../types/admin";
import { AdminInvestigationCasePlaybookPanel } from "./AdminInvestigationCasePlaybookPanel";
import { dateText, Empty, Header } from "./AdminWebPrimitives";

function OpenRoute({ model, route, label = "Abrir" }: { model: AdminWebModel; route?: string | null; label?: string }) {
  if (!route) {
    return null;
  }
  return <button type="button" onClick={() => void model.openCaseFileRoute(route)}>{label}</button>;
}

function PageSection<T extends { id: string; action_route: string }>({
  children,
  model,
  name,
  page,
  title
}: {
  children: (item: T) => ReactNode;
  model: AdminWebModel;
  name: Exclude<AdminInvestigationCaseFileSectionName, "evidence">;
  page: AdminInvestigationCaseFilePage<T>;
  title: string;
}) {
  const loading = model.caseFileSectionLoading === name;
  return (
    <section className="admin-case-file-section">
      <div className="admin-case-file-section__header">
        <h3>{title}</h3>
        <span>{page.total_count ?? page.items.length}</span>
      </div>
      {page.status === "partial_error" || page.status === "error" ? (
        <div className="admin-case-file-error">
          <p>{page.error?.message || "Esta seccion no esta disponible."}</p>
          <button type="button" disabled={loading} onClick={() => void model.loadCaseFileSection(name)}>
            {loading ? "Reintentando..." : "Reintentar"}
          </button>
        </div>
      ) : null}
      {page.status === "ok" && page.items.length === 0 ? <Empty text={`Sin ${title.toLowerCase()} relacionados.`} /> : null}
      <div className="admin-case-file-list">{page.items.map(children)}</div>
      {page.next_cursor ? (
        <button type="button" disabled={loading} onClick={() => void model.loadCaseFileSection(name, { append: true })}>
          {loading ? "Cargando..." : "Cargar mas"}
        </button>
      ) : null}
    </section>
  );
}

export function AdminInvestigationCaseFileScreen({ model }: { model: AdminWebModel }) {
  const readOnly = true;
  const file = model.caseFile;
  if (model.caseFileLoading) {
    return <section className="admin-web-panel"><p>Cargando ficha...</p></section>;
  }
  if (!file) {
    return (
      <section className="admin-web-panel">
        <Header title="Ficha de investigacion" />
        <Empty text="No hay una ficha cargada." />
        <button type="button" onClick={() => (model.adminCanGoBack ? model.goBackAdminView() : model.setView("investigation"))}>
          Volver a buscar
        </button>
      </section>
    );
  }

  return (
    <section className="admin-web-panel admin-case-file" data-read-only={readOnly}>
      <Header
        title={file.anchor.title}
        action={(
          <button type="button" onClick={() => (model.adminCanGoBack ? model.goBackAdminView() : model.setView("investigation"))}>
            {model.adminBackLabel}
          </button>
        )}
      />
      <div className="admin-case-file-summary">
        <div><span>Estado</span><strong>{file.anchor.status || "-"}</strong></div>
        <div><span>Ordenes</span><strong>{file.summary.counts.orders}</strong></div>
        <div><span>Tickets</span><strong>{file.summary.counts.support_tickets}</strong></div>
        <div><span>Ultima actividad</span><strong>{dateText(file.summary.last_activity_at)}</strong></div>
      </div>
      <div className="admin-case-file-actions">
        <OpenRoute model={model} route={file.anchor.action_route} label="Abrir origen" />
      </div>

      <AdminInvestigationCasePlaybookPanel file={file} onOpenRoute={(route) => void model.openCaseFileRoute(route)} />

      <section className="admin-case-file-section">
        <h3>Participantes</h3>
        <div className="admin-case-file-participants">
          {file.participants.client ? (
            <div>
              <strong>{file.participants.client.display_name}</strong>
              <span>{file.participants.client.telegram_hint || "Sin contacto visible"}</span>
              <OpenRoute model={model} route={file.participants.client.action_route} />
            </div>
          ) : null}
          {file.participants.business ? (
            <div>
              <strong>{file.participants.business.name}</strong>
              <span>{file.participants.business.status}</span>
              <OpenRoute model={model} route={file.participants.business.action_route} />
            </div>
          ) : null}
          {file.participants.business_owner ? (
            <div>
              <strong>Owner del negocio</strong>
              <span>{file.participants.business_owner.telegram_hint || "Sin contacto visible"}</span>
              <OpenRoute model={model} route={file.participants.business_owner.action_route} />
            </div>
          ) : null}
        </div>
      </section>

      <PageSection model={model} name="orders" page={file.orders} title="Ordenes">
        {(item) => (
          <article className="admin-case-file-row" key={item.id}>
            <div><strong>{item.public_order_code}</strong><span>{item.status} - ${item.amount_usd}</span></div>
            <OpenRoute model={model} route={item.action_route} />
          </article>
        )}
      </PageSection>

      <PageSection model={model} name="support_tickets" page={file.support_tickets} title="Tickets de soporte">
        {(item) => (
          <article className="admin-case-file-row" key={item.id}>
            <div><strong>{item.category}</strong><span>{item.status} - {item.scope}</span></div>
            <OpenRoute model={model} route={item.action_route} />
          </article>
        )}
      </PageSection>

      <PageSection model={model} name="business_intakes" page={file.business_intakes} title="Solicitudes de negocio">
        {(item) => (
          <article className="admin-case-file-row" key={item.id}>
            <div>
              <strong>{item.business_name || "Solicitud de negocio"}</strong>
              <span>{item.status}{item.referral_code ? ` - ${item.referral_code}` : ""}</span>
            </div>
            <OpenRoute model={model} route={item.action_route} />
          </article>
        )}
      </PageSection>

      <section className="admin-case-file-section">
        <div className="admin-case-file-section__header">
          <h3>Evidencia disponible</h3>
          {file.evidence.status !== "ok" ? (
            <button
              type="button"
              disabled={model.caseFileSectionLoading === "evidence"}
              onClick={() => void model.loadCaseFileSection("evidence")}
            >
              Reintentar
            </button>
          ) : null}
        </div>
        <div className="admin-case-file-evidence">
          <span>Reporte de pago: {file.evidence.payment_report_present ? "presente" : "no encontrado"}</span>
          <span>Conversacion de orden: {file.evidence.chat_evidence_available ? "disponible" : "no encontrada"}</span>
          {file.evidence.chat_action_routes.map((route) => (
            <OpenRoute key={route} model={model} route={route} label="Abrir chat" />
          ))}
          <span>Documentos: {file.evidence.documents.length}</span>
          <span>Adjuntos: {file.evidence.attachments.length}</span>
          {file.evidence.next_cursor ? (
            <button
              type="button"
              disabled={model.caseFileSectionLoading === "evidence"}
              onClick={() => void model.loadCaseFileSection("evidence", { append: true })}
            >
              {model.caseFileSectionLoading === "evidence" ? "Cargando..." : "Cargar mas evidencia"}
            </button>
          ) : null}
        </div>
      </section>

      <PageSection model={model} name="timeline" page={file.timeline} title="Timeline">
        {(item) => (
          <article className="admin-case-file-row" key={item.id}>
            <div><strong>{item.label}</strong><span>{dateText(item.created_at)}</span></div>
            <OpenRoute model={model} route={item.action_route} />
          </article>
        )}
      </PageSection>

      <section className="admin-case-file-section">
        <h3>Checklist</h3>
        <div className="admin-case-file-checklist">
          {file.review_checklist.map((item) => (
            <div key={item.code}>
              <span>{item.label}</span>
              <strong>{item.status}</strong>
              <OpenRoute model={model} route={item.action_route} />
            </div>
          ))}
        </div>
      </section>
      <p className="admin-web-muted">{file.disclaimer}</p>
    </section>
  );
}
