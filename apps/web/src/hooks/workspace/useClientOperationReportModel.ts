"use client";

import { useCallback, useState } from "react";
import { createOperationReport } from "../../api/support";
import type { AuthenticatedRequest } from "../../api/client";
import type { OperationReportCreateInput } from "../../types/support";
import { useStableIdempotencyKeys } from "../useStableIdempotencyKeys";

type OperationReportFeedback = {
  orderId: string;
  message: string;
};

export function useClientOperationReportModel({
  request,
  setNotice
}: {
  request: AuthenticatedRequest;
  setNotice: (notice: string) => void;
}) {
  const [creatingOperationReportOrderId, setCreatingOperationReportOrderId] = useState<string | null>(null);
  const [operationReportError, setOperationReportError] = useState<OperationReportFeedback | null>(null);
  const [operationReportSuccessOrderId, setOperationReportSuccessOrderId] = useState<string | null>(null);
  const { clearIdempotencyKey, getIdempotencyKey } = useStableIdempotencyKeys();

  const submitOperationReport = useCallback(async (
    orderId: string,
    input: OperationReportCreateInput
  ): Promise<boolean> => {
    const payload = { ...input, message: input.message.trim() };
    const idempotencyScope = `operation_report_${orderId}`;
    setCreatingOperationReportOrderId(orderId);
    setOperationReportError(null);
    try {
      await createOperationReport(
        request,
        orderId,
        payload,
        getIdempotencyKey(idempotencyScope, { orderId, ...payload })
      );
      clearIdempotencyKey(idempotencyScope);
      setOperationReportSuccessOrderId(orderId);
      setNotice("Reporte recibido. Soporte NODO revisara la operacion.");
      return true;
    } catch (error) {
      const message = error instanceof Error
        ? error.message
        : "No pudimos enviar el reporte. Tu informacion sigue lista para reintentar.";
      setOperationReportError({ orderId, message });
      return false;
    } finally {
      setCreatingOperationReportOrderId(null);
    }
  }, [clearIdempotencyKey, getIdempotencyKey, request, setNotice]);

  return {
    creatingOperationReportOrderId,
    operationReportError,
    operationReportSuccessOrderId,
    submitOperationReport
  };
}
