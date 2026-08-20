import { useState } from "react";
import type { AdminWebModel } from "../../hooks/useAdminWebModel";
import { businessName, dateText, Empty, Header, ReasonBox, Table } from "./AdminWebPrimitives";

async function copyText(value: string) {
  if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(value);
    return;
  }

  const textarea = document.createElement("textarea");
  textarea.value = value;
  textarea.setAttribute("readonly", "true");
  textarea.style.position = "fixed";
  textarea.style.opacity = "0";
  document.body.appendChild(textarea);
  textarea.select();
  document.execCommand("copy");
  document.body.removeChild(textarea);
}

const ACCESS_ACTION_COPY: Record<string, string> = {
  none: "Sin accion pendiente.",
  unblock_business: "Desbloquear negocio.",
  reactivate_business: "Reactivar negocio.",
  review_business_approval: "Revisar aprobacion del negocio.",
  unblock_owner_user: "Desbloquear dueno.",
  reactivate_owner_user: "Reactivar dueno.",
  reactivate_owner_link: "Reactivar vinculo owner.",
  create_owner_link: "Crear vinculo owner.",
  regenerate_owner_link: "Regenerar o revisar vinculo owner.",
  review_owner_binding: "Revisar vinculacion del dueno.",
};

const ACCESS_REASON_COPY: Record<string, string> = {
  BUSINESS_BLOCKED: "El negocio esta bloqueado.",
  BUSINESS_SUSPENDED: "El negocio esta suspendido.",
  BUSINESS_NOT_APPROVED: "El negocio no esta aprobado.",
  USER_BLOCKED: "La cuenta del dueno esta bloqueada.",
  USER_NOT_ACTIVE: "La cuenta del dueno no esta activa.",
  BUSINESS_ACCESS_SUSPENDED: "El vinculo owner esta suspendido.",
  BUSINESS_ACCESS_BLOCKED: "El vinculo owner esta bloqueado.",
  BUSINESS_ACCESS_REVOKED: "El vinculo owner esta revocado.",
  BUSINESS_ACCESS_LINK_REQUIRED: "Falta un vinculo owner valido.",
  SURFACE_ACCESS_DENIED: "La vinculacion no coincide con el acceso autenticado.",
  OWNER_USER_NOT_FOUND: "No se encontro el usuario dueno.",
};

export function Businesses({ model }: { model: AdminWebModel }) {
  return (
    <section className="admin-web-panel admin-web-businesses-panel">
      <Header title="A-02 Negocios" action={<button form="admin-businesses-filter" type="submit">Aplicar filtro</button>} />
      <form
        className="admin-web-toolbar admin-web-toolbar--businesses"
        id="admin-businesses-filter"
        onSubmit={(event) => {
          event.preventDefault();
          void model.loadBusinesses(model.businessFilter, model.businessSearchFilter);
        }}
      >
        <label>
          <span>Estado del negocio</span>
          <select value={model.businessFilter} onChange={(event) => model.setBusinessFilter(event.target.value)}>
            <option value="">Todos</option>
            <option value="pending">Pendientes</option>
            <option value="approved">Aprobados</option>
            <option value="suspended">Suspendidos</option>
            <option value="blocked">Bloqueados</option>
            <option value="rejected">Rechazados</option>
          </select>
        </label>
        <label>
          <span>ID o nombre</span>
          <input value={model.businessSearchFilter} onChange={(event) => model.setBusinessSearchFilter(event.target.value)} placeholder="ID o nombre del negocio" />
        </label>
        <button type="button" onClick={() => void model.loadPendingBusinesses()}>Pendientes</button>
      </form>
      <div className="admin-web-businesses-list-scroll" role="region" aria-label="Lista de negocios admin" tabIndex={0}>
        <Table headers={["Negocio", "Estado", "Riesgo", "Creado", ""]}>
          {model.businesses.map((item) => (
            <tr key={item.id}>
              <td>{businessName(item)}</td>
              <td>{item.verification_status || "-"}</td>
              <td>{item.risk_level || "-"}</td>
              <td>{dateText(item.created_at || item.submitted_at)}</td>
              <td><button type="button" onClick={() => void model.openBusiness(item.id)}>Abrir</button></td>
            </tr>
          ))}
        </Table>
      </div>
      {model.businessesNextCursor ? (
        <div className="admin-web-orders-list-actions">
          <button disabled={model.businessesLoadingMore} type="button" onClick={() => void model.loadMoreBusinesses()}>
            {model.businessesLoadingMore ? "Cargando..." : "Cargar mas"}
          </button>
        </div>
      ) : null}
      {model.businesses.length === 0 ? <Empty text="No hay negocios para el filtro actual." /> : null}
    </section>
  );
}

export function BusinessDetail({ model }: { model: AdminWebModel }) {
  const detail = model.selectedBusiness;
  const [copiedBusinessId, setCopiedBusinessId] = useState(false);
  if (!detail) {
    return <Empty text="Selecciona un negocio." />;
  }
  const businessStatus = detail.business.verification_status;
  const diagnostic = detail.access_diagnostic;
  const canEnterBusinessApp = diagnostic.business_can_access_surface;
  const copyBusinessId = async () => {
    await copyText(detail.business.id);
    setCopiedBusinessId(true);
    window.setTimeout(() => setCopiedBusinessId(false), 1800);
  };
  return (
    <section className="admin-web-split">
      {model.adminCanGoBack ? (
        <div className="admin-web-detail-backbar span-2">
          <button type="button" onClick={() => model.goBackAdminView()}>{model.adminBackLabel}</button>
        </div>
      ) : null}
      <div className="admin-web-panel">
        <h2>A-03 Detalle negocio</h2>
        <div className="admin-web-copy-box">
          <div>
            <span>Business ID</span>
            <code>{detail.business.id}</code>
          </div>
          <button type="button" onClick={() => void copyBusinessId()}>
            {copiedBusinessId ? "Copiado" : "Copiar ID"}
          </button>
        </div>
        <dl className="admin-web-dl">
          <dt>Nombre</dt><dd>{detail.business.business_name}</dd>
          <dt>Status</dt><dd>{detail.business.verification_status}</dd>
          <dt>Nivel</dt><dd>{detail.business.trust_level || "new"}</dd>
          <dt>Riesgo</dt><dd>{detail.business.risk_level}</dd>
          <dt>Rango por operacion</dt><dd>${detail.business.min_order_amount_usd || "20.00"} - ${detail.business.max_order_amount_usd || "100.00"}</dd>
          <dt>Limite diario</dt><dd>${detail.business.daily_limit_usd || "1000.00"}</dd>
          <dt>Ordenes activas</dt><dd>{detail.business.active_order_limit || 1}</dd>
          <dt>Telefono</dt><dd>{detail.business.phone || "-"}</dd>
        </dl>
        <div className="admin-web-business-status-actions" aria-label="Estado operativo del negocio">
          <h3>Estado operativo del negocio</h3>
          <p>Este control cambia si el negocio puede operar. El acceso del dueno se gestiona abajo.</p>
          <ReasonBox
            model={model}
            label="Razon obligatoria para cambiar estado del negocio"
            placeholder="Indica el motivo operativo antes de cambiar el estado"
          />
          <div className="admin-web-actions inline">
            {businessStatus === "approved" ? (
              <button disabled={!model.adminMutable} type="button" onClick={() => model.changeBusinessStatus("suspend")}>Suspender negocio</button>
            ) : null}
            {businessStatus === "suspended" ? (
              <button disabled={!model.adminMutable} type="button" onClick={() => model.changeBusinessStatus("reactivate")}>Reactivar negocio</button>
            ) : null}
            {businessStatus === "blocked" ? (
              <button disabled={!model.adminMutable} type="button" onClick={() => model.changeBusinessStatus("reactivate")}>Desbloquear negocio</button>
            ) : null}
            {businessStatus !== "blocked" ? (
              <button className="danger" disabled={!model.adminMutable} type="button" onClick={() => model.changeBusinessStatus("block")}>Bloquear negocio</button>
            ) : null}
          </div>
          {model.businessAccessActionFeedback?.target === "business" ? (
            <div
              className={`admin-web-access-action-feedback is-${model.businessAccessActionFeedback.tone}`}
              role={model.businessAccessActionFeedback.tone === "error" ? "alert" : "status"}
            >
              {model.businessAccessActionFeedback.message}
            </div>
          ) : null}
        </div>
      </div>
      <div className="admin-web-panel">
        <h3>Capacidad del negocio</h3>
        <div className="admin-web-toolbar">
          <label>
            <span>Nivel</span>
            <select
              disabled={!model.adminMutable}
              value={model.businessCapacityDraft.trust_level}
              onChange={(event) => model.setBusinessCapacityDraft({ ...model.businessCapacityDraft, trust_level: event.target.value })}
            >
              <option value="new">Nuevo</option>
              <option value="basic">Basico</option>
              <option value="plus">Plus</option>
              <option value="pro">Pro</option>
              <option value="premium">Premium</option>
            </select>
          </label>
          <label>
            <span>Minimo USD</span>
            <input
              disabled={!model.adminMutable}
              inputMode="decimal"
              value={model.businessCapacityDraft.min_order_amount_usd}
              onChange={(event) => model.setBusinessCapacityDraft({ ...model.businessCapacityDraft, min_order_amount_usd: event.target.value })}
            />
          </label>
          <label>
            <span>Maximo por operacion (USD)</span>
            <input
              disabled={!model.adminMutable}
              inputMode="decimal"
              value={model.businessCapacityDraft.max_order_amount_usd}
              onChange={(event) => model.setBusinessCapacityDraft({ ...model.businessCapacityDraft, max_order_amount_usd: event.target.value })}
            />
          </label>
          <label>
            <span>Capacidad maxima diaria (USD)</span>
            <input
              disabled={!model.adminMutable}
              inputMode="decimal"
              value={model.businessCapacityDraft.daily_limit_usd}
              onChange={(event) => model.setBusinessCapacityDraft({ ...model.businessCapacityDraft, daily_limit_usd: event.target.value })}
            />
          </label>
          <label>
            <span>Ordenes activas</span>
            <input
              disabled={!model.adminMutable}
              inputMode="numeric"
              value={String(model.businessCapacityDraft.active_order_limit)}
              onChange={(event) => model.setBusinessCapacityDraft({ ...model.businessCapacityDraft, active_order_limit: Number(event.target.value || "1") })}
            />
          </label>
        </div>
        <p className="admin-web-muted">
          Primero guarda la capacidad maxima diaria si quieres permitir un disponible operativo mayor al limite actual.
        </p>
        <button disabled={!model.adminMutable} type="button" onClick={() => model.submitBusinessCapacity()}>Guardar capacidad</button>
      </div>
      <div className="admin-web-panel">
        <h3>Capacidad operativa declarada</h3>
        <dl className="admin-web-dl">
          <dt>Disponible declarado</dt>
          <dd>${model.businessOperationalCapacity?.declared_available_capacity_usd ?? "0.00"}</dd>
          <dt>Reservado</dt>
          <dd>${model.businessOperationalCapacity?.reserved_capacity_usd ?? "0.00"}</dd>
          <dt>Restante efectivo</dt>
          <dd>${model.businessOperationalCapacity?.effective_available_capacity_usd ?? "0.00"}</dd>
          <dt>Limite diario</dt>
          <dd>${model.businessOperationalCapacity?.daily_limit_usd ?? "0.00"}</dd>
          <dt>Reservado activo</dt>
          <dd>${model.businessOperationalCapacity?.daily_reserved_usd ?? "0.00"}</dd>
          <dt>Consumido hoy</dt>
          <dd>${model.businessOperationalCapacity?.daily_consumed_usd ?? "0.00"}</dd>
          <dt>Restante diario</dt>
          <dd>${model.businessOperationalCapacity?.daily_remaining_usd ?? "0.00"}</dd>
          <dt>Reinicio</dt>
          <dd>00:00 UTC</dd>
        </dl>
        <h4>Ordenes que explican el limite diario</h4>
        {model.businessOperationalCapacity?.daily_orders.length ? (
          <Table headers={["Orden", "Monto", "Estado", "Fecha"]}>
            {model.businessOperationalCapacity.daily_orders.map((order) => (
              <tr key={order.order_id}>
                <td><code>{order.order_id}</code></td>
                <td>${order.amount_usd}</td>
                <td>{order.capacity_status}</td>
                <td>{dateText(order.consumed_at || order.created_at)}</td>
              </tr>
            ))}
          </Table>
        ) : (
          <Empty text="Sin reservas activas ni consumos del dia." />
        )}
        {model.businessOperationalCapacity?.daily_orders_truncated ? (
          <p>Se muestran las primeras 50 ordenes que explican el calculo.</p>
        ) : null}
        <div className="admin-web-toolbar">
          <label>
            <span>Disponible operativo ahora (USD)</span>
            <input
              disabled={!model.adminMutable}
              inputMode="decimal"
              value={model.businessOperationalCapacityDraft}
              onChange={(event) => model.setBusinessOperationalCapacityDraft(event.target.value)}
            />
          </label>
          <button
            disabled={!model.adminMutable}
            type="button"
            onClick={() => model.submitBusinessOperationalCapacity()}
          >
            Actualizar disponible
          </button>
        </div>
      </div>
      <div className="admin-web-panel">
        <h3>Documentos privados</h3>
        {detail.documents.length === 0 ? <Empty text="Sin documentos." /> : null}
        {detail.documents.map((file) => (
          <div className="admin-web-row" key={file.id}>
            <span>{file.file_type}</span>
            <small>{file.mime_type} - {file.size_bytes} bytes</small>
            <button disabled={!model.adminMutable} type="button" onClick={() => model.openDocument(file.id)}>URL corta</button>
          </div>
        ))}
      </div>
      <div className="admin-web-panel">
        <h3>Referidos</h3>
        <dl className="admin-web-dl">
          <dt>Codigo usado</dt><dd>{detail.referrals.code_used || "-"}</dd>
          <dt>Referido por</dt><dd>{detail.referrals.referred_by?.business_name || "-"}</dd>
          <dt>Creditos ganados</dt><dd>{detail.referrals.earned_credits}</dd>
          <dt>Restantes hasta el limite</dt><dd>{detail.referrals.remaining_bonus_credits}</dd>
        </dl>
        {detail.referrals.referred_businesses.length ? (
          <Table headers={["Negocio referido", "Estado", "Creditos"]}>
            {detail.referrals.referred_businesses.map((item) => (
              <tr key={item.business_id}>
                <td>{item.business_name}</td>
                <td>{item.status}</td>
                <td>{item.credits_awarded}</td>
              </tr>
            ))}
          </Table>
        ) : <Empty text="Este negocio aun no ha referido otros negocios." />}
        {detail.referrals.referred_businesses_truncated ? (
          <p className="admin-web-muted">Se muestran los 50 eventos de referidos mas recientes.</p>
        ) : null}
      </div>
      <div className="admin-web-panel">
        <Header
          title="Acceso Mini App Negocio"
          action={(
            <div className="admin-web-actions inline">
              <button type="button" onClick={() => void model.openBusiness(detail.business.id)}>Actualizar</button>
              <button
                disabled={!model.adminMutable || detail.business.verification_status !== "approved"}
                type="button"
                onClick={() => model.createBusinessOwnerAccessLink()}
              >
                Activar acceso
              </button>
            </div>
          )}
        />
        <p>El negocio solo puede entrar cuando esta aprobado y tiene un acceso activo para el Telegram del dueno.</p>
        <ReasonBox
          model={model}
          label="Razon obligatoria para cambiar el acceso"
          placeholder="Indica el motivo operativo antes de cambiar el acceso"
        />
        {model.businessAccessDiagnosticPending ? (
          <div className="admin-web-business-access-summary is-warning" role="status">
            <strong>Acceso actualizado</strong>
            <span>No pudimos confirmar el diagnostico actualizado. Usa Actualizar.</span>
          </div>
        ) : (
          <div className={`admin-web-business-access-summary ${canEnterBusinessApp ? "is-ok" : "is-warning"}`} role="status">
            <strong>{canEnterBusinessApp ? "Puede entrar" : "No puede entrar"}</strong>
            <span>{diagnostic.blocking_reason ? ACCESS_REASON_COPY[diagnostic.blocking_reason] || "Acceso no habilitado." : "Todas las puertas de acceso estan habilitadas."}</span>
            <dl className="admin-web-dl admin-web-business-access-gates">
              <dt>Negocio</dt><dd>{diagnostic.business_status}</dd>
              <dt>Dueno</dt><dd>{diagnostic.owner_user_status}{diagnostic.owner_role_valid ? "" : " - rol no valido"}</dd>
              <dt>Vinculo owner</dt><dd>{diagnostic.owner_link_status}{diagnostic.owner_link_role ? ` - ${diagnostic.owner_link_role}` : ""}</dd>
              <dt>Telegram</dt><dd>{diagnostic.telegram_matches === true ? "coincide" : diagnostic.telegram_matches === false ? "no coincide" : "sin vinculo verificable"}</dd>
            </dl>
            {diagnostic.owner_link_conflict ? <span>Hay otro owner activo. Revisa la vinculacion antes de operar.</span> : null}
            <span><strong>Accion recomendada:</strong> {ACCESS_ACTION_COPY[diagnostic.recommended_admin_action] || "Revisar vinculacion."}</span>
          </div>
        )}
        {model.businessAccessActionFeedback?.target === "access" ? (
          <div
            className={`admin-web-access-action-feedback is-${model.businessAccessActionFeedback.tone}`}
            role={model.businessAccessActionFeedback.tone === "error" ? "alert" : "status"}
          >
            {model.businessAccessActionFeedback.message}
          </div>
        ) : null}
        {detail.business.verification_status === "approved" && model.businessAccessLinks.length === 0 ? (
          <div className="admin-web-inline-warning">
            Negocio aprobado, pero el dueno aun no puede entrar. Pulsa Activar acceso para habilitar NODO Negocio.
          </div>
        ) : null}
        {detail.business.verification_status !== "approved" ? (
          <div className="admin-web-inline-warning">
            Primero aprueba el negocio. Luego podras activar el acceso del dueno.
          </div>
        ) : null}
        <Table headers={["Usuario", "Cuenta", "Telegram", "Rol", "Acceso", "Actualizado", "Acciones"]}>
          {model.businessAccessLinks.map((link) => (
            <tr key={link.id}>
              <td>{link.user?.username || link.user?.first_name || link.user_id}</td>
              <td>{link.user?.status || "-"}</td>
              <td>{link.telegram_id ? String(link.telegram_id) : link.telegram_id_masked || link.user?.telegram_id_masked || "-"}</td>
              <td>{link.role_in_business}</td>
              <td>{link.status}</td>
              <td>{dateText(link.updated_at || link.created_at)}</td>
              <td>
                <div className="admin-web-actions inline">
                  <button disabled={!model.adminMutable} type="button" onClick={() => model.changeBusinessAccessLink(link.id, "suspend")}>Suspender</button>
                  <button disabled={!model.adminMutable} type="button" onClick={() => model.changeBusinessAccessLink(link.id, "reactivate")}>Reactivar</button>
                  <button disabled={!model.adminMutable} type="button" onClick={() => model.changeBusinessAccessLink(link.id, "revoke")}>Revocar</button>
                  <button className="danger" disabled={!model.adminMutable} type="button" onClick={() => model.changeBusinessAccessLink(link.id, "block")}>Bloquear</button>
                  {link.user?.status === "blocked" ? (
                    <button disabled={!model.adminMutable} type="button" onClick={() => model.changeBusinessOwnerUserStatus(link.user_id, "reactivate")}>Desbloquear dueno</button>
                  ) : null}
                  {link.user?.status && link.user.status !== "active" && link.user.status !== "blocked" ? (
                    <button disabled={!model.adminMutable} type="button" onClick={() => model.changeBusinessOwnerUserStatus(link.user_id, "reactivate")}>Reactivar dueno</button>
                  ) : null}
                </div>
                {model.businessAccessActionFeedback?.target === `link:${link.id}`
                || model.businessAccessActionFeedback?.target === `owner:${link.user_id}` ? (
                  <div
                    className={`admin-web-access-action-feedback is-${model.businessAccessActionFeedback.tone}`}
                    role={model.businessAccessActionFeedback.tone === "error" ? "alert" : "status"}
                  >
                    {model.businessAccessActionFeedback.message}
                  </div>
                ) : null}
              </td>
            </tr>
          ))}
        </Table>
        {model.businessAccessLinks.length === 0 ? <Empty text="Sin accesos activos para este negocio." /> : null}
      </div>
    </section>
  );
}
