"use client";

import { useRef } from "react";
import type { AuthenticatedRequest } from "../../api/client";
import { getPaymentInstructions, submitOrderPaymentReport, uploadPaymentEvidence as uploadOrderPaymentEvidence } from "../../api/paymentReports";
import type { PaymentInstructions } from "../../types/payments";
import { actionStartedAt, recordActionCompleted, recordActionFailed, recordActionStarted } from "../actionTelemetry";
import { useStableIdempotencyKeys } from "../useStableIdempotencyKeys";
import type { ClientWorkspaceState } from "./useClientWorkspaceState";

type PaymentReportState = Pick<
  ClientWorkspaceState,
  | "selectedOrder"
  | "chatOrderId"
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
  | "setView"
>;

type RefreshChatAfterPaymentReport = (options?: { silent?: boolean }) => Promise<boolean>;

export function usePaymentReportModel(
  state: PaymentReportState & {
    request: AuthenticatedRequest;
    loadMyOrders: () => Promise<void>;
    refreshChatAfterPaymentReport: RefreshChatAfterPaymentReport;
  }
) {
  const {
    request,
    loadMyOrders,
    refreshChatAfterPaymentReport,
    selectedOrder,
    chatOrderId,
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
    setUploadingPaymentEvidence,
    setView
  } = state;
  const { clearIdempotencyKey, getIdempotencyKey } = useStableIdempotencyKeys();
  const openingPaymentReportRef = useRef(false);
  const paymentReportTargetOrderIdRef = useRef<string | null>(null);
  const activeChatOrderIdRef = useRef(chatOrderId);
  const openingChatOrderIdRef = useRef(openingChatOrderId);
  const activeViewRef = useRef(view);
  activeChatOrderIdRef.current = chatOrderId;
  openingChatOrderIdRef.current = openingChatOrderId;
  activeViewRef.current = view;

  function paymentReportTargetIsCurrent(orderId: string) {
    return (
      paymentReportTargetOrderIdRef.current === orderId
      && activeChatOrderIdRef.current === orderId
      && openingChatOrderIdRef.current === null
      && activeViewRef.current === "order-chat"
    );
  }

  async function openPaymentReport(orderId: string) {
    if (openingPaymentReportRef.current) {
      return false;
    }
    openingPaymentReportRef.current = true;
    paymentReportTargetOrderIdRef.current = orderId;
    const startedAt = actionStartedAt();
    recordActionStarted("client_payment_instructions_open", "report-payment");
    setNotice("");
    setLoadingPaymentInstructions(true);
    try {
      const data = await getPaymentInstructions<PaymentInstructions>(request, orderId);
      if (!paymentReportTargetIsCurrent(orderId)) {
        return false;
      }
      setPaymentInstructions(data);
      setPaymentEvidence(null);
      setPendingPaymentReportId(null);
      setPaymentReportForm({
        payment_reference: "",
        payment_sender_name: "",
        payment_sender_account_masked: "",
        payment_amount: data.order.amount_usd,
        tx_hash: ""
      });
      setNotice("");
      recordActionCompleted("client_payment_instructions_open", "report-payment", startedAt);
      return true;
    } catch (error) {
      if (paymentReportTargetIsCurrent(orderId)) {
        setNotice(error instanceof Error ? error.message : "Las instrucciones no estan disponibles para esta orden.");
      }
      recordActionFailed("client_payment_instructions_open", "report-payment", startedAt, error instanceof Error ? error.name : undefined);
      return false;
    } finally {
      if (paymentReportTargetOrderIdRef.current === orderId) {
        paymentReportTargetOrderIdRef.current = null;
      }
      openingPaymentReportRef.current = false;
      setLoadingPaymentInstructions(false);
    }
  }

  async function uploadPaymentEvidence(file: File | null) {
    const orderId = paymentInstructions?.order.id || selectedOrder?.id || chatOrderId;
    if (!orderId || !file) {
      return;
    }
    const startedAt = actionStartedAt();
    recordActionStarted("client_payment_evidence_upload", "report-payment");
    setUploadingPaymentEvidence(true);
    const idempotencyScope = `payment_evidence_${orderId}`;
    try {
      const data = await uploadOrderPaymentEvidence<any>(request, orderId, file, pendingPaymentReportId, getIdempotencyKey(idempotencyScope, { orderId, pendingPaymentReportId, name: file.name, size: file.size }));
      clearIdempotencyKey(idempotencyScope);
      setPaymentEvidence(data.file);
      setPendingPaymentReportId(data.pending_payment_report_id);
      setNotice("");
      recordActionCompleted("client_payment_evidence_upload", "report-payment", startedAt);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "No logramos cargar el comprobante.");
      recordActionFailed("client_payment_evidence_upload", "report-payment", startedAt, error instanceof Error ? error.name : undefined);
    } finally {
      setUploadingPaymentEvidence(false);
    }
  }

  async function submitPaymentReport() {
    const orderId = paymentInstructions?.order.id || selectedOrder?.id || chatOrderId;
    if (!orderId) {
      setNotice("Selecciona una orden.");
      return;
    }
    let resolvedInstructions = paymentInstructions;
    if (!resolvedInstructions) {
      try {
        setLoadingPaymentInstructions(true);
        resolvedInstructions = await getPaymentInstructions<PaymentInstructions>(request, orderId);
        if (activeChatOrderIdRef.current !== orderId && selectedOrder?.id !== orderId) {
          return;
        }
        setPaymentInstructions(resolvedInstructions);
      } catch (error) {
        setNotice(error instanceof Error ? error.message : "Las instrucciones no estan disponibles para esta orden.");
        return;
      } finally {
        setLoadingPaymentInstructions(false);
      }
    }
    const paymentMethod = resolvedInstructions.payment_instructions.method_type || selectedOrder?.payment_method_snapshot;
    const lockedPaymentAmount = resolvedInstructions.order.amount_usd || selectedOrder?.amount_usd;
    if (!paymentMethod || !lockedPaymentAmount) {
      setNotice("Selecciona una orden.");
      return;
    }
    const isZelle = paymentMethod === "zelle";
    if (isZelle && (!paymentEvidence || !pendingPaymentReportId)) {
      setNotice("Zelle requiere comprobante.");
      return;
    }
    if (!isZelle && !paymentReportForm.tx_hash) {
      setNotice("USDT TRC20 requiere tx_hash.");
      return;
    }
    const startedAt = actionStartedAt();
    recordActionStarted("client_payment_report_submit", "report-payment");
    setSubmittingPaymentReport(true);
    const idempotencyScope = `payment_report_${orderId}`;
    try {
      const data = await submitOrderPaymentReport<any>(
        request,
        orderId,
        isZelle
          ? {
              payment_type: "zelle",
              payment_amount: lockedPaymentAmount,
              proof_file_id: paymentEvidence?.id,
              pending_payment_report_id: pendingPaymentReportId
            }
          : {
              payment_type: "usdt_trc20",
              tx_hash: paymentReportForm.tx_hash,
              network: "TRC20",
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
      setPaymentInstructions(null);
      setPaymentEvidence(null);
      setPendingPaymentReportId(null);
      setPaymentReportForm((current) => ({
        ...current,
        payment_reference: "",
        payment_sender_name: "",
        payment_sender_account_masked: "",
        tx_hash: ""
      }));
      setView("order-chat");
      setNotice("");
      await refreshChatAfterPaymentReport({ silent: true });
      void loadMyOrders();
      recordActionCompleted("client_payment_report_submit", "report-payment", startedAt);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "No pudimos reportar el pago.");
      recordActionFailed("client_payment_report_submit", "report-payment", startedAt, error instanceof Error ? error.name : undefined);
    } finally {
      setSubmittingPaymentReport(false);
    }
  }

  return { openPaymentReport, uploadPaymentEvidence, submitPaymentReport };
}
