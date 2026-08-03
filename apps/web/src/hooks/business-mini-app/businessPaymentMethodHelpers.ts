import type { BusinessPaymentMethod, BusinessPaymentMethodFormState } from "../../types/business";

const USDT_WALLET_ADDRESS = /^[A-Za-z0-9]{20,120}$/;

export function activeBusinessPaymentMethods(methods: BusinessPaymentMethod[]) {
  return methods.filter((method) => method.is_available !== false);
}

export function emptyPaymentMethodForm(methodType: BusinessPaymentMethodFormState["method_type"] = "zelle"): BusinessPaymentMethodFormState {
  return { method_type: methodType, account_value: "", holder_name: "" };
}

export function paymentMethodDisplay(methodType: BusinessPaymentMethodFormState["method_type"]) {
  return methodType === "usdt_trc20" ? "USDT" : "Zelle";
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
    return methodType === "usdt_trc20" ? "Escribe la wallet USDT." : "Escribe el Zelle.";
  }
  if (normalizedAccount && methodType === "usdt_trc20" && !USDT_WALLET_ADDRESS.test(normalizedAccount)) {
    return "Revisa la wallet USDT. Confirma la red exacta con el cliente por chat.";
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
      ? "Revisa la wallet USDT. Confirma la red exacta con el cliente por chat."
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
