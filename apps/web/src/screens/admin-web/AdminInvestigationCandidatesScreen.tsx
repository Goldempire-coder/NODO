import type { AdminWebModel } from "../../hooks/useAdminWebModel";
import type { AdminInvestigationCandidateFilters } from "../../types/admin";
import { dateText, Empty, Header } from "./AdminWebPrimitives";

const ORDER_STATUSES = [
  "waiting_payment",
  "payment_reported",
  "payment_rejected",
  "payment_confirmed",
  "delivered",
  "completed",
  "cancelled",
  "disputed"
];

function Field({
  label,
  name,
  model,
  type = "text"
}: {
  label: string;
  name: keyof AdminInvestigationCandidateFilters;
  model: AdminWebModel;
  type?: string;
}) {
  return (
    <label>
      {label}
      <input
        type={type}
        value={model.candidateFilters[name]}
        onChange={(event) => model.setCandidateFilter(name, event.target.value)}
      />
    </label>
  );
}

export function AdminInvestigationCandidatesScreen({ model }: { model: AdminWebModel }) {
  const results = model.candidateResults;
  return (
    <section className="admin-web-panel admin-web-investigation admin-web-candidates">
      <Header title="Filtros avanzados" />
      <p className="admin-web-muted">Combina al menos dos pistas. Todos los filtros deben coincidir.</p>
      <form
        className="admin-web-form-grid admin-web-candidates__filters"
        onSubmit={(event) => {
          event.preventDefault();
          void model.searchInvestigationCandidates();
        }}
      >
        <Field label="Cliente o telefono" name="client_hint" model={model} />
        <Field label="Negocio o referencia" name="business_hint" model={model} />
        <label>
          Estado de orden
          <select
            value={model.candidateFilters.order_status}
            onChange={(event) => model.setCandidateFilter("order_status", event.target.value)}
          >
            <option value="">Cualquier estado</option>
            {ORDER_STATUSES.map((status) => <option key={status} value={status}>{status}</option>)}
          </select>
        </label>
        <Field label="Monto desde" name="amount_min_usd" model={model} type="number" />
        <Field label="Monto hasta" name="amount_max_usd" model={model} type="number" />
        <label>
          Soporte
          <select
            value={model.candidateFilters.support_status_group}
            onChange={(event) => model.setCandidateFilter("support_status_group", event.target.value)}
          >
            <option value="all">Todos</option>
            <option value="active">Activos</option>
            <option value="archived">Archivados</option>
          </select>
        </label>
        <Field label="Fecha desde" name="created_from" model={model} type="datetime-local" />
        <Field label="Fecha hasta" name="created_to" model={model} type="datetime-local" />
        <div className="admin-web-candidates__submit">
          <button type="submit" disabled={model.candidateLoading}>
            {model.candidateLoading ? "Buscando..." : "Buscar candidatos"}
          </button>
          <button type="button" onClick={() => model.setView("investigation")}>Busqueda rapida</button>
        </div>
      </form>

      {results && results.items.length === 0 ? <Empty text="No encontramos ordenes con todos esos filtros." /> : null}
      <div className="admin-web-investigation-results admin-web-candidates__results">
        {results?.items.map((candidate) => (
          <article className="admin-web-investigation-result" key={candidate.order_id}>
            <div>
              <div className="admin-web-investigation-result__top">
                <strong>{candidate.public_order_code}</strong>
                <span>{candidate.status}</span>
              </div>
              <p>{candidate.business.name} · {candidate.client.display_name} · ${candidate.amount_usd}</p>
              <small>
                {dateText(candidate.created_at)} · {candidate.signals.join(", ")}
                {candidate.support_ticket_count ? ` · ${candidate.support_ticket_count} ticket(s)` : ""}
              </small>
            </div>
            <div className="admin-web-investigation-result__actions">
              <button type="button" onClick={() => void model.openCandidateOrder(candidate.order_id)}>Abrir orden</button>
              <button type="button" onClick={() => void model.investigateCandidate(candidate)}>Investigar</button>
            </div>
          </article>
        ))}
      </div>
      {results?.next_cursor ? (
        <button
          type="button"
          disabled={model.candidateLoading}
          onClick={() => void model.searchInvestigationCandidates({ append: true })}
        >
          {model.candidateLoading ? "Cargando..." : "Cargar mas"}
        </button>
      ) : null}
      {results?.disclaimer ? <p className="admin-web-muted">{results.disclaimer}</p> : null}
    </section>
  );
}
