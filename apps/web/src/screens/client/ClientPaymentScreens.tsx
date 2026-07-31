import { Button, Text } from "@telegram-apps/telegram-ui";
import { CHAT_DISPUTE_COPY, PAYMENT_COPY } from "../../constants/copy";
import { formatPaymentMethod } from "../../constants/paymentLabels";
import type { RemitterScreensModel } from "./RemitterScreens.types";

export function ClientPaymentScreens({ model }: { model: RemitterScreensModel }) {
  const {
    openOrderChat,
    openingChatOrderId,
    paymentEvidence,
    paymentInstructions,
    paymentReportForm,
    selectedOrder,
    setPaymentReportForm,
    submittingPaymentReport,
    submitPaymentReport,
    uploadingPaymentEvidence,
    uploadPaymentEvidence,
    view
  } = model;
  const reportOrderId = paymentInstructions?.order.id || selectedOrder?.id;
  const reportOrderCode = paymentInstructions?.order.public_order_code || selectedOrder?.public_order_code;
  const reportAmount = paymentInstructions?.order.amount_usd || selectedOrder?.amount_usd;
  const reportPaymentMethod = paymentInstructions?.payment_instructions.method_type || selectedOrder?.payment_method_snapshot;

  return (
    <>
      {view === "report-payment" ? (
        <div className="business-card">
          <Text className="business-card__label">Reportar pago</Text>
          {paymentInstructions && reportOrderId && reportAmount && reportPaymentMethod ? (
            <>
              <Text>{reportOrderCode} - {formatPaymentMethod(reportPaymentMethod)}</Text>
              <Text className="auth-entry__session-meta">{PAYMENT_COPY}</Text>
              <label className="business-field">
                <span>Monto pagado</span>
                <input
                  aria-readonly="true"
                  readOnly
                  value={paymentInstructions.order.amount_usd}
                  inputMode="decimal"
                />
              </label>
              {reportPaymentMethod === "zelle" ? (
                <>
                  <label className="business-field">
                    <span>Referencia Zelle</span>
                    <input value={paymentReportForm.payment_reference} onChange={(event) => setPaymentReportForm((current) => ({ ...current, payment_reference: event.target.value }))} />
                  </label>
                  <label className="business-field">
                    <span>Nombre del remitente</span>
                    <input value={paymentReportForm.payment_sender_name} onChange={(event) => setPaymentReportForm((current) => ({ ...current, payment_sender_name: event.target.value }))} />
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
              <Button mode="outline" stretched disabled={openingChatOrderId === reportOrderId} onClick={() => void openOrderChat(reportOrderId)}>
                {openingChatOrderId === reportOrderId ? "Abriendo..." : "Volver al chat"}
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
