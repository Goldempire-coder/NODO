import type { BusinessPaymentMethod, BusinessPaymentMethodFormState } from "../../types/business";

export function activeBusinessPaymentMethods(methods: BusinessPaymentMethod[]) {
  return methods.filter((method) => method.is_available !== false);
}

export function emptyPaymentMethodForm(methodType: BusinessPaymentMethodFormState["method_type"] = "zelle"): BusinessPaymentMethodFormState {
  return { method_type: methodType, account_value: "", holder_name: "" };
}

export function paymentMethodDisplay(methodType: BusinessPaymentMethodFormState["method_type"]) {
  return methodType === "usdt_trc20" ? "USDT TRC20" : "Zelle";
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
