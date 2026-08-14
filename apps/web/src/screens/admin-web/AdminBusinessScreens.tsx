import { useState } from "react";
import type { AdminWebModel } from "../../hooks/useAdminWebModel";
import { businessName, dateText, Empty, Header, Table } from "./AdminWebPrimitives";

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
      <div className="admin-web-businesses-list-scroll">
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
  const copyBusinessId = async () => {
    await copyText(detail.business.id);
    setCopiedBusinessId(true);
    window.setTimeout(() => setCopiedBusinessId(false), 1800);
  };
  return (
    <section className="admin-web-split">
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
            <span>Maximo USD</span>
            <input
              disabled={!model.adminMutable}
              inputMode="decimal"
              value={model.businessCapacityDraft.max_order_amount_usd}
              onChange={(event) => model.setBusinessCapacityDraft({ ...model.businessCapacityDraft, max_order_amount_usd: event.target.value })}
            />
          </label>
          <label>
            <span>Diario USD</span>
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
            <span>Disponible ahora (USD)</span>
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
        <Header title="Acceso Mini App Negocio" action={<button disabled={!model.adminMutable} type="button" onClick={() => model.createBusinessOwnerAccessLink()}>Crear link owner</button>} />
        <p>El acceso se gobierna por backend. El bot solo abre la Mini App cuando el negocio ya esta aprobado y vinculado.</p>
        <Table headers={["Usuario", "Telegram", "Rol", "Estado", "Actualizado", "Acciones"]}>
          {model.businessAccessLinks.map((link) => (
            <tr key={link.id}>
              <td>{link.user?.username || link.user?.first_name || link.user_id}</td>
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
                </div>
              </td>
            </tr>
          ))}
        </Table>
        {model.businessAccessLinks.length === 0 ? <Empty text="No hay links de acceso para este negocio." /> : null}
      </div>
    </section>
  );
}
