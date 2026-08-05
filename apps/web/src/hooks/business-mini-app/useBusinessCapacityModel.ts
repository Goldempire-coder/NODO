import { useCallback, useState } from "react";
import { getBusinessCapacity, updateBusinessCapacity } from "../../api/businesses";
import { ApiClientError, type AuthenticatedRequest } from "../../api/client";
import type { BusinessOperationalCapacity, BusinessSummary } from "../../types/business";
import {
  actionStartedAt,
  recordBusinessActionCompleted,
  recordBusinessActionFailed,
  recordBusinessActionStarted
} from "../actionTelemetry";
import { useStableIdempotencyKeys } from "../useStableIdempotencyKeys";

export type BusinessCapacityRefreshState = "idle" | "ready" | "stale";

export function useBusinessCapacityModel({
  business,
  handleBusinessPinError,
  request,
  requireBusinessPinFor,
  setNotice
}: {
  business: BusinessSummary | null;
  handleBusinessPinError: (error: unknown, action: string) => boolean;
  request: AuthenticatedRequest;
  requireBusinessPinFor: (action: string) => boolean;
  setNotice: (notice: string) => void;
}) {
  const [businessCapacity, setBusinessCapacity] = useState<BusinessOperationalCapacity | null>(null);
  const [businessCapacityDraft, setBusinessCapacityDraft] = useState("0.00");
  const [businessCapacityRefreshState, setBusinessCapacityRefreshState] =
    useState<BusinessCapacityRefreshState>("idle");
  const [savingBusinessCapacity, setSavingBusinessCapacity] = useState(false);
  const [pendingBusinessCapacityAmount, setPendingBusinessCapacityAmount] = useState<string | null>(null);
  const { clearIdempotencyKey, getIdempotencyKey } = useStableIdempotencyKeys();

  const refreshBusinessCapacity = useCallback(async () => {
    try {
      const data = await getBusinessCapacity<BusinessOperationalCapacity>(request);
      setBusinessCapacity(data);
      setBusinessCapacityDraft(data.declared_available_capacity_usd);
      setBusinessCapacityRefreshState("ready");
      return data;
    } catch (error) {
      setBusinessCapacityRefreshState("stale");
      throw error;
    }
  }, [request]);

  const saveBusinessCapacityUnlocked = useCallback(async (amount = businessCapacityDraft) => {
    const normalizedAmount = amount.trim();
    if (!/^\d+(\.\d{1,2})?$/.test(normalizedAmount)) {
      setNotice("Escribe un monto valido con hasta 2 decimales.");
      return false;
    }
    setSavingBusinessCapacity(true);
    const startedAt = actionStartedAt();
    recordBusinessActionStarted("business_capacity_update", "business-dashboard");
    const idempotencyScope = "business_operational_capacity";
    try {
      const data = await updateBusinessCapacity<BusinessOperationalCapacity>(
        request,
        {
          availability_status: business?.is_accepting_orders === false ? "offline" : "online",
          declared_available_capacity_usd: normalizedAmount
        },
        getIdempotencyKey(idempotencyScope, {
          availability_status: business?.is_accepting_orders === false ? "offline" : "online",
          declared_available_capacity_usd: normalizedAmount
        })
      );
      clearIdempotencyKey(idempotencyScope);
      setBusinessCapacity(data);
      setBusinessCapacityDraft(data.declared_available_capacity_usd);
      setBusinessCapacityRefreshState("ready");
      setPendingBusinessCapacityAmount(null);
      setNotice("Capacidad disponible actualizada.");
      recordBusinessActionCompleted("business_capacity_update", "business-dashboard", startedAt);
      return true;
    } catch (error) {
      if (handleBusinessPinError(error, "actualizar la capacidad disponible")) {
        setPendingBusinessCapacityAmount(normalizedAmount);
        recordBusinessActionFailed(
          "business_capacity_update",
          "business-dashboard",
          startedAt,
          "BUSINESS_PIN_REQUIRED"
        );
        return false;
      }
      const message = error instanceof ApiClientError && error.code === "BUSINESS_CAPACITY_BELOW_RESERVED"
        ? "No puedes bajar el disponible por debajo del monto reservado."
        : error instanceof ApiClientError && error.code === "BUSINESS_CAPACITY_BELOW_ACTIVE_ADS"
          ? "Pausa o ajusta tus anuncios activos, o termina las negociaciones abiertas, antes de bajar el disponible."
          : error instanceof Error
            ? error.message
            : "No pudimos actualizar la capacidad.";
      setNotice(message);
      recordBusinessActionFailed(
        "business_capacity_update",
        "business-dashboard",
        startedAt,
        error instanceof ApiClientError ? error.code : undefined
      );
      return false;
    } finally {
      setSavingBusinessCapacity(false);
    }
  }, [
    business?.is_accepting_orders,
    businessCapacityDraft,
    clearIdempotencyKey,
    getIdempotencyKey,
    handleBusinessPinError,
    request,
    setNotice
  ]);

  const saveBusinessCapacity = useCallback(async () => {
    if (!requireBusinessPinFor("actualizar la capacidad disponible")) {
      setPendingBusinessCapacityAmount(businessCapacityDraft.trim());
      return false;
    }
    return saveBusinessCapacityUnlocked();
  }, [businessCapacityDraft, requireBusinessPinFor, saveBusinessCapacityUnlocked]);

  return {
    businessCapacity,
    businessCapacityDraft,
    businessCapacityRefreshState,
    pendingBusinessCapacityAmount,
    refreshBusinessCapacity,
    saveBusinessCapacity,
    saveBusinessCapacityUnlocked,
    savingBusinessCapacity,
    setBusinessCapacityDraft,
    setPendingBusinessCapacityAmount
  };
}
