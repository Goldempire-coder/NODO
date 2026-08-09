import type { AdminBusinessPublicationHold } from "../../types/admin";
import { dateText } from "./AdminWebPrimitives";

const STATUS_LABELS = {
  active: "Activo",
  released: "Liberado"
} as const;

export function AdminPublicationHoldPanel({
  error,
  hold,
  reason,
  releasing,
  onReasonChange,
  onRequestRelease
}: {
  error: string;
  hold: AdminBusinessPublicationHold | null | undefined;
  reason: string;
  releasing: boolean;
  onReasonChange: (value: string) => void;
  onRequestRelease: () => void;
}) {
  const canRelease = hold?.status === "active";

  return (
    <section className="admin-publication-hold" data-status={hold?.status || "none"} aria-label="Control de publicacion">
      <div className="admin-publication-hold__header">
        <div>
          <span>Publicacion del negocio</span>
          <strong>{hold ? STATUS_LABELS[hold.status] : "Sin hold"}</strong>
        </div>
        {hold ? <time>{dateText(hold.released_at || hold.created_at)}</time> : null}
      </div>

      {!hold ? (
        <p className="admin-web-muted">No hay hold operativo asociado a este ticket.</p>
      ) : (
        <div className="admin-publication-hold__details">
          <span><b>Hold</b><code>{hold.id}</code></span>
          <span><b>Ticket</b><code>{hold.support_ticket_id}</code></span>
          <span><b>Orden</b><code>{hold.order_id}</code></span>
          <span><b>Negocio</b><code>{hold.business_id}</code></span>
        </div>
      )}

      {canRelease ? (
        <div className="admin-publication-hold__action">
          <p>El negocio podra volver a publicar si no tiene otro bloqueo activo.</p>
          <label className="admin-web-field">
            <span>Razon obligatoria</span>
            <textarea
              disabled={releasing}
              maxLength={500}
              value={reason}
              onChange={(event) => onReasonChange(event.target.value)}
            />
          </label>
          {error ? <p className="admin-publication-hold__error" role="alert">{error}</p> : null}
          <button
            className="admin-web-button danger"
            type="button"
            disabled={releasing}
            onClick={onRequestRelease}
          >
            {releasing ? "Liberando..." : "Liberar publicacion"}
          </button>
        </div>
      ) : error ? (
        <p className="admin-publication-hold__error" role="alert">{error}</p>
      ) : null}
    </section>
  );
}
