"use client";

import type { AdminWebModel } from "../../hooks/useAdminWebModel";
import { AdminWebScreens } from "./AdminWebScreens";

function priorityLabel(priority: string) {
  const labels: Record<string, string> = {
    info: "Info",
    attention: "Atencion",
    high: "Alta",
    critical: "Critica"
  };
  return labels[priority] || priority;
}

export function AdminWebShell({ model }: { model: AdminWebModel }) {
  return (
    <main className="admin-web-shell">
      <aside className="admin-web-sidebar" aria-label="Admin navigation">
        <div className="admin-web-brand">
          <span>NODO</span>
          <small>Admin Web</small>
        </div>
        <nav className="admin-web-nav">
          {model.navigation.map((item) => (
            <button
              className={model.view === item.view ? "is-active" : ""}
              key={item.view}
              type="button"
              onClick={() => void item.action()}
            >
              <span>{item.label}</span>
              {item.badge ? <strong className="admin-web-nav-badge">{item.badge}</strong> : null}
            </button>
          ))}
        </nav>
      </aside>

      <section className="admin-web-main">
        <header className="admin-web-topbar">
          <div>
            <p>Panel operativo</p>
            <h1>Admin Web</h1>
          </div>
          <div className="admin-web-topbar-actions">
            <div className="admin-web-notifications">
              <button
                aria-expanded={model.adminNotificationsPanelOpen}
                aria-label="Notificaciones operativas"
                className="admin-web-notification-button"
                type="button"
                onClick={() => void model.toggleAdminNotifications()}
              >
                <span>Notificaciones</span>
                {model.adminNotificationsUnreadCount > 0 ? <strong>{model.adminNotificationsUnreadCount}</strong> : null}
              </button>
              {model.adminNotificationsUnreadState === "stale" ? <small className="admin-web-notification-stale" role="status">Contador sin actualizar</small> : null}
              {model.adminNotificationsPanelOpen ? (
                <section className="admin-web-notification-panel" aria-label="Bandeja de notificaciones operativas">
                  <div className="admin-web-notification-panel__header">
                    <strong>Operacion</strong>
                    <button type="button" onClick={() => void model.loadAdminNotifications("unread")}>
                      Actualizar
                    </button>
                  </div>
                  {model.adminNotifications.length ? (
                    <div className="admin-web-notification-list">
                      {model.adminNotifications.map((notification) => {
                        const busy = model.adminNotificationBusyId === notification.id;
                        return (
                          <article className={`admin-web-notification-card priority-${notification.priority}`} key={notification.id}>
                            <div>
                              <span>{priorityLabel(notification.priority)}</span>
                              <time dateTime={notification.last_seen_at}>{new Date(notification.last_seen_at).toLocaleString()}</time>
                            </div>
                            <button type="button" onClick={() => void model.openAdminNotification(notification)} disabled={busy}>
                              <strong>{notification.title}</strong>
                              <small>{notification.summary}</small>
                            </button>
                            <div className="admin-web-notification-card__actions">
                              {model.adminMutable ? (
                                <>
                                  <button type="button" onClick={() => void model.markAdminNotificationRead(notification.id)} disabled={busy}>
                                    Leida
                                  </button>
                                  <button type="button" onClick={() => void model.dismissAdminNotification(notification.id)} disabled={busy}>
                                    Descartar
                                  </button>
                                  <button type="button" onClick={() => void model.resolveAdminNotification(notification.id)} disabled={busy}>
                                    Resolver
                                  </button>
                                </>
                              ) : null}
                            </div>
                          </article>
                        );
                      })}
                    </div>
                  ) : (
                    <p className="admin-web-notification-empty">Sin notificaciones pendientes.</p>
                  )}
                </section>
              ) : null}
            </div>
            <div className="admin-web-session">
              <span>{model.user.first_name || model.user.username || "Admin"}</span>
              <strong>{model.user.role}</strong>
            </div>
          </div>
        </header>

        <div className={`admin-web-notice ${model.busy ? "is-busy" : ""}`} role="status">
          {model.busy ? "Procesando..." : model.notice}
        </div>

        {model.pendingAction ? (
          <section className="admin-web-confirm" aria-live="polite">
            <div>
              <strong>{model.pendingAction.title}</strong>
              <p>{model.pendingAction.detail}</p>
            </div>
            <div className="admin-web-actions">
              <button type="button" onClick={() => model.setPendingAction(null)}>
                Cancelar
              </button>
              <button className="danger" type="button" onClick={() => void model.confirmPendingAction()}>
                Confirmar
              </button>
            </div>
          </section>
        ) : null}

        <AdminWebScreens model={model} />
      </section>
    </main>
  );
}
