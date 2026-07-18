import { useCallback, useState } from "react";
import type { Dispatch, SetStateAction } from "react";
import { updateBusinessAvailability } from "../../api/businesses";
import { ApiClientError, type AuthenticatedRequest } from "../../api/client";
import type { BusinessSummary } from "../../types/business";
import { actionStartedAt, recordBusinessActionCompleted, recordBusinessActionFailed, recordBusinessActionStarted } from "../actionTelemetry";
import { useStableIdempotencyKeys } from "../useStableIdempotencyKeys";

export function useBusinessAvailabilityModel({
  business,
  handleBusinessPinError,
  request,
  requireBusinessPinFor,
  setBusiness,
  setNotice
}: {
  business: BusinessSummary | null;
  handleBusinessPinError: (error: unknown, action: string) => boolean;
  request: AuthenticatedRequest;
  requireBusinessPinFor: (action: string) => boolean;
  setBusiness: Dispatch<SetStateAction<BusinessSummary | null>>;
  setNotice: (notice: string) => void;
}) {
  const [pendingAvailabilityTarget, setPendingAvailabilityTarget] = useState<boolean | null>(null);
  const [updatingAvailability, setUpdatingAvailability] = useState(false);
  const { clearIdempotencyKey, getIdempotencyKey } = useStableIdempotencyKeys();

  const setBusinessAvailabilityUnlocked = useCallback(async (acceptingOrders: boolean) => {
    setUpdatingAvailability(true);
    const startedAt = actionStartedAt();
    recordBusinessActionStarted("business_availability_update", "business-dashboard");
    const idempotencyScope = `business_availability_${acceptingOrders ? "online" : "offline"}`;
    try {
      const data = await updateBusinessAvailability<{ business: BusinessSummary }>(
        request,
        acceptingOrders,
        getIdempotencyKey(idempotencyScope, { acceptingOrders })
      );
      clearIdempotencyKey(idempotencyScope);
      setBusiness(data.business);
      setNotice(acceptingOrders ? "Negocio online. Tus anuncios activos pueden recibir ordenes." : "Negocio offline. Tus anuncios no apareceran para nuevas ordenes.");
      recordBusinessActionCompleted("business_availability_update", "business-dashboard", startedAt);
    } catch (error) {
      if (handleBusinessPinError(error, acceptingOrders ? "poner el negocio online" : "poner el negocio offline")) {
        setPendingAvailabilityTarget(acceptingOrders);
        recordBusinessActionFailed("business_availability_update", "business-dashboard", startedAt, "BUSINESS_PIN_REQUIRED");
        return;
      }
      recordBusinessActionFailed("business_availability_update", "business-dashboard", startedAt, error instanceof ApiClientError ? error.code : undefined);
      setNotice(error instanceof Error ? error.message : "No pudimos cambiar tu estado online.");
    } finally {
      setUpdatingAvailability(false);
    }
  }, [clearIdempotencyKey, getIdempotencyKey, handleBusinessPinError, request, setBusiness, setNotice]);

  const setBusinessAvailability = useCallback(async (acceptingOrders: boolean) => {
    const action = acceptingOrders ? "poner el negocio online" : "poner el negocio offline";
    if (!requireBusinessPinFor(action)) {
      setPendingAvailabilityTarget(acceptingOrders);
      return;
    }
    await setBusinessAvailabilityUnlocked(acceptingOrders);
  }, [requireBusinessPinFor, setBusinessAvailabilityUnlocked]);

  const clearPendingAvailabilityTarget = useCallback(() => {
    setPendingAvailabilityTarget(null);
  }, []);

  return {
    clearPendingAvailabilityTarget,
    pendingAvailabilityTarget,
    setBusinessAvailability,
    setBusinessAvailabilityUnlocked,
    updatingAvailability
  };
}
