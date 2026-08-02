import type { BusinessPaymentMethod, BusinessPaymentMethodFormState } from "../../types/business";

const TRON_BASE58_ADDRESS = /^T[1-9A-HJ-NP-Za-km-z]{33}$/;

export function activeBusinessPaymentMethods(methods: BusinessPaymentMethod[]) {
  return methods.filter((method) => method.is_available !== false);
}

export function emptyPaymentMethodForm(methodType: BusinessPaymentMethodFormState["method_type"] = "zelle"): BusinessPaymentMethodFormState {
  return { method_type: methodType, account_value: "", holder_name: "" };
}

export function paymentMethodDisplay(methodType: BusinessPaymentMethodFormState["method_type"]) {
  return methodType === "usdt_trc20" ? "USDT TRC20" : "Zelle";
}

export function normalizePaymentMethodAccount(methodType: BusinessPaymentMethodFormState["method_type"], accountValue: string) {
  return methodType === "usdt_trc20"
    ? accountValue.trim().replace(/\s+/g, "")
    : accountValue.trim();
}

export function paymentMethodInputError({
  accountValue,
  editing,
  holderName,
  methodType
}: {
  accountValue: string;
  editing: boolean;
  holderName: string;
  methodType: BusinessPaymentMethodFormState["method_type"];
}) {
  const normalizedAccount = normalizePaymentMethodAccount(methodType, accountValue);
  if (!editing && !normalizedAccount) {
    return methodType === "usdt_trc20" ? "Escribe la wallet USDT TRC20." : "Escribe el Zelle.";
  }
  if (normalizedAccount && methodType === "usdt_trc20" && !TRON_BASE58_ADDRESS.test(normalizedAccount)) {
    return "La wallet USDT TRC20 debe comenzar con T y tener 34 caracteres validos.";
  }
  if (normalizedAccount && methodType === "zelle" && normalizedAccount.length < 3) {
    return "Revisa el Zelle que escribiste.";
  }
  if (holderName.trim().length < 2) {
    return "Escribe el nombre del titular.";
  }
  return "";
}

export function paymentMethodRequestError(
  errorCode: string | undefined,
  methodType: BusinessPaymentMethodFormState["method_type"],
  fallback: string
) {
  if (errorCode === "PAYMENT_METHOD_INVALID") {
    return methodType === "usdt_trc20"
      ? "La wallet USDT TRC20 no es valida. Debe comenzar con T y tener 34 caracteres validos."
      : "Revisa el Zelle y el nombre del titular.";
  }
  if (errorCode === "PAYMENT_METHOD_LIMIT_REACHED") {
    return `Ya alcanzaste el limite de ${paymentMethodDisplay(methodType)} guardados.`;
  }
  if (errorCode === "BUSINESS_NOT_APPROVED") {
    return "El negocio debe estar aprobado para guardar metodos de cobro.";
  }
  return fallback;
}

const PAYMENT_METHOD_TELEMETRY_ACTIONS = {
  zelle_add: "zelle_add",
  zelle_edit: "zelle_edit",
  zelle_delete: "zelle_delete",
  usdt_wallet_add: "usdt_wallet_add",
  usdt_wallet_edit: "usdt_wallet_edit",
  usdt_wallet_delete: "usdt_wallet_delete"
} as const;

export function paymentMethodTelemetry(methodType: BusinessPaymentMethodFormState["method_type"], action: "add" | "edit" | "delete") {
  return methodType === "usdt_trc20"
    ? PAYMENT_METHOD_TELEMETRY_ACTIONS[`usdt_wallet_${action}`]
    : PAYMENT_METHOD_TELEMETRY_ACTIONS[`zelle_${action}`];
}
