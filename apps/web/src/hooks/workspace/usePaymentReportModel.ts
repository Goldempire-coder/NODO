"use client";

import type { AuthenticatedRequest } from "../../api/client";
import { getPaymentInstructions, submitOrderPaymentReport, uploadPaymentEvidence as uploadOrderPaymentEvidence } from "../../api/paymentReports";
import { PAYMENT_COPY } from "../../constants/copy";
import { actionStartedAt, recordActionCompleted, recordActionFailed, recordActionStarted } from "../actionTelemetry";
import { useStableIdempotencyKeys } from "../useStableIdempotencyKeys";
import type { ClientWorkspaceState } from "./useClientWorkspaceState";

type PaymentReportState = Pick<
  ClientWorkspaceState,
  | "selectedOrder"
  | "paymentEvidence"
  | "pendingPaymentReportId"
  | "paymentReportForm"
  | "setPaymentInstructions"
  | "setPaymentEvidence"
  | "setPendingPaymentReportId"
  | "setPaymentReportForm"
  | "setSelectedOrder"
  | "setNotice"
  | "setLoadingPaymentInstructions"
  | "setUploadingPaymentEvidence"
  | "setSubmittingPaymentReport"
  | "setView"
>;

export function usePaymentReportModel(state: PaymentReportState & { request: AuthenticatedRequest; loadMyOrders: () => Promise<void> }) {
  const {
    request,
    loadMyOrders,
    selectedOrder,
    paymentEvidence,
    pendingPaymentReportId,
    paymentReportForm,
    setPaymentInstructions,
    setPaymentEvidence,
    setPendingPaymentReportId,
    setPaymentReportForm,
    setSelectedOrder,
    setNotice,
    setLoadingPaymentInstructions,
    setSubmittingPaymentReport,
    setUploadingPaymentEvidence,
    setView
  } = state;
  const { clearIdempotencyKey, getIdempotencyKey } = useStableIdempotencyKeys();

  async function openPaymentInstructions(orderId: string) {
    const startedAt = actionStartedAt();
    recordActionStarted("client_payment_instructions_open", "payment-instructions");
    setView("payment-instructions");
    setNotice("");
    setLoadingPaymentInstructions(true);
    try {
      const data = await getPaymentInstructions<any>(request, orderId);
      setPaymentInstructions(data);
      setPaymentEvidence(null);
      setPendingPaymentReportId(null);
      setPaymentReportForm((current) => ({ ...current, payment_amount: data.order.amount_usd }));
      setView("payment-instructions");
      setNotice(data.disclaimer || PAYMENT_COPY);
      recordActionCompleted("client_payment_instructions_open", "payment-instructions", startedAt);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Las instrucciones no estan disponibles para esta orden.");
      recordActionFailed("client_payment_instructions_open", "payment-instructions", startedAt, error instanceof Error ? error.name : undefined);
    } finally {
      setLoadingPaymentInstructions(false);
    }
  }

  async function uploadPaymentEvidence(file: File | null) {
    if (!selectedOrder || !file) {
      return;
    }
    const startedAt = actionStartedAt();
    recordActionStarted("client_payment_evidence_upload", "report-payment");
    setUploadingPaymentEvidence(true);
    const idempotencyScope = `payment_evidence_${selectedOrder.id}`;
    try {
      const data = await uploadOrderPaymentEvidence<any>(request, selectedOrder.id, file, pendingPaymentReportId, getIdempotencyKey(idempotencyScope, { orderId: selectedOrder.id, pendingPaymentReportId, name: file.name, size: file.size }));
      clearIdempotencyKey(idempotencyScope);
      setPaymentEvidence(data.file);
      setPendingPaymentReportId(data.pending_payment_report_id);
      setNotice("Evidencia privada cargada. La ruta interna no se muestra.");
      recordActionCompleted("client_payment_evidence_upload", "report-payment", startedAt);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "No logramos cargar el comprobante.");
      recordActionFailed("client_payment_evidence_upload", "report-payment", startedAt, error instanceof Error ? error.name : undefined);
    } finally {
      setUploadingPaymentEvidence(false);
    }
  }

  async function submitPaymentReport() {
    if (!selectedOrder) {
      setNotice("Selecciona una orden.");
      return;
    }
    const isZelle = selectedOrder.payment_method_snapshot === "zelle";
    if (isZelle && (!paymentEvidence || !pendingPaymentReportId || !paymentReportForm.payment_reference || !paymentReportForm.payment_sender_name)) {
      setNotice("Zelle requiere referencia, nombre y comprobante.");
      return;
    }
    if (!isZelle && !paymentReportForm.tx_hash) {
      setNotice("USDT TRC20 requiere tx_hash.");
      return;
    }
    const startedAt = actionStartedAt();
    recordActionStarted("client_payment_report_submit", "report-payment");
    setSubmittingPaymentReport(true);
    const idempotencyScope = `payment_report_${selectedOrder.id}`;
    try {
      const data = await submitOrderPaymentReport<any>(
        request,
        selectedOrder.id,
        isZelle
          ? {
              payment_type: "zelle",
              payment_reference: paymentReportForm.payment_reference,
              payment_sender_name: paymentReportForm.payment_sender_name,
              payment_sender_account_masked: paymentReportForm.payment_sender_account_masked || undefined,
              payment_amount: paymentReportForm.payment_amount,
              proof_file_id: paymentEvidence?.id,
              pending_payment_report_id: pendingPaymentReportId
            }
          : {
              payment_type: "usdt_trc20",
              tx_hash: paymentReportForm.tx_hash,
              network: "TRC20",
              payment_amount: paymentReportForm.payment_amount,
              proof_file_id: paymentEvidence?.id || undefined,
              pending_payment_report_id: pendingPaymentReportId || undefined
            },
        getIdempotencyKey(idempotencyScope, { orderId: selectedOrder.id, isZelle, paymentReportForm, pendingPaymentReportId, proofFileId: paymentEvidence?.id })
      );
      clearIdempotencyKey(idempotencyScope);
      setSelectedOrder((current) => (current ? { ...current, status: data.order.status } : current));
      setView("my-orders");
      setNotice(`${data.disclaimer} Estado: ${data.order.status}.`);
      void loadMyOrders();
      recordActionCompleted("client_payment_report_submit", "report-payment", startedAt);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "No pudimos reportar el pago.");
      recordActionFailed("client_payment_report_submit", "report-payment", startedAt, error instanceof Error ? error.name : undefined);
    } finally {
      setSubmittingPaymentReport(false);
    }
  }

  return { openPaymentInstructions, uploadPaymentEvidence, submitPaymentReport };
}
