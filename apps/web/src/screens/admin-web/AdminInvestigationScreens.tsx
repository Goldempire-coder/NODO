import type { AdminWebModel } from "../../hooks/useAdminWebModel";
import type { AdminInvestigationSearchItem } from "../../types/admin";
import { dateText, Empty, Header } from "./AdminWebPrimitives";

const GROUPS: Array<{ key: keyof AdminWebModel["investigationResults"]["groups"]; label: string }> = [
  { key: "users", label: "Clientes" },
  { key: "businesses", label: "Negocios" },
  { key: "business_intakes", label: "Intake" },
  { key: "orders", label: "Ordenes" },
  { key: "support_tickets", label: "Soporte" }
];

function ResultCard({ item, model }: { item: AdminInvestigationSearchItem; model: AdminWebModel }) {
  return (
    <article className="admin-web-investigation-result">
      <div>
        <div className="admin-web-investigation-result__top">
          <strong>{item.title}</strong>
          {item.status ? <span>{item.status}</span> : null}
        </div>
        <p>{item.subtitle}</p>
        <small>
          {item.reference ? `${item.reference} - ` : ""}
          {item.matched_on.join(", ")}
          {item.created_at ? ` - ${dateText(item.created_at)}` : ""}
        </small>
      </div>
      <div className="admin-web-investigation-result__actions">
        <button type="button" onClick={() => void model.openInvestigationResult(item)}>Abrir</button>
        <button type="button" onClick={() => void model.openInvestigationCaseFile(item)}>Investigar</button>
      </div>
    </article>
  );
}

export function InvestigationSearch({ model }: { model: AdminWebModel }) {
  const total = Object.values(model.investigationResults.result_counts).reduce((sum, value) => sum + value, 0);

  return (
    <section className="admin-web-panel admin-web-investigation">
      <Header title="Buscar" />
      <p className="admin-web-muted">Busca por telefono, usuario, codigo de orden, ID, nombre de negocio, codigo de referencia o ticket.</p>
      <form
        className="admin-web-investigation-search"
        onSubmit={(event) => {
          event.preventDefault();
          void model.searchInvestigation();
        }}
      >
        <input
          aria-label="Buscar en el dashboard"
          value={model.investigationQuery}
          onChange={(event) => model.setInvestigationQuery(event.target.value)}
          placeholder="Ej. telefono, NODO-AB12CD34, @usuario, REF..."
        />
        <button type="submit">Buscar</button>
      </form>
      {model.investigationSearched && total === 0 ? <Empty text="No encontramos resultados con esa pista." /> : null}
      <div className="admin-web-investigation-groups">
        {GROUPS.map((group) => {
          const items = model.investigationResults.groups[group.key];
          if (!items.length) {
            return null;
          }
          return (
            <div className="admin-web-investigation-group" key={group.key}>
              <h3>{group.label}</h3>
              <div className="admin-web-investigation-results">
                {items.map((item) => <ResultCard key={`${item.type}-${item.id}`} item={item} model={model} />)}
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}
