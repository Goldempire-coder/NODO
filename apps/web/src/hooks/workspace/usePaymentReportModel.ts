"use client";

import { useRef } from "react";
import type { AuthenticatedRequest } from "../../api/client";
import { getPaymentInstructions, submitOrderPaymentReport, uploadPaymentEvidence as uploadOrderPaymentEvidence } from "../../api/paymentReports";
import { preparePaymentEvidenceFile } from "../../utils/paymentEvidenceFiles";
import { actionStartedAt, recordActionCompleted, recordActionFailed, recordActionStarted } from "../actionTelemetry";
import { useStableIdempotencyKeys } from "../useStableIdempotencyKeys";
import { emptyPaymentReportForm, type ClientWorkspaceState } from "./useClientWorkspaceState";

type PaymentReportState = Pick<
  ClientWorkspaceState,
  | "paymentOrderContextRef"
  | "openingChatOrderId"
  | "view"
  | "paymentInstructions"
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
>;

type RefreshChatAfterPaymentReport = (options?: { silent?: boolean }) => Promise<boolean>;

function paymentEvidenceUploadErrorMessage(error: unknown): string {
  if (error instanceof Error) {
    const normalizedMessage = error.message.toLowerCase();
    if (error.name === "TypeError" || normalizedMessage.includes("fetch")) {
      return "No pudimos subir el comprobante. Revisa tu conexion y que la imagen no sea demasiado pesada.";
    }
    return error.message;
  }
  return "No pudimos subir el comprobante.";
}

function paymentReportSubmitErrorMessage(error: unknown): string {
  if (error instanceof Error) {
    const normalizedMessage = error.message.toLowerCase();
    if (error.name === "TypeError" || normalizedMessage.includes("fetch")) {
      return "No pudimos confirmar el pago. Revisa tu conexion e intenta otra vez.";
    }
    return error.message;
  }
  return "No pudimos confirmar el pago.";
}

export function usePaymentReportModel(
  state: PaymentReportState & {
    request: AuthenticatedRequest;
    refreshMyOrdersAfterPaymentReport: () => Promise<void>;
    refreshChatAfterPaymentReport: RefreshChatAfterPaymentReport;
  }
) {
  const {
    request,
    refreshMyOrdersAfterPaymentReport,
    refreshChatAfterPaymentReport,
    paymentOrderContextRef,
    openingChatOrderId,
    view,
    paymentInstructions,
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
    setUploadingPaymentEvidence
  } = state;
  const { clearIdempotencyKey, getIdempotencyKey } = useStableIdempotencyKeys();
  const paymentInstructionsRequestOrderIdRef = useRef<string | null>(null);
  const openingChatOrderIdRef = useRef(openingChatOrderId);
  const activeViewRef = useRef(view);
  openingChatOrderIdRef.current = openingChatOrderId;
  activeViewRef.current = view;

  function paymentActionIsCurrent(orderId: string) {
    return (
      paymentOrderContextRef.current === orderId
      && openingChatOrderIdRef.current === null
      && activeViewRef.current === "order-chat"
    );
  }

  function currentPaymentInstructions(orderId: string) {
    return paymentInstructions?.order.id === orderId ? paymentInstructions : null;
  }

  async function loadPaymentInstructionsForActiveOrder(orderId: string) {
    if (paymentInstructionsRequestOrderIdRef.current === orderId) {
      return null;
    }
    paymentInstructionsRequestOrderIdRef.current = orderId;
    setLoadingPaymentInstructions(true);
    try {
      const data = await getPaymentInstructions(request, orderId);
      if (
        paymentInstructionsRequestOrderIdRef.current !== orderId
        || !paymentActionIsCurrent(orderId)
      ) {
        return null;
      }
      setPaymentInstructions(data);
      setPaymentReportForm((current) => ({
        ...current,
        payment_amount: data.order.amount_usd
      }));
      return data;
    } finally {
      if (paymentInstructionsRequestOrderIdRef.current === orderId) {
        paymentInstructionsRequestOrderIdRef.current = null;
        setLoadingPaymentInstructions(false);
      }
    }
  }

  async function openPaymentReport(orderId: string) {
    const startedAt = actionStartedAt();
    recordActionStarted("client_payment_instructions_open", "report-payment");
    setNotice("");
    try {
      const data = await loadPaymentInstructionsForActiveOrder(orderId);
      if (!data) {
        return false;
      }
      setPaymentEvidence(null);
      setPendingPaymentReportId(null);
      setPaymentReportForm(emptyPaymentReportForm(data.order.amount_usd));
      setNotice("");
      recordActionCompleted("client_payment_instructions_open", "report-payment", startedAt);
      return true;
    } catch (error) {
      if (paymentActionIsCurrent(orderId)) {
        setNotice(error instanceof Error ? error.message : "Las instrucciones no estan disponibles para esta orden.");
      }
      recordActionFailed("client_payment_instructions_open", "report-payment", startedAt, error instanceof Error ? error.name : undefined);
      return false;
    }
  }

  async function uploadPaymentEvidence(file: File | null) {
    const orderId = paymentOrderContextRef.current;
    if (!orderId || !file || !paymentActionIsCurrent(orderId)) {
      return;
    }
    let resolvedInstructions = currentPaymentInstructions(orderId);
    if (!resolvedInstructions) {
      try {
        resolvedInstructions = await loadPaymentInstructionsForActiveOrder(orderId);
      } catch (error) {
        if (paymentActionIsCurrent(orderId)) {
          setNotice(error instanceof Error ? error.message : "Las instrucciones no estan disponibles para esta orden.");
        }
        return;
      }
    }
    if (!resolvedInstructions || !paymentActionIsCurrent(orderId)) {
      if (paymentActionIsCurrent(orderId)) {
        setNotice("Espera a que carguen los datos de pago e intenta de nuevo.");
      }
      return;
    }
    const startedAt = actionStartedAt();
    recordActionStarted("client_payment_evidence_upload", "report-payment");
    setUploadingPaymentEvidence(true);
    const idempotencyScope = `payment_evidence_${orderId}`;
    try {
      const preparedFile = await preparePaymentEvidenceFile(file);
      const data = await uploadOrderPaymentEvidence(
        request,
        orderId,
        preparedFile,
        pendingPaymentReportId,
        getIdempotencyKey(idempotencyScope, {
          orderId,
          pendingPaymentReportId,
          name: preparedFile.name,
          size: preparedFile.size,
          type: preparedFile.type
        })
      );
      clearIdempotencyKey(idempotencyScope);
      if (!paymentActionIsCurrent(orderId)) {
        return;
      }
      setPaymentEvidence(data.file);
      setPendingPaymentReportId(data.pending_payment_report_id);
      setNotice("");
      recordActionCompleted("client_payment_evidence_upload", "report-payment", startedAt);
    } catch (error) {
      if (paymentActionIsCurrent(orderId)) {
        setNotice(paymentEvidenceUploadErrorMessage(error));
      }
      recordActionFailed("client_payment_evidence_upload", "report-payment", startedAt, error instanceof Error ? error.name : undefined);
    } finally {
      setUploadingPaymentEvidence(false);
    }
  }

  async function submitPaymentReport() {
    const orderId = paymentOrderContextRef.current;
    if (!orderId || !paymentActionIsCurrent(orderId)) {
      setNotice("Selecciona una orden.");
      return;
    }
    let resolvedInstructions = currentPaymentInstructions(orderId);
    if (!resolvedInstructions) {
      try {
        resolvedInstructions = await loadPaymentInstructionsForActiveOrder(orderId);
      } catch (error) {
        if (paymentActionIsCurrent(orderId)) {
          setNotice(error instanceof Error ? error.message : "Las instrucciones no estan disponibles para esta orden.");
        }
        return;
      }
    }
    if (!resolvedInstructions || !paymentActionIsCurrent(orderId)) {
      return;
    }
    const paymentMethod = resolvedInstructions.payment_instructions.method_type;
    const lockedPaymentAmount = resolvedInstructions.order.amount_usd;
    if (!paymentMethod || !lockedPaymentAmount) {
      setNotice("Selecciona una orden.");
      return;
    }
    const isZelle = paymentMethod === "zelle";
    const startedAt = actionStartedAt();
    recordActionStarted("client_payment_report_submit", "report-payment");
    setSubmittingPaymentReport(true);
    const idempotencyScope = `payment_report_${orderId}`;
    try {
      const data = await submitOrderPaymentReport(
        request,
        orderId,
        isZelle
          ? {
              payment_type: "zelle",
              payment_amount: lockedPaymentAmount,
              ...(paymentEvidence && pendingPaymentReportId
                ? {
                    proof_file_id: paymentEvidence.id,
                    pending_payment_report_id: pendingPaymentReportId
                  }
                : {})
            }
          : {
              payment_type: "usdt_trc20",
              payment_amount: lockedPaymentAmount,
              proof_file_id: paymentEvidence?.id || undefined,
              pending_payment_report_id: pendingPaymentReportId || undefined
            },
        getIdempotencyKey(idempotencyScope, {
          orderId,
          isZelle,
          paymentReportForm: {
            ...paymentReportForm,
            payment_amount: lockedPaymentAmount
          },
          pendingPaymentReportId,
          proofFileId: paymentEvidence?.id
        })
      );
      clearIdempotencyKey(idempotencyScope);
      setSelectedOrder((current) => (
        current?.id === orderId ? { ...current, status: data.order.status } : current
      ));
      if (paymentActionIsCurrent(orderId)) {
        setPaymentInstructions(null);
        setPaymentEvidence(null);
        setPendingPaymentReportId(null);
        setPaymentReportForm(emptyPaymentReportForm());
        setNotice("");
        await refreshChatAfterPaymentReport({ silent: true });
      }
      void refreshMyOrdersAfterPaymentReport();
      recordActionCompleted("client_payment_report_submit", "report-payment", startedAt);
    } catch (error) {
      if (paymentActionIsCurrent(orderId)) {
        setNotice(paymentReportSubmitErrorMessage(error));
      }
      recordActionFailed("client_payment_report_submit", "report-payment", startedAt, error instanceof Error ? error.name : undefined);
    } finally {
      setSubmittingPaymentReport(false);
    }
  }

  return { openPaymentReport, uploadPaymentEvidence, submitPaymentReport };
}
