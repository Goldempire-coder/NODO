export type PaymentStep = "wallet" | "checking" | "review" | "approval" | "pay" | "submitting" | "sent";

const HANDOFF_TOKEN_PATTERN = /^[A-Za-z0-9_-]{43}$/;

function readHandoffTokenFromHistoryState(state: unknown): string | null {
  if (!state || typeof state !== "object" || !("nodoCreditHandoffToken" in state)) {
    return null;
  }
  const token = (state as { nodoCreditHandoffToken?: unknown }).nodoCreditHandoffToken;
  return typeof token === "string" && HANDOFF_TOKEN_PATTERN.test(token) ? token : null;
}

export function extractCreditHandoffToken(search: string, fragment: string, pathname: string, historyState: unknown): string | null {
  const pathMatch = pathname.match(/^\/business\/credit-payment\/handoff\/([A-Za-z0-9_-]{43})\/?$/);
  const token = new URLSearchParams(search).get("handoff")
    || new URLSearchParams(fragment.replace(/^#/, "")).get("handoff")
    || pathMatch?.[1]
    || readHandoffTokenFromHistoryState(historyState);
  return token && HANDOFF_TOKEN_PATTERN.test(token) ? token : null;
}

export function returnToTelegram() {
  if (typeof window === "undefined") {
    return;
  }
  window.location.assign("tg://");
}

export function isWalletUserRejected(error: unknown): boolean {
  return Boolean(error && typeof error === "object" && "code" in error && error.code === 4001);
}

export function paymentStepTitle(step: PaymentStep, amountDisplay: string) {
  if (step === "sent") {
    return "Pago enviado";
  }
  if (step === "submitting") {
    return "Confirmando en MetaMask";
  }
  if (step === "pay") {
    return "Paso final: enviar pago";
  }
  if (step === "approval") {
    return "Autoriza el monto";
  }
  return `Compra por ${amountDisplay} USDC`;
}

export function paymentStepBody(step: PaymentStep) {
  if (step === "approval") {
    return "MetaMask pedira permiso solo por el monto exacto. Esto todavia no cobra.";
  }
  if (step === "pay") {
    return "Ya autorizaste el monto. Confirma el pago final en MetaMask.";
  }
  if (step === "submitting") {
    return "Confirma la transaccion en MetaMask. Al terminar, NODO acreditara los creditos automaticamente.";
  }
  if (step === "sent") {
    return "Vuelve a NODO. Los creditos se acreditan automaticamente; suele tardar menos de un minuto.";
  }
  if (step === "review") {
    return "Revisando si falta autorizar o enviar el pago final.";
  }
  return "Revisando el estado de la compra.";
}

export function expectedNetworkBody(isExpectedNetwork: boolean) {
  return isExpectedNetwork ? "Lista para pagar." : "Cambia la red para continuar.";
}
