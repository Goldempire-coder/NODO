import { ApiClientError } from "../../api/client";
import type { BusinessMiniAppView } from "../../constants/businessViews";
import type { BusinessSummary } from "../../types/business";

const BUSINESS_PIN_ERROR_CODES = new Set([
  "BUSINESS_PIN_NOT_SET",
  "BUSINESS_PIN_REQUIRED",
  "BUSINESS_PIN_LOCKED"
]);

export function isBusinessPinError(error: unknown): error is ApiClientError {
  return error instanceof ApiClientError
    && (BUSINESS_PIN_ERROR_CODES.has(error.code) || error.statusCode === 423);
}

export function businessPinActionMessage(errorCode: string, action: string) {
  if (errorCode === "BUSINESS_PIN_LOCKED") {
    return "Tu PIN esta bloqueado temporalmente. Intenta de nuevo mas tarde.";
  }
  if (errorCode === "BUSINESS_PIN_NOT_SET") {
    return `Crea tu PIN para ${action}.`;
  }
  return `Desbloquea tu PIN para ${action}.`;
}

export function requireUnlockedBusinessPin({
  action,
  business,
  setNotice,
  setView
}: {
  action: string;
  business: BusinessSummary | null;
  setNotice: (notice: string) => void;
  setView: (view: BusinessMiniAppView) => void;
}) {
  const link = business?.access_link;
  if (!link?.pin_required) {
    return true;
  }
  if (!link.pin_configured) {
    setNotice(businessPinActionMessage("BUSINESS_PIN_NOT_SET", action));
    setView("business-pin");
    return false;
  }
  if (!link.pin_unlocked) {
    setNotice(businessPinActionMessage("BUSINESS_PIN_REQUIRED", action));
    setView("business-pin");
    return false;
  }
  return true;
}

export function handleBusinessPinError({
  action,
  error,
  setNotice,
  setView
}: {
  action: string;
  error: unknown;
  setNotice: (notice: string) => void;
  setView: (view: BusinessMiniAppView) => void;
}) {
  if (!isBusinessPinError(error)) {
    return false;
  }
  setNotice(businessPinActionMessage(error.code, action));
  setView("business-pin");
  return true;
}
