import type { ReactNode } from "react";
import type { AdminWebModel, BusinessSummaryForAdmin } from "../../hooks/useAdminWebModel";

export function dateText(value?: string | null) {
  if (!value) {
    return "-";
  }
  return new Date(value).toLocaleString();
}

export function businessName(item: BusinessSummaryForAdmin) {
  return item.business_name || item.display_name || "Negocio";
}

export function Empty({ text }: { text: string }) {
  return <div className="admin-web-empty">{text}</div>;
}

export function ReasonBox({ model, label = "Nota admin opcional" }: { model: AdminWebModel; label?: string }) {
  return (
    <label className="admin-web-field">
      <span>{label}</span>
      <textarea value={model.reason} onChange={(event) => model.setReason(event.target.value)} placeholder="Opcional: agrega contexto interno para auditoria" />
    </label>
  );
}

export function Metric({ label, value }: { label: string; value?: number }) {
  return (
    <div className="admin-web-metric">
      <span>{label}</span>
      <strong>{value ?? 0}</strong>
    </div>
  );
}

export function Placeholder({ title }: { title: string }) {
  return (
    <section className="admin-web-panel">
      <h2>{title}</h2>
      <p>Placeholder gobernado. No ejecuta mutaciones ni inventa datos hasta que el endpoint correspondiente este implementado.</p>
    </section>
  );
}

export function Header({ title, action }: { title: string; action?: ReactNode }) {
  return (
    <div className="admin-web-panel-header">
      <h2>{title}</h2>
      {action}
    </div>
  );
}

export function Table({ headers, children }: { headers: string[]; children: ReactNode }) {
  return (
    <div className="admin-web-table-wrap">
      <table className="admin-web-table">
        <thead>
          <tr>{headers.map((header) => <th key={header}>{header}</th>)}</tr>
        </thead>
        <tbody>{children}</tbody>
      </table>
    </div>
  );
}
