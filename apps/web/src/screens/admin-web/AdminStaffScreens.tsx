"use client";

import type { AdminWebModel } from "../../hooks/useAdminWebModel";
import { dateText, Empty, Header, ReasonBox, Table } from "./AdminWebPrimitives";

const STAFF_ROLES = ["support_agent", "support_lead", "operations_readonly", "admin", "super_admin"];
const STAFF_PERMISSIONS = [
  "view_support_queue",
  "view_assigned_support_tickets",
  "reply_support_ticket",
  "assign_support_ticket",
  "escalate_support_ticket",
  "resolve_support_ticket",
  "close_support_ticket",
  "view_support_attachment",
  "view_users_masked",
  "view_businesses_masked",
  "view_orders_masked",
  "view_audit_limited",
  "view_metrics_limited"
];
const STAFF_SCOPES = ["assigned_only", "queue_scope", "category_scope", "global_readonly"];

export function StaffCenter({ model }: { model: AdminWebModel }) {
  return (
    <section className="admin-web-panel">
      <Header
        title="Staff interno"
        action={
          model.user.role === "super_admin" ? (
            <button type="button" onClick={() => model.setView("staff-invite")}>
              Invitar staff
            </button>
          ) : null
        }
      />
      <div className="admin-web-filters">
        <input
          value={model.staffFilters.q}
          onChange={(event) => model.setStaffFilters({ ...model.staffFilters, q: event.target.value })}
          placeholder="Buscar por nombre o username"
        />
        <select value={model.staffFilters.status} onChange={(event) => model.setStaffFilters({ ...model.staffFilters, status: event.target.value })}>
          <option value="">Todos los estados</option>
          <option value="active">active</option>
          <option value="suspended">suspended</option>
          <option value="revoked">revoked</option>
        </select>
        <select value={model.staffFilters.staff_role} onChange={(event) => model.setStaffFilters({ ...model.staffFilters, staff_role: event.target.value })}>
          <option value="">Todos los roles staff</option>
          {STAFF_ROLES.map((role) => (
            <option value={role} key={role}>
              {role}
            </option>
          ))}
        </select>
        <button type="button" onClick={() => void model.loadStaff(model.staffFilters.status)}>
          Filtrar
        </button>
      </div>
      {model.staff.length ? (
        <Table headers={["Nombre", "Usuario", "Staff role", "Status", "Permisos", "Ultima actividad", ""]}>
          {model.staff.map((item) => (
            <tr key={item.id}>
              <td>{item.display_name || "-"}</td>
              <td>{item.username || item.user_id}</td>
              <td>{item.staff_role}</td>
              <td>{item.status}</td>
              <td>{item.permission_count}</td>
              <td>{dateText(item.last_activity_at)}</td>
              <td>
                <button type="button" onClick={() => void model.openStaff(item.id)}>
                  Ver detalle
                </button>
              </td>
            </tr>
          ))}
        </Table>
      ) : (
        <Empty text="No hay perfiles staff con esos filtros." />
      )}
    </section>
  );
}

export function StaffDetail({ model }: { model: AdminWebModel }) {
  const staff = model.selectedStaff;
  if (!staff) {
    return <Empty text="Selecciona un perfil staff." />;
  }
  const activePermissions = staff.permissions.filter((item) => item.status === "active");
  return (
    <section className="admin-web-panel split">
      <div>
        <Header title="Detalle staff" />
        <dl className="admin-web-detail-list">
          <dt>Nombre</dt>
          <dd>{staff.display_name || "-"}</dd>
          <dt>Base role</dt>
          <dd>{staff.base_role}</dd>
          <dt>Staff role</dt>
          <dd>{staff.staff_role}</dd>
          <dt>Status</dt>
          <dd>{staff.status}</dd>
          <dt>Usuario</dt>
          <dd>{staff.user_id}</dd>
          <dt>Creado</dt>
          <dd>{dateText(staff.created_at)}</dd>
        </dl>
        <ReasonBox model={model} label="Reason para mutacion staff" />
        <div className="admin-web-actions">
          <button type="button" disabled={model.user.role !== "super_admin"} onClick={() => model.changeStaffStatus(staff.id, "activate")}>
            Activar
          </button>
          <button type="button" disabled={model.user.role !== "super_admin"} onClick={() => model.changeStaffStatus(staff.id, "suspend")}>
            Suspender
          </button>
          <button className="danger" type="button" disabled={model.user.role !== "super_admin"} onClick={() => model.changeStaffStatus(staff.id, "revoke")}>
            Revocar
          </button>
        </div>
      </div>
      <div>
        <Header title="Permisos activos" />
        {activePermissions.length ? (
          <Table headers={["Permiso", "Scope", "Valor"]}>
            {activePermissions.map((item, index) => (
              <tr key={`${item.permission}-${index}`}>
                <td>{item.permission}</td>
                <td>{item.scope}</td>
                <td>{item.scope_value || "-"}</td>
              </tr>
            ))}
          </Table>
        ) : (
          <Empty text="Sin permisos activos." />
        )}
        <button
          type="button"
          disabled={model.user.role !== "super_admin"}
          onClick={() =>
            model.replaceStaffPermissions(staff.id, [
              { permission: "view_assigned_support_tickets", scope: "assigned_only", scope_value: null },
              { permission: "reply_support_ticket", scope: "assigned_only", scope_value: null }
            ])
          }
        >
          Aplicar perfil soporte asignado
        </button>
        <Header title="Actividad limitada" />
        {model.staffActivity.length ? (
          <Table headers={["Evento", "Actor", "Recurso", "Fecha"]}>
            {model.staffActivity.map((item, index) => (
              <tr key={`${item.event_type}-${index}`}>
                <td>{item.event_type}</td>
                <td>{item.actor_role || "-"}</td>
                <td>{item.resource_type || "-"}</td>
                <td>{dateText(item.created_at)}</td>
              </tr>
            ))}
          </Table>
        ) : (
          <Empty text="Sin actividad reciente." />
        )}
      </div>
    </section>
  );
}

export function StaffInvite({ model }: { model: AdminWebModel }) {
  return (
    <section className="admin-web-panel">
      <Header title="Invitar staff" />
      <p>Solo super_admin puede crear o activar staff. El backend valida rol base, reason, permisos y audit.</p>
      <div className="admin-web-grid">
        <label className="admin-web-field">
          <span>target_user_id</span>
          <input value={model.staffInvite.target_user_id} onChange={(event) => model.setStaffInvite({ ...model.staffInvite, target_user_id: event.target.value })} />
        </label>
        <label className="admin-web-field">
          <span>target_telegram_id</span>
          <input value={model.staffInvite.target_telegram_id} onChange={(event) => model.setStaffInvite({ ...model.staffInvite, target_telegram_id: event.target.value })} />
        </label>
        <label className="admin-web-field">
          <span>target_username</span>
          <input value={model.staffInvite.target_username} onChange={(event) => model.setStaffInvite({ ...model.staffInvite, target_username: event.target.value })} />
        </label>
        <label className="admin-web-field">
          <span>staff_role</span>
          <select value={model.staffInvite.staff_role} onChange={(event) => model.setStaffInvite({ ...model.staffInvite, staff_role: event.target.value })}>
            {STAFF_ROLES.map((role) => (
              <option value={role} key={role}>
                {role}
              </option>
            ))}
          </select>
        </label>
        <label className="admin-web-field">
          <span>permiso inicial</span>
          <select value={model.staffInvite.permission} onChange={(event) => model.setStaffInvite({ ...model.staffInvite, permission: event.target.value })}>
            {STAFF_PERMISSIONS.map((permission) => (
              <option value={permission} key={permission}>
                {permission}
              </option>
            ))}
          </select>
        </label>
        <label className="admin-web-field">
          <span>scope</span>
          <select value={model.staffInvite.scope} onChange={(event) => model.setStaffInvite({ ...model.staffInvite, scope: event.target.value })}>
            {STAFF_SCOPES.map((scope) => (
              <option value={scope} key={scope}>
                {scope}
              </option>
            ))}
          </select>
        </label>
        <label className="admin-web-field">
          <span>scope_value</span>
          <input value={model.staffInvite.scope_value} onChange={(event) => model.setStaffInvite({ ...model.staffInvite, scope_value: event.target.value })} />
        </label>
        <label className="admin-web-field">
          <span>expires_at</span>
          <input value={model.staffInvite.expires_at} onChange={(event) => model.setStaffInvite({ ...model.staffInvite, expires_at: event.target.value })} placeholder="ISO timestamp opcional" />
        </label>
      </div>
      <ReasonBox model={model} label="Reason obligatorio" />
      <button type="button" disabled={model.user.role !== "super_admin"} onClick={() => void model.submitStaffInvite()}>
        Crear invitacion
      </button>
    </section>
  );
}
