import type { AdminWebModel } from "../../hooks/useAdminWebModel";
import type { AdminCreditPurchaseSummary, AdminCreditTransactionItem } from "../../types/credits";
import { dateText, Empty, Header, ReasonBox, Table } from "./AdminWebPrimitives";

const WARNING_LABELS: Record<string, string> = {
  CREDITED_WITHOUT_LEDGER: "La compra figura acreditada, pero no tiene ledger relacionado.",
  CREDIT_PURCHASE_EXPIRED: "La compra expiro sin completar la reconciliacion.",
  LEDGER_STATUS_MISMATCH: "El ledger y el estado de la compra requieren revision.",
  ONCHAIN_VERIFICATION_FAILED: "La verificacion on-chain fallo.",
  PAYMENT_REQUIRES_REVIEW: "La evidencia requiere revision Admin."
};

const TRANSACTION_STATUS_LABELS: Record<string, string> = {
  confirmed: "Confirmada",
  dismissed: "Descartada",
  failed: "Fallida",
  pending: "Pendiente",
  review: "En revision"
};

const PAYMENT_METHOD_LABELS: Record<string, string> = {
  base_usdc_contract: "Base USDC",
  base_usdc_onchain: "Base USDC legacy",
  stripe_checkout: "Stripe",
  usdt_manual_admin_approved: "USDT manual",
  zelle_manual_admin_approved: "Zelle manual"
};

const CREDIT_PURCHASE_STATUS_OPTIONS = [
  { value: "", label: "Todos" },
  { value: "pending_manual_review", label: "Revision manual" },
  { value: "pending_payment", label: "Pago pendiente" },
  { value: "pending_onchain_confirmation", label: "Confirmacion on-chain" },
  { value: "detected", label: "Pago detectado" },
  { value: "under_review", label: "En revision" },
  { value: "paid", label: "Pagada" },
  { value: "approved", label: "Aprobada manual" },
  { value: "credited", label: "Acreditada" },
  { value: "rejected", label: "Rechazada" },
  { value: "failed", label: "Fallida" },
  { value: "expired", label: "Expirada" },
  { value: "verification_failed", label: "Verificacion fallida" }
];

function matchLabel(value: boolean | null) {
  if (value === null) {
    return "Sin evidencia";
  }
  return value ? "Coincide" : "No coincide";
}

function methodLabel(value: string) {
  return PAYMENT_METHOD_LABELS[value] || value;
}

function transactionStatusLabel(value: string) {
  return TRANSACTION_STATUS_LABELS[value] || value;
}

function transactionEvidence(item: AdminCreditTransactionItem) {
  return item.tx_hash_masked || item.payer_wallet_masked || item.payment_contract_masked || "-";
}

function purchaseSummaryFromTransaction(item: AdminCreditTransactionItem): AdminCreditPurchaseSummary {
  return {
    id: item.purchase_id,
    business_id: item.business_id,
    package_code: item.package_code,
    credits_amount: item.credits_amount,
    price_usd: item.price_usd,
    payment_method: item.payment_method,
    status: item.purchase_status,
    verification_status: item.verification_status,
    has_reported_tx: Boolean(item.tx_hash_masked),
    created_at: item.created_at,
    updated_at: item.updated_at
  };
}

export function CreditTransactions({ model }: { model: AdminWebModel }) {
  const filters = model.creditTransactionFilters;
  return (
    <section className="admin-web-panel admin-web-credit-transactions-panel">
      <Header title="A-04 Registro NODO" action={<button type="button" onClick={() => void model.loadCreditTransactions(filters)}>Aplicar filtros</button>} />
      <div className="admin-web-credit-transactions-summary">
        <div><span>Ingresos confirmados</span><strong>${model.creditTransactionsSummary.confirmed_amount_usd}</strong></div>
        <div><span>Creditos confirmados</span><strong>{model.creditTransactionsSummary.confirmed_credits}</strong></div>
        <div><span>Confirmadas</span><strong>{model.creditTransactionsSummary.confirmed_count}</strong></div>
        <div><span>Pendientes</span><strong>{model.creditTransactionsSummary.pending_count}</strong></div>
        <div><span>En revision</span><strong>{model.creditTransactionsSummary.review_count}</strong></div>
        <div><span>Descartados</span><strong>{model.creditTransactionsSummary.dismissed_count}</strong></div>
      </div>
      <div className="admin-web-toolbar admin-web-toolbar--credit-transactions">
        <label>
          <span>Estado financiero</span>
          <select
            value={filters.financial_status}
            onChange={(event) => model.setCreditTransactionFilters({ ...filters, financial_status: event.target.value })}
          >
            <option value="">Todos</option>
            <option value="confirmed">Confirmadas</option>
            <option value="pending">Pendientes</option>
            <option value="review">En revision</option>
            <option value="failed">Fallidas</option>
            <option value="dismissed">Descartadas</option>
          </select>
        </label>
        <label>
          <span>Metodo</span>
          <select
            value={filters.payment_method}
            onChange={(event) => model.setCreditTransactionFilters({ ...filters, payment_method: event.target.value })}
          >
            <option value="">Todos</option>
            <option value="base_usdc_contract">Base USDC</option>
            <option value="zelle_manual_admin_approved">Zelle manual</option>
            <option value="usdt_manual_admin_approved">USDT manual</option>
            <option value="stripe_checkout">Stripe</option>
          </select>
        </label>
        <label>
          <span>Paquete</span>
          <select
            value={filters.package_code}
            onChange={(event) => model.setCreditTransactionFilters({ ...filters, package_code: event.target.value })}
          >
            <option value="">Todos</option>
            <option value="starter">Starter</option>
            <option value="pro">Pro</option>
            <option value="business">Business</option>
            <option value="enterprise">Enterprise</option>
          </select>
        </label>
        <label>
          <span>Business ID</span>
          <input
            value={filters.business_id}
            onChange={(event) => model.setCreditTransactionFilters({ ...filters, business_id: event.target.value })}
            placeholder="UUID del negocio"
          />
        </label>
        <label>
          <span>Desde</span>
          <input
            type="datetime-local"
            value={filters.created_from}
            onChange={(event) => model.setCreditTransactionFilters({ ...filters, created_from: event.target.value })}
          />
        </label>
        <label>
          <span>Hasta</span>
          <input
            type="datetime-local"
            value={filters.created_to}
            onChange={(event) => model.setCreditTransactionFilters({ ...filters, created_to: event.target.value })}
          />
        </label>
      </div>
      <div className="admin-web-credit-transactions-list-scroll" role="region" aria-label="Registro de transacciones de creditos admin" tabIndex={0}>
        <Table headers={["Fecha", "Negocio", "Paquete", "Creditos", "Monto", "Metodo", "Estado", "Ledger", "Evidencia", ""]}>
          {model.creditTransactions.map((item: AdminCreditTransactionItem) => (
            <tr key={item.purchase_id}>
              <td>{dateText(item.transaction_at)}</td>
              <td>{item.business_name || item.business_id}</td>
              <td>{item.package_code}</td>
              <td>{item.credits_amount}</td>
              <td>${item.price_usd}</td>
              <td>{methodLabel(item.payment_method)}</td>
              <td>{transactionStatusLabel(item.financial_status)}</td>
              <td>{item.ledger_matched ? "Si" : "No"}</td>
              <td>{transactionEvidence(item)}</td>
              <td><button type="button" onClick={() => void model.setSelectedCreditPurchase(purchaseSummaryFromTransaction(item), "credit-transactions")}>Detalle</button></td>
            </tr>
          ))}
        </Table>
      </div>
      {model.creditTransactionsNextCursor ? (
        <div className="admin-web-orders-list-actions">
          <button disabled={model.creditTransactionsLoadingMore} type="button" onClick={() => void model.loadMoreCreditTransactions()}>
            {model.creditTransactionsLoadingMore ? "Cargando..." : "Cargar mas"}
          </button>
        </div>
      ) : null}
      {model.creditTransactions.length === 0 ? <Empty text="Sin transacciones de creditos para esos filtros." /> : null}
    </section>
  );
}

export function CreditPurchases({ model }: { model: AdminWebModel }) {
  return (
    <section className="admin-web-panel admin-web-credit-purchases-panel">
      <Header title="A-04 Pagos de creditos" action={<button onClick={() => void model.loadCreditPurchases(model.creditFilter)} type="button">Aplicar filtro</button>} />
      <div className="admin-web-toolbar">
        <label>
          <span>Estado</span>
          <select value={model.creditFilter} onChange={(event) => model.setCreditFilter(event.target.value)}>
            {CREDIT_PURCHASE_STATUS_OPTIONS.map((option) => (
              <option key={option.value || "all"} value={option.value}>{option.label}</option>
            ))}
          </select>
        </label>
        <button type="button" onClick={() => model.setView("credit-adjustments")}>Ajuste manual</button>
      </div>
      <div className="admin-web-credit-purchases-list-scroll" role="region" aria-label="Lista de compras de creditos admin" tabIndex={0}>
        <Table headers={["Business", "Paquete", "Creditos", "Monto", "Metodo", "Status", ""]}>
          {model.creditPurchases.map((item: AdminCreditPurchaseSummary) => (
            <tr key={item.id}>
              <td>{item.business_id}</td>
              <td>{item.package_code}</td>
              <td>{item.credits_amount}</td>
              <td>${item.price_usd}</td>
              <td>{item.payment_method}</td>
              <td>{item.status}</td>
              <td><button type="button" onClick={() => void model.setSelectedCreditPurchase(item)}>Detalle</button></td>
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
  const detail = model.selectedCreditPurchase;
  if (!detail) {
    return <Empty text="Selecciona una compra." />;
  }
  const { ledger, onchain_evidence: evidence, purchase, reconciliation } = detail;
  const canApprove = purchase.status === "pending_manual_review";
  const canReject = canApprove || (purchase.payment_method === "base_usdc_onchain" && purchase.status === "under_review");
  return (
    <section className="admin-web-credit-detail-scroll" role="region" aria-label="Reconciliacion de compra de creditos" tabIndex={0}>
      <div className="admin-web-credit-detail-header">
        <div>
          <p>Admin Creditos</p>
          <h2>Detalle y reconciliacion</h2>
        </div>
        <button type="button" onClick={() => { void model.setSelectedCreditPurchase(null); model.setView(model.creditDetailReturnView); }}>Volver</button>
      </div>
      <div className="admin-web-credit-detail-grid">
        <section className="admin-web-credit-detail-section">
          <h3>Compra</h3>
          <dl className="admin-web-dl">
            <dt>ID</dt><dd>{purchase.id}</dd>
            <dt>Negocio</dt><dd>{purchase.business_id}</dd>
            <dt>Paquete</dt><dd>{purchase.package_code}</dd>
            <dt>Estado</dt><dd>{purchase.status}</dd>
            <dt>Creditos</dt><dd>{purchase.credits_amount}</dd>
            <dt>Monto esperado</dt><dd>${purchase.price_usd}</dd>
            <dt>Metodo</dt><dd>{purchase.payment_method}</dd>
          </dl>
        </section>

        <section className="admin-web-credit-detail-section">
          <h3>Diagnostico</h3>
          <p className={`admin-web-credit-reconciliation admin-web-credit-reconciliation--${reconciliation.state}`}>
            Estado: {reconciliation.state}
          </p>
          {reconciliation.warning_codes.length ? (
            <ul className="admin-web-credit-warning-list">
              {reconciliation.warning_codes.map((code) => <li key={code}>{WARNING_LABELS[code] || code}</li>)}
            </ul>
          ) : <p>Compra y ledger relacionados sin warnings.</p>}
        </section>

        {evidence ? (
          <section className="admin-web-credit-detail-section">
            <h3>Evidencia on-chain enmascarada</h3>
            <dl className="admin-web-dl">
              <dt>Red</dt><dd>{evidence.network || "-"} ({evidence.chain_id ?? "-"})</dd>
              <dt>Token</dt><dd>{evidence.token_symbol || "-"} / {evidence.token_contract_address_masked || "-"}</dd>
              <dt>Pagador</dt><dd>{evidence.payer_wallet_masked || "-"}</dd>
              <dt>Wallet destino</dt><dd>{evidence.destination_wallet_masked || "-"}</dd>
              <dt>Contrato</dt><dd>{evidence.payment_contract_masked || "-"} / v{evidence.payment_contract_version ?? "-"}</dd>
              <dt>Referencia de compra</dt><dd>{evidence.purchase_ref_masked || "-"}</dd>
              <dt>Hash</dt><dd>{evidence.tx_hash_masked || "No reportado"}</dd>
              <dt>Monto esperado</dt><dd>{evidence.expected_amount_units ?? "-"}</dd>
              <dt>Monto detectado</dt><dd>{evidence.tx_amount_units ?? "-"}</dd>
              <dt>Coincidencia pagador</dt><dd>{matchLabel(evidence.payer_matches)}</dd>
              <dt>Destino</dt><dd>{matchLabel(evidence.destination_matches)}</dd>
              <dt>Monto</dt><dd>{matchLabel(evidence.amount_matches)}</dd>
              <dt>Confirmaciones</dt><dd>{evidence.confirmations ?? "-"}</dd>
              <dt>Verificacion</dt><dd>{evidence.verification_status || "pendiente"}</dd>
            </dl>
          </section>
        ) : (
          <section className="admin-web-credit-detail-section">
            <h3>Evidencia manual</h3>
            <dl className="admin-web-dl">
              <dt>Referencia</dt><dd>{purchase.manual_payment_reference_masked || "-"}</dd>
              <dt>Hash</dt><dd>{purchase.manual_tx_hash_masked || "-"}</dd>
              <dt>Red</dt><dd>{purchase.manual_network || "-"}</dd>
            </dl>
          </section>
        )}

        <section className="admin-web-credit-detail-section">
          <h3>Ledger relacionado</h3>
          {ledger ? (
            <dl className="admin-web-dl">
              <dt>Ledger ID</dt><dd>{ledger.id}</dd>
              <dt>Compra relacionada</dt><dd>{ledger.related_credit_purchase_id || "-"}</dd>
              <dt>Movimiento</dt><dd>{ledger.type} / {ledger.amount}</dd>
              <dt>Disponible</dt><dd>{ledger.balance_available_before} → {ledger.balance_available_after}</dd>
              <dt>Bloqueado</dt><dd>{ledger.balance_blocked_before} → {ledger.balance_blocked_after}</dd>
              <dt>Consumido</dt><dd>{ledger.balance_consumed_before} → {ledger.balance_consumed_after}</dd>
            </dl>
          ) : <p>Sin movimiento de ledger relacionado.</p>}
        </section>

        {canApprove || canReject ? (
          <section className="admin-web-credit-detail-section admin-web-credit-review-actions">
            <h3>Revision Admin</h3>
            <ReasonBox
              model={model}
              label="Razon obligatoria para revisar compra de creditos"
              placeholder="Indica el motivo operativo antes de aprobar o rechazar"
            />
            <div className="admin-web-actions">
              {canApprove ? <button disabled={!model.adminMutable} type="button" onClick={() => model.reviewCreditPurchase("approve")}>Aprobar</button> : null}
              {canReject ? <button className="danger" disabled={!model.adminMutable} type="button" onClick={() => model.reviewCreditPurchase("reject")}>Rechazar</button> : null}
            </div>
          </section>
        ) : null}
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
