import type { AdminWebModel } from "../../hooks/useAdminWebModel";
import type { AdminDisputeSummary, AdminOrderSummary } from "../../types/admin";
import { dateText, Empty, Header, ReasonBox, Table } from "./AdminWebPrimitives";
import { AdminOrderChatEvidencePanel } from "./AdminOrderChatEvidencePanel";

export function Orders({ model }: { model: AdminWebModel }) {
  return (
    <section className="admin-web-panel admin-web-orders-panel">
      <Header title="A-11 Ordenes" action={<button form="admin-orders-filter" type="submit">Aplicar filtro</button>} />
      <form
        className="admin-web-toolbar admin-web-toolbar--orders"
        id="admin-orders-filter"
        onSubmit={(event) => {
          event.preventDefault();
          void model.loadOrders(model.orderFilter, model.orderCodeFilter);
        }}
      >
        <label><span>Status</span><input value={model.orderFilter} onChange={(event) => model.setOrderFilter(event.target.value)} placeholder="disputed, delivered..." /></label>
        <label><span>Codigo de orden</span><input value={model.orderCodeFilter} onChange={(event) => model.setOrderCodeFilter(event.target.value)} placeholder="NODO-7C25CBC6" /></label>
      </form>
      <div className="admin-web-orders-list-scroll" role="region" aria-label="Lista de ordenes admin" tabIndex={0}>
        <Table headers={["Codigo", "Status", "Monto", "Metodo", ""]}>
          {model.orders.map((item: AdminOrderSummary) => (
            <tr key={item.id}>
              <td className="admin-web-order-code-cell">{item.public_order_code}</td>
              <td>{item.status}</td>
              <td>{item.amount_usd} USD</td>
              <td>{item.payment_method_snapshot}</td>
              <td><button type="button" onClick={() => void model.openOrder(item.id)}>Detalle</button></td>
            </tr>
          ))}
        </Table>
      </div>
      {model.orders.length === 0 ? <Empty text="No hay ordenes para el filtro actual." /> : null}
      {model.ordersNextCursor ? (
        <div className="admin-web-orders-list-actions">
          <button className="admin-web-button" disabled={model.ordersLoadingMore} type="button" onClick={() => void model.loadMoreOrders()}>
            {model.ordersLoadingMore ? "Cargando..." : "Cargar mas"}
          </button>
        </div>
      ) : null}
    </section>
  );
}

export function OrderDetail({ model }: { model: AdminWebModel }) {
  const order = model.selectedOrder?.order as AdminOrderSummary | undefined;
  const paymentReport = model.selectedOrder?.payment_report as { status?: string; payment_type?: string; payment_amount?: string; created_at?: string } | undefined;
  const timeline = model.selectedOrder?.timeline as { event_type?: string; to_status?: string; created_at?: string }[] | undefined;
  const cancelledBeforePayment = (timeline || []).some(
    (event) => event.event_type === "order_cancelled_by_remitter"
  );
  return (
    <>
      {model.adminCanGoBack ? (
        <div className="admin-web-detail-backbar">
          <button type="button" onClick={() => model.goBackAdminView()}>{model.adminBackLabel}</button>
        </div>
      ) : null}
      {order?.status === "payment_rejected" ? (
        <section className="admin-web-panel admin-web-order-resolution">
          <div className="admin-web-order-resolution__header">
            <div>
              <h3>Resolver orden</h3>
              <p className="admin-web-muted">
                Abre una investigacion formal y luego usa la resolucion de disputas existente.
              </p>
            </div>
            <button disabled={!model.adminMutable} type="button" onClick={() => model.resolveAdminStuckOrder()}>
              Resolver orden
            </button>
          </div>
          <div className="admin-web-order-resolution__body">
            <label className="admin-web-field">
              <span>Resultado operativo</span>
              <select value={model.resolutionType} onChange={(event) => model.setResolutionType(event.target.value)}>
                <option value="cancelled">Cancelar por pago no comprobado</option>
                <option value="keep_under_review">Mantener en investigacion</option>
                <option value="remitter_favored">Resolver a favor del cliente</option>
                <option value="business_favored">Resolver a favor del negocio</option>
              </select>
            </label>
            <ReasonBox
              model={model}
              label="Razon obligatoria"
              placeholder="Explica la evidencia y el motivo de la decision"
            />
          </div>
          <p className="admin-web-muted">{model.stuckOrderResolutionPreview}</p>
        </section>
      ) : null}
      <section className="admin-web-split admin-order-detail-summary">
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
          {cancelledBeforePayment ? (
            <p className="admin-web-muted">Cancelada antes de reportar pago.</p>
          ) : null}
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
          <div className="admin-web-order-timeline-scroll" role="region" aria-label="Timeline completo de la orden" tabIndex={0}>
            {(timeline || []).map((event, index) => (
              <div className="admin-web-row" key={`${event.event_type}_${event.created_at}_${index}`}>
                <span>{event.event_type || "event"}</span>
                <small>{event.to_status || "-"} - {dateText(event.created_at)}</small>
              </div>
            ))}
          </div>
        </div>
      </section>
      {order ? <AdminOrderChatEvidencePanel model={model} /> : null}
    </>
  );
}

export function Disputes({ model }: { model: AdminWebModel }) {
  return (
    <section className="admin-web-panel admin-web-disputes-panel">
      <Header title="A-06 Disputas" action={<button onClick={() => void model.loadDisputes(model.disputeFilter)} type="button">Aplicar filtro</button>} />
      <div className="admin-web-toolbar">
        <label><span>Status</span><input value={model.disputeFilter} onChange={(event) => model.setDisputeFilter(event.target.value)} placeholder="open, in_review..." /></label>
      </div>
      <div className="admin-web-disputes-list-scroll" role="region" aria-label="Lista de disputas admin" tabIndex={0}>
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
      </div>
      {model.disputes.length === 0 ? <Empty text="No hay disputas para ese filtro." /> : null}
      {model.disputesNextCursor ? (
        <button className="admin-web-button" disabled={model.disputesLoadingMore} type="button" onClick={() => void model.loadMoreDisputes()}>
          {model.disputesLoadingMore ? "Cargando..." : "Cargar mas"}
        </button>
      ) : null}
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
