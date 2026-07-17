import { Button, Text, Title } from "@telegram-apps/telegram-ui";
import { CHAT_DISPUTE_COPY, FULL_PAYMENT_FIELD, PAYMENT_COPY } from "../../constants/copy";
import { formatPaymentMethod } from "../../constants/paymentLabels";
import { sanitizeDecimalInput } from "../../lib/numericInput";
import type { RemitterScreensModel } from "./RemitterScreens.types";

export function ClientPaymentScreens({ model }: { model: RemitterScreensModel }) {
  const {
    loadingPaymentInstructions,
    openOrderChat,
    openingChatOrderId,
    paymentEvidence,
    paymentInstructions,
    paymentReportForm,
    selectedOrder,
    setPaymentReportForm,
    setView,
    submittingPaymentReport,
    submitPaymentReport,
    uploadingPaymentEvidence,
    uploadPaymentEvidence,
    view
  } = model;

  return (
    <>
      {view === "payment-instructions" ? (
        <div className="business-card">
          <Text className="business-card__label">Instrucciones de pago</Text>
          {paymentInstructions && selectedOrder ? (
            <>
              <Title level="3" className="business-shell__title">{paymentInstructions.order.public_order_code}</Title>
              <Text>{paymentInstructions.order.amount_usd} USD - {paymentInstructions.order.amount_bs_calculated} Bs</Text>
              <Text>Tasa {paymentInstructions.order.rate_snapshot} Bs/USD</Text>
              <Text>Límite: {new Date(paymentInstructions.order.payment_report_deadline_at).toLocaleString()}</Text>
              <div className="payment-instruction">
                <Text className="business-card__label">{paymentInstructions.payment_instructions.method_type.toUpperCase()}</Text>
                <Text>Titular: {paymentInstructions.payment_instructions.holder_name}</Text>
                <Text>Cuenta oficial: {paymentInstructions.payment_instructions[FULL_PAYMENT_FIELD]}</Text>
                {paymentInstructions.payment_instructions.network ? <Text>Red: {paymentInstructions.payment_instructions.network}</Text> : null}
              </div>
              <Text className="auth-entry__session-meta">{PAYMENT_COPY}</Text>
              <Button mode="filled" stretched disabled={loadingPaymentInstructions} onClick={() => setView("report-payment")}>
                {loadingPaymentInstructions ? "Cargando..." : "Ya realicé el pago"}
              </Button>
            </>
          ) : (
            <Text>No hay instrucciones disponibles para esta orden.</Text>
          )}
        </div>
      ) : null}

      {view === "report-payment" ? (
        <div className="business-card">
          <Text className="business-card__label">Reportar pago</Text>
          {selectedOrder ? (
            <>
              <Text>{selectedOrder.public_order_code} - {formatPaymentMethod(selectedOrder.payment_method_snapshot)}</Text>
              <Text className="auth-entry__session-meta">{PAYMENT_COPY}</Text>
              <label className="business-field">
                <span>Monto pagado</span>
                <input value={paymentReportForm.payment_amount} onChange={(event) => setPaymentReportForm((current) => ({ ...current, payment_amount: sanitizeDecimalInput(event.target.value, { maxDecimals: 2, maxIntegerDigits: 6 }) }))} inputMode="decimal" pattern="[0-9]*[.]?[0-9]*" autoComplete="off" />
              </label>
              {selectedOrder.payment_method_snapshot === "zelle" ? (
                <>
                  <label className="business-field">
                    <span>Referencia Zelle</span>
                    <input value={paymentReportForm.payment_reference} onChange={(event) => setPaymentReportForm((current) => ({ ...current, payment_reference: event.target.value }))} />
                  </label>
                  <label className="business-field">
                    <span>Nombre del remitente</span>
                    <input value={paymentReportForm.payment_sender_name} onChange={(event) => setPaymentReportForm((current) => ({ ...current, payment_sender_name: event.target.value }))} />
                  </label>
                  <label className="business-field">
                    <span>Cuenta masked opcional</span>
                    <input value={paymentReportForm.payment_sender_account_masked} onChange={(event) => setPaymentReportForm((current) => ({ ...current, payment_sender_account_masked: event.target.value }))} />
                  </label>
                  <label className="business-upload">
                    <span>Comprobante privado</span>
                    <input accept="image/jpeg,image/png,image/webp,application/pdf" disabled={uploadingPaymentEvidence} type="file" onChange={(event) => void uploadPaymentEvidence(event.target.files?.[0] || null)} />
                    {uploadingPaymentEvidence ? <small>Subiendo comprobante...</small> : paymentEvidence ? <small>{paymentEvidence.mime_type} - {paymentEvidence.size_bytes} bytes</small> : null}
                  </label>
                </>
              ) : (
                <>
                  <label className="business-field">
                    <span>Tx hash USDT TRC20</span>
                    <input value={paymentReportForm.tx_hash} onChange={(event) => setPaymentReportForm((current) => ({ ...current, tx_hash: event.target.value }))} />
                  </label>
                  <label className="business-upload">
                    <span>Comprobante opcional</span>
                    <input accept="image/jpeg,image/png,image/webp,application/pdf" disabled={uploadingPaymentEvidence} type="file" onChange={(event) => void uploadPaymentEvidence(event.target.files?.[0] || null)} />
                    {uploadingPaymentEvidence ? <small>Subiendo comprobante...</small> : paymentEvidence ? <small>{paymentEvidence.mime_type} - {paymentEvidence.size_bytes} bytes</small> : null}
                  </label>
                </>
              )}
              <Button mode="filled" stretched disabled={submittingPaymentReport} onClick={() => void submitPaymentReport()}>
                {submittingPaymentReport ? "Enviando reporte..." : "Confirmar y enviar"}
              </Button>
              <Button mode="outline" stretched disabled={!selectedOrder || selectedOrder.status === "waiting_payment" || openingChatOrderId === selectedOrder.id} onClick={() => selectedOrder ? void openOrderChat(selectedOrder.id) : undefined}>
                {selectedOrder && openingChatOrderId === selectedOrder.id ? "Abriendo..." : "Abrir tracking/chat"}
              </Button>
              <Text className="auth-entry__session-meta">{CHAT_DISPUTE_COPY}</Text>
            </>
          ) : (
            <Text>Selecciona una orden propia.</Text>
          )}
        </div>
      ) : null}
    </>
  );
}
