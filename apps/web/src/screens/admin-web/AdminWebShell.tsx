"use client";

import type { AdminWebModel } from "../../hooks/useAdminWebModel";
import { AdminWebScreens } from "./AdminWebScreens";

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
              {item.label}
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
          <div className="admin-web-session">
            <span>{model.user.first_name || model.user.username || "Admin"}</span>
            <strong>{model.user.role}</strong>
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
