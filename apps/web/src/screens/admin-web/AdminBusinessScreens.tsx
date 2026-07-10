import type { AdminWebModel } from "../../hooks/useAdminWebModel";
import { businessName, dateText, Empty, Header, ReasonBox, Table } from "./AdminWebPrimitives";

export function Businesses({ model }: { model: AdminWebModel }) {
  return (
    <section className="admin-web-panel">
      <Header title="A-02 Negocios" action={<button onClick={() => void model.loadBusinesses(model.businessFilter)} type="button">Aplicar filtro</button>} />
      <div className="admin-web-toolbar">
        <label><span>Status</span><input value={model.businessFilter} onChange={(event) => model.setBusinessFilter(event.target.value)} placeholder="pending, approved..." /></label>
        <button type="button" onClick={() => void model.loadPendingBusinesses()}>Pendientes</button>
      </div>
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
      {model.businesses.length === 0 ? <Empty text="No hay negocios para el filtro actual." /> : null}
    </section>
  );
}

export function BusinessDetail({ model }: { model: AdminWebModel }) {
  const detail = model.selectedBusiness;
  if (!detail) {
    return <Empty text="Selecciona un negocio." />;
  }
  return (
    <section className="admin-web-split">
      <div className="admin-web-panel">
        <h2>A-03 Detalle negocio</h2>
        <dl className="admin-web-dl">
          <dt>Nombre</dt><dd>{detail.business.business_name}</dd>
          <dt>Status</dt><dd>{detail.business.verification_status}</dd>
          <dt>Riesgo</dt><dd>{detail.business.risk_level}</dd>
          <dt>Telefono</dt><dd>{detail.business.phone || "-"}</dd>
        </dl>
        <ReasonBox model={model} />
        <div className="admin-web-actions">
          <button disabled={!model.adminMutable} type="button" onClick={() => model.reviewBusiness("approve")}>Aprobar</button>
          <button className="danger" disabled={!model.adminMutable} type="button" onClick={() => model.reviewBusiness("reject")}>Rechazar</button>
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
    </section>
  );
}
