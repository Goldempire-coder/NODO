import type { AdminWebModel } from "../../hooks/useAdminWebModel";
import { dateText, Empty, Header, ReasonBox, Table } from "./AdminWebPrimitives";

function userName(user: { first_name?: string | null; last_name?: string | null; username?: string | null }) {
  const fullName = [user.first_name, user.last_name].filter(Boolean).join(" ").trim();
  return fullName || user.username || "Usuario";
}

function userContact(user: { phone?: string | null; phone_masked?: string | null; telegram_id?: number | null; telegram_id_masked?: string | null }) {
  return {
    phone: user.phone || user.phone_masked || "-",
    telegram: user.telegram_id ? String(user.telegram_id) : user.telegram_id_masked || "-"
  };
}

export function Users({ model }: { model: AdminWebModel }) {
  return (
    <section className="admin-web-panel">
      <Header title="A-10 Usuarios" action={<button onClick={() => void model.loadUsers()} type="button">Buscar</button>} />
      <div className="admin-web-toolbar">
        <label>
          <span>Telefono</span>
          <input value={model.userFilters.phone} onChange={(event) => model.setUserFilters({ ...model.userFilters, phone: event.target.value })} placeholder="+58..." />
        </label>
        <label>
          <span>Telegram ID</span>
          <input value={model.userFilters.telegram_id} onChange={(event) => model.setUserFilters({ ...model.userFilters, telegram_id: event.target.value })} placeholder="123456789" />
        </label>
        <label>
          <span>Username</span>
          <input value={model.userFilters.username} onChange={(event) => model.setUserFilters({ ...model.userFilters, username: event.target.value })} placeholder="@usuario" />
        </label>
        <label>
          <span>Rol</span>
          <input value={model.userFilters.role} onChange={(event) => model.setUserFilters({ ...model.userFilters, role: event.target.value })} placeholder="remitter, business_owner..." />
        </label>
        <label>
          <span>Estado</span>
          <input value={model.userFilters.status} onChange={(event) => model.setUserFilters({ ...model.userFilters, status: event.target.value })} placeholder="active, restricted..." />
        </label>
      </div>
      <Table headers={["Usuario", "Telefono", "Telegram", "Rol", "Estado", "Ultima vez", ""]}>
        {model.users.map((item) => {
          const contact = userContact(item);
          return (
            <tr key={item.id}>
              <td>{userName(item)}</td>
              <td>{contact.phone}</td>
              <td>{contact.telegram}</td>
              <td>{item.role}</td>
              <td>{item.status}</td>
              <td>{dateText(item.last_seen_at || item.updated_at || item.created_at)}</td>
              <td><button type="button" onClick={() => void model.openUser(item.id)}>Abrir</button></td>
            </tr>
          );
        })}
      </Table>
      {model.users.length === 0 ? <Empty text="Busca usuarios por telefono, Telegram ID, username, rol o estado." /> : null}
    </section>
  );
}

export function UserDetail({ model }: { model: AdminWebModel }) {
  const detail = model.selectedUser;
  if (!detail) {
    return <Empty text="Selecciona un usuario." />;
  }
  const contact = userContact(detail.user);
  return (
    <section className="admin-web-split">
      <div className="admin-web-panel">
        <h2>Detalle usuario</h2>
        <dl className="admin-web-dl">
          <dt>Nombre</dt><dd>{userName(detail.user)}</dd>
          <dt>Telefono</dt><dd>{contact.phone}</dd>
          <dt>Telegram</dt><dd>{contact.telegram}</dd>
          <dt>Rol</dt><dd>{detail.user.role}</dd>
          <dt>Estado</dt><dd>{detail.user.status}</dd>
          <dt>Terminos</dt><dd>{detail.user.terms_version || "-"} {dateText(detail.user.terms_accepted_at)}</dd>
        </dl>
        <ReasonBox model={model} />
        <div className="admin-web-actions">
          <button disabled={!model.adminMutable || !detail.capabilities.can_mutate_status} type="button" onClick={() => model.changeUserStatus(detail.user.id, "suspend")}>Suspender</button>
          <button disabled={!model.adminMutable || !detail.capabilities.can_mutate_status} type="button" onClick={() => model.changeUserStatus(detail.user.id, "reactivate")}>Reactivar</button>
          <button className="danger" disabled={!model.adminMutable || !detail.capabilities.can_mutate_status} type="button" onClick={() => model.changeUserStatus(detail.user.id, "block")}>Bloquear</button>
        </div>
      </div>
      <div className="admin-web-panel">
        <h3>Accesos negocio</h3>
        <Table headers={["Negocio", "Rol", "Estado", "Telegram", "Actualizado"]}>
          {detail.access_links.map((link) => (
            <tr key={link.id}>
              <td>{link.business?.business_name || link.business?.display_name || link.business_id}</td>
              <td>{link.role_in_business}</td>
              <td>{link.status}</td>
              <td>{link.telegram_id ? String(link.telegram_id) : link.telegram_id_masked || "-"}</td>
              <td>{dateText(link.updated_at || link.created_at)}</td>
            </tr>
          ))}
        </Table>
        {detail.access_links.length === 0 ? <Empty text="Este usuario no tiene accesos de negocio." /> : null}
      </div>
    </section>
  );
}
