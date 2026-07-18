import { ApiClientError } from "../../api/client";
import type { BusinessMiniAppView } from "../../constants/businessViews";
import { createIdempotencyKey } from "../useStableIdempotencyKeys";

export type BusinessAccessState =
  | "loading"
  | "ready"
  | "no_business_link"
  | "business_not_approved"
  | "business_suspended"
  | "business_blocked"
  | "link_suspended"
  | "link_revoked"
  | "link_blocked"
  | "user_not_active"
  | "user_blocked"
  | "error";

export const ROOT_BUSINESS_VIEWS = new Set<BusinessMiniAppView>([
  "business-dashboard",
  "my-ads",
  "business-orders",
  "credits-dashboard",
  "business-settings"
]);

export function fallbackForBusinessMiniAppView(view: BusinessMiniAppView): BusinessMiniAppView {
  if (view === "business-order-detail" || view === "business-chat") {
    return "business-orders";
  }
  if (view === "archived-ads" || view === "payment-methods" || view === "create-ad") {
    return "my-ads";
  }
  if (view === "buy-credits" || view === "credit-payment-pending" || view === "referrals") {
    return "credits-dashboard";
  }
  if (view === "business-rules") {
    return "business-settings";
  }
  return "business-dashboard";
}

export function idempotencyKey(prefix: string) {
  return createIdempotencyKey(prefix);
}

export function accessStateFromError(error: unknown): BusinessAccessState {
  if (!(error instanceof ApiClientError)) {
    return "error";
  }
  const map: Record<string, BusinessAccessState> = {
    BUSINESS_ACCESS_LINK_REQUIRED: "no_business_link",
    BUSINESS_ACCESS_SUSPENDED: "link_suspended",
    BUSINESS_ACCESS_BLOCKED: "link_blocked",
    BUSINESS_ACCESS_REVOKED: "link_revoked",
    BUSINESS_NOT_APPROVED: "business_not_approved",
    BUSINESS_SUSPENDED: "business_suspended",
    BUSINESS_BLOCKED: "business_blocked",
    USER_NOT_ACTIVE: "user_not_active",
    USER_BLOCKED: "user_blocked",
    SURFACE_ACCESS_DENIED: "no_business_link"
  };
  return map[error.code] || "error";
}

export function humanizeOrderStatus(status: string) {
  const labels: Record<string, string> = {
    waiting_payment: "Esperando pago",
    payment_reported: "Pago reportado",
    payment_rejected: "Reporte rechazado",
    payment_confirmed: "Pago confirmado",
    delivered: "Enviado",
    completed: "Completada",
    disputed: "En revision",
    cancelled: "Cancelada"
  };
  return labels[status] || status.replaceAll("_", " ");
}

export function humanizeAdStatus(status: string) {
  const labels: Record<string, string> = {
    active: "Activo",
    paused: "Pausado",
    expired: "Expirado",
    archived: "Archivado",
    in_order: "En orden"
  };
  return labels[status] || status.replaceAll("_", " ");
}

export function humanizePurchaseStatus(status: string) {
  const labels: Record<string, string> = {
    pending_manual_review: "En revision",
    pending_payment: "Pago pendiente",
    pending_onchain_confirmation: "Confirmando en Base",
    under_review: "En revision NODO",
    verification_failed: "Verificacion fallida",
    pending_stripe: "Pago iniciado",
    pending: "Pendiente",
    active: "Activo",
    approved: "Aprobada",
    accepted: "Aceptado",
    corrected: "Corregido",
    rejected: "Rechazada",
    suspended: "Suspendida",
    blocked: "Bloqueada",
    credited: "Acreditada",
    cancelled: "Cancelada",
    submitted: "Enviada"
  };
  return labels[status] || status.replaceAll("_", " ");
}

export function humanizeSenderRole(role: string) {
  const labels: Record<string, string> = {
    remitter: "Cliente",
    business_owner: "Negocio",
    admin: "NODO",
    support: "Soporte"
  };
  return labels[role] || role.replaceAll("_", " ");
}
