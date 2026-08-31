"use client";

import { useEffect, useRef } from "react";
import type { AdminWebModel } from "../../hooks/useAdminWebModel";
import { AdminWebScreens } from "./AdminWebScreens";

type AdminNavigationItem = AdminWebModel["navigation"][number];

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
  const confirmCancelRef = useRef<HTMLButtonElement>(null);
  const previousFocusRef = useRef<HTMLElement | null>(null);
  const confirmationOpenRef = useRef(false);
  const navigationGroups = model.navigation.reduce<Array<{ label: string; items: AdminNavigationItem[] }>>((groups, item) => {
    const existing = groups.find((group) => group.label === item.group);
    if (existing) {
      existing.items.push(item);
      return groups;
    }
    groups.push({ label: item.group, items: [item] });
    return groups;
  }, []);

  useEffect(() => {
    const isOpen = Boolean(model.pendingAction);
    if (isOpen && !confirmationOpenRef.current) {
      previousFocusRef.current = document.activeElement instanceof HTMLElement ? document.activeElement : null;
      confirmCancelRef.current?.focus();
    } else if (!isOpen && confirmationOpenRef.current) {
      previousFocusRef.current?.focus();
      previousFocusRef.current = null;
    }
    confirmationOpenRef.current = isOpen;
  }, [model.pendingAction]);

  return (
    <main className="admin-web-shell">
      <aside className="admin-web-sidebar" aria-label="Admin navigation">
        <div className="admin-web-brand">
          <span>NODO</span>
          <small>Admin Web</small>
        </div>
        <nav className="admin-web-nav">
          {navigationGroups.map((group) => (
            <div className="admin-web-nav-group" key={group.label}>
              <span className="admin-web-nav-group-label">{group.label}</span>
              {group.items.map((item) => (
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
            </div>
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
                    <div
                      aria-label="Lista de notificaciones operativas"
                      className="admin-web-notification-list"
                      role="region"
                      tabIndex={0}
                    >
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
                  {model.adminNotificationsNextCursor ? (
                    <div className="admin-web-orders-list-actions">
                      <button
                        disabled={model.adminNotificationsLoadingMore}
                        type="button"
                        onClick={() => void model.loadMoreAdminNotifications()}
                      >
                        {model.adminNotificationsLoadingMore ? "Cargando..." : "Cargar mas"}
                      </button>
                    </div>
                  ) : null}
                </section>
              ) : null}
            </div>
            <div className="admin-web-session">
              <span>{model.user.first_name || model.user.username || "Admin"}</span>
              <strong>{model.user.role}</strong>
              <button
                className="admin-web-session-logout"
                disabled={model.loggingOut}
                type="button"
                onClick={() => void model.logout()}
              >
                {model.loggingOut ? "Cerrando..." : "Cerrar sesion"}
              </button>
            </div>
          </div>
        </header>

        <div className={`admin-web-notice ${model.busy ? "is-busy" : ""}`} role="status">
          {model.busy ? "Procesando..." : model.notice}
        </div>

        <AdminWebScreens model={model} />

        {model.pendingAction ? (
          <section
            aria-describedby="admin-web-confirm-detail"
            aria-labelledby="admin-web-confirm-title"
            className="admin-web-confirm"
            role="dialog"
          >
            <div>
              <strong id="admin-web-confirm-title">{model.pendingAction.title}</strong>
              <p id="admin-web-confirm-detail">{model.pendingAction.detail}</p>
            </div>
            <div className="admin-web-actions">
              <button ref={confirmCancelRef} type="button" onClick={() => model.setPendingAction(null)}>
                Cancelar
              </button>
              <button className="danger" type="button" onClick={() => void model.confirmPendingAction()}>
                Confirmar
              </button>
            </div>
          </section>
        ) : null}
      </section>
    </main>
  );
}
