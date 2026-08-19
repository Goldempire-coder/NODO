import type { AdminWebModel } from "../../hooks/useAdminWebModel";
import type { CreditPurchase } from "../../types/credits";
import { Empty, Header, ReasonBox, Table } from "./AdminWebPrimitives";

export function CreditPurchases({ model }: { model: AdminWebModel }) {
  return (
    <section className="admin-web-panel admin-web-credit-purchases-panel">
      <Header title="A-04 Pagos de creditos" action={<button onClick={() => void model.loadCreditPurchases(model.creditFilter)} type="button">Aplicar filtro</button>} />
      <div className="admin-web-toolbar">
        <label><span>Status</span><input value={model.creditFilter} onChange={(event) => model.setCreditFilter(event.target.value)} /></label>
        <button type="button" onClick={() => model.setView("credit-adjustments")}>Ajuste manual</button>
      </div>
      <div className="admin-web-credit-purchases-list-scroll" role="region" aria-label="Lista de compras de creditos admin" tabIndex={0}>
        <Table headers={["Business", "Paquete", "Creditos", "Status", ""]}>
          {model.creditPurchases.map((item: CreditPurchase) => (
            <tr key={item.id}>
              <td>{item.business_id}</td>
              <td>{item.package_code}</td>
              <td>{item.credits_amount}</td>
              <td>{item.status}</td>
              <td><button type="button" onClick={() => { model.setSelectedCreditPurchase(item); model.setView("credit-detail"); }}>Detalle</button></td>
            </tr>
          ))}
        </Table>
      </div>
      {model.creditPurchasesNextCursor ? (
        <div className="admin-web-orders-list-actions">
          <button disabled={model.creditPurchasesLoadingMore} type="button" onClick={() => void model.loadMoreCreditPurchases()}>
            {model.creditPurchasesLoadingMore ? "Cargando..." : "Cargar mas"}
          </button>
        </div>
      ) : null}
      {model.creditPurchases.length === 0 ? <Empty text="Sin compras de creditos para ese filtro." /> : null}
    </section>
  );
}

export function CreditDetail({ model }: { model: AdminWebModel }) {
  const purchase = model.selectedCreditPurchase;
  if (!purchase) {
    return <Empty text="Selecciona una compra." />;
  }
  return (
    <section className="admin-web-split">
      <div className="admin-web-panel">
        <h2>A-05 Compra manual</h2>
        <dl className="admin-web-dl">
          <dt>Paquete</dt><dd>{purchase.package_code}</dd>
          <dt>Status</dt><dd>{purchase.status}</dd>
          <dt>Creditos</dt><dd>{purchase.credits_amount}</dd>
          <dt>Metodo</dt><dd>{purchase.payment_method}</dd>
        </dl>
      </div>
      <div className="admin-web-panel">
        <ReasonBox model={model} />
        <div className="admin-web-actions">
          <button disabled={!model.adminMutable} type="button" onClick={() => model.reviewCreditPurchase("approve")}>Aprobar</button>
          <button className="danger" disabled={!model.adminMutable} type="button" onClick={() => model.reviewCreditPurchase("reject")}>Rechazar</button>
        </div>
      </div>
    </section>
  );
}

export function CreditAdjustments({ model }: { model: AdminWebModel }) {
  return (
    <section className="admin-web-panel">
      <h2>A-13 Ajuste manual de creditos</h2>
      <div className="admin-web-form-grid">
        <label><span>Business ID</span><input value={model.adjustmentBusinessId} onChange={(event) => model.setAdjustmentBusinessId(event.target.value)} /></label>
        <label><span>Monto</span><input value={model.adjustmentAmount} onChange={(event) => model.setAdjustmentAmount(event.target.value)} inputMode="numeric" /></label>
        <label><span>Direccion</span><select value={model.adjustmentDirection} onChange={(event) => model.setAdjustmentDirection(event.target.value as "add" | "remove")}><option value="add">Add</option><option value="remove">Remove</option></select></label>
      </div>
      <ReasonBox model={model} />
      <button disabled={!model.adminMutable} type="button" onClick={() => model.submitAdjustment()}>Aplicar ajuste</button>
    </section>
  );
}
