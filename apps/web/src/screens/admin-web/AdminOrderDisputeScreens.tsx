import type { AdminWebModel } from "../../hooks/useAdminWebModel";
import type { AdminDisputeSummary, AdminOrderSummary } from "../../types/admin";
import { dateText, Empty, Header, ReasonBox, Table } from "./AdminWebPrimitives";

export function Orders({ model }: { model: AdminWebModel }) {
  return (
    <section className="admin-web-panel">
      <Header title="A-11 Ordenes" action={<button onClick={() => void model.loadOrders(model.orderFilter)} type="button">Aplicar filtro</button>} />
      <div className="admin-web-toolbar">
        <label><span>Status</span><input value={model.orderFilter} onChange={(event) => model.setOrderFilter(event.target.value)} placeholder="disputed, delivered..." /></label>
      </div>
      <Table headers={["Codigo", "Status", "Monto", "Metodo", ""]}>
        {model.orders.map((item: AdminOrderSummary) => (
          <tr key={item.id}>
            <td>{item.public_order_code}</td>
            <td>{item.status}</td>
            <td>{item.amount_usd} USD</td>
            <td>{item.payment_method_snapshot}</td>
            <td><button type="button" onClick={() => void model.openOrder(item.id)}>Detalle</button></td>
          </tr>
        ))}
      </Table>
      {model.orders.length === 0 ? <Empty text="No hay ordenes para el filtro actual." /> : null}
    </section>
  );
}

export function OrderDetail({ model }: { model: AdminWebModel }) {
  const order = model.selectedOrder?.order as AdminOrderSummary | undefined;
  const paymentReport = model.selectedOrder?.payment_report as { status?: string; payment_type?: string; payment_amount?: string; created_at?: string } | undefined;
  const timeline = model.selectedOrder?.timeline as { event_type?: string; to_status?: string; created_at?: string }[] | undefined;
  return (
    <section className="admin-web-split">
      <div className="admin-web-panel">
        <h2>Detalle de orden</h2>
        {order ? (
          <dl className="admin-web-dl">
            <dt>Codigo</dt><dd>{order.public_order_code}</dd>
            <dt>Status</dt><dd>{order.status}</dd>
            <dt>Negocio</dt><dd>{order.business_id}</dd>
            <dt>Remitente</dt><dd>{order.remitter_user_id}</dd>
            <dt>Monto</dt><dd>{order.amount_usd} USD</dd>
            <dt>Metodo</dt><dd>{order.payment_method_snapshot}</dd>
            <dt>Entrega</dt><dd>{order.delivery_method_snapshot}</dd>
          </dl>
        ) : <Empty text="Selecciona una orden." />}
      </div>
      <div className="admin-web-panel">
        <h3>Reporte y timeline</h3>
        {paymentReport ? (
          <dl className="admin-web-dl">
            <dt>Reporte</dt><dd>{paymentReport.status || "-"}</dd>
            <dt>Tipo</dt><dd>{paymentReport.payment_type || "-"}</dd>
            <dt>Monto</dt><dd>{paymentReport.payment_amount || "-"}</dd>
          </dl>
        ) : <p className="admin-web-muted">Sin reporte de pago.</p>}
        {(timeline || []).slice(0, 6).map((event, index) => (
          <div className="admin-web-row" key={`${event.event_type}_${index}`}>
            <span>{event.event_type || "event"}</span>
            <small>{event.to_status || "-"} - {dateText(event.created_at)}</small>
          </div>
        ))}
      </div>
    </section>
  );
}

export function Disputes({ model }: { model: AdminWebModel }) {
  return (
    <section className="admin-web-panel">
      <Header title="A-06 Disputas" action={<button onClick={() => void model.loadDisputes(model.disputeFilter)} type="button">Aplicar filtro</button>} />
      <div className="admin-web-toolbar">
        <label><span>Status</span><input value={model.disputeFilter} onChange={(event) => model.setDisputeFilter(event.target.value)} placeholder="open, in_review..." /></label>
      </div>
      <Table headers={["Orden", "Status", "Motivo", "Creada", ""]}>
        {model.disputes.map((item: AdminDisputeSummary) => (
          <tr key={item.id}>
            <td>{item.order_id}</td>
            <td>{item.status}</td>
            <td>{item.reason}</td>
            <td>{dateText(item.created_at)}</td>
            <td><button type="button" onClick={() => void model.openDispute(item.id)}>Abrir</button></td>
          </tr>
        ))}
      </Table>
      {model.disputes.length === 0 ? <Empty text="No hay disputas para ese filtro." /> : null}
    </section>
  );
}

export function DisputeDetail({ model }: { model: AdminWebModel }) {
  const detail = model.selectedDispute;
  if (!detail) {
    return <Empty text="Selecciona una disputa." />;
  }
  return (
    <section className="admin-web-split">
      <div className="admin-web-panel">
        <h2>A-07 Disputa</h2>
        <dl className="admin-web-dl">
          <dt>Status</dt><dd>{detail.dispute.status}</dd>
          <dt>Motivo</dt><dd>{detail.dispute.reason}</dd>
          <dt>Estado previo</dt><dd>{detail.dispute.previous_order_status}</dd>
          <dt>Resolucion</dt><dd>{detail.dispute.resolution_type || "-"}</dd>
        </dl>
      </div>
      <div className="admin-web-panel">
        <h3>Resolver</h3>
        <label className="admin-web-field">
          <span>Resolution type</span>
          <select value={model.resolutionType} onChange={(event) => model.setResolutionType(event.target.value)}>
            <option value="keep_under_review">Keep under review</option>
            <option value="remitter_favored">Remitter favored</option>
            <option value="business_favored">Business favored</option>
            <option value="cancelled">Cancelled</option>
            <option value="completed">Completed</option>
          </select>
        </label>
        <ReasonBox model={model} />
        <button disabled={!model.adminMutable} type="button" onClick={() => model.resolveDispute()}>Resolver disputa</button>
        <p className="admin-web-muted">NODO registra decision operativa/admin; no recibe, retiene, transfiere ni garantiza fondos.</p>
      </div>
    </section>
  );
}
