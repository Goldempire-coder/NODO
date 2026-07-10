import { useCallback, useState } from "react";
import { submitAdminCreditAdjustment } from "../../api/admin";
import type { AuthenticatedRequest } from "../../api/client";
import { idempotencyKey } from "./helpers";
import type { QueueCriticalAction } from "./adminCreditsTypes";

export function useAdminCreditAdjustmentsModel({
  adminMutable,
  queueCriticalAction,
  reason,
  request,
  setNotice,
  setReason
}: {
  adminMutable: boolean;
  queueCriticalAction: QueueCriticalAction;
  reason: string;
  request: AuthenticatedRequest;
  setNotice: (notice: string) => void;
  setReason: (reason: string) => void;
}) {
  const [adjustmentBusinessId, setAdjustmentBusinessId] = useState("");
  const [adjustmentAmount, setAdjustmentAmount] = useState("1");
  const [adjustmentDirection, setAdjustmentDirection] = useState<"add" | "remove">("add");

  const submitAdjustment = useCallback(() => {
    if (!adminMutable) {
      setNotice("Support no puede ajustar creditos.");
      return;
    }
    if (!adjustmentBusinessId.trim() || !adjustmentAmount.trim()) {
      setNotice("Business ID y monto son obligatorios.");
      return;
    }
    queueCriticalAction("Aplicar ajuste de creditos", "El ajuste crea ledger admin_adjustment desde backend.", async () => {
      await submitAdminCreditAdjustment(request, {
        business_id: adjustmentBusinessId,
        amount: Number.parseInt(adjustmentAmount, 10),
        direction: adjustmentDirection,
        reason
      }, idempotencyKey("credit_adjust"));
      setReason("");
      setNotice("Ajuste enviado al backend.");
    });
  }, [adminMutable, adjustmentAmount, adjustmentBusinessId, adjustmentDirection, queueCriticalAction, reason, request, setNotice, setReason]);

  return {
    adjustmentAmount,
    adjustmentBusinessId,
    adjustmentDirection,
    setAdjustmentAmount,
    setAdjustmentBusinessId,
    setAdjustmentDirection,
    submitAdjustment
  };
}
