import { useCallback, useState } from "react";
import type { ConfirmAction } from "./adminWebTypes";

export function useAdminCriticalAction({
  setBusy,
  setNotice
}: {
  setBusy: (busy: boolean) => void;
  setNotice: (notice: string) => void;
}) {
  const [reason, setReason] = useState("");
  const [pendingAction, setPendingAction] = useState<ConfirmAction | null>(null);

  const queueCriticalAction = useCallback((title: string, detail: string, run: () => Promise<void>) => {
    if (!reason.trim()) {
      setNotice("Motivo obligatorio antes de ejecutar accion admin.");
      return;
    }
    setPendingAction({ title, detail, run });
  }, [reason, setNotice]);

  const confirmPendingAction = useCallback(async () => {
    const action = pendingAction;
    if (!action) {
      return;
    }
    setPendingAction(null);
    setBusy(true);
    try {
      await action.run();
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "No se pudo completar la accion admin.");
    } finally {
      setBusy(false);
    }
  }, [pendingAction, setBusy, setNotice]);

  return {
    confirmPendingAction,
    pendingAction,
    queueCriticalAction,
    reason,
    setPendingAction,
    setReason
  };
}
