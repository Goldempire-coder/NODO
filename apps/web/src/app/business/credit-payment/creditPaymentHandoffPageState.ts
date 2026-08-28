export type PaymentStep = "wallet" | "checking" | "review" | "approval" | "pay" | "sent";

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
  return step === "sent"
    ? "Pago enviado"
    : `Pagaras ${amountDisplay} USDC de prueba en Base Sepolia`;
}

export function paymentStepBody(step: PaymentStep) {
  if (step === "approval") {
    return "MetaMask pedira permiso solo por el monto exacto de esta compra.";
  }
  if (step === "pay") {
    return "Autorizacion enviada. Si MetaMask aun la confirma, espera unos segundos antes de pagar.";
  }
  if (step === "sent") {
    return "Vuelve a NODO para ver la confirmacion de tus creditos.";
  }
  if (step === "review") {
    return "Puedes revisar el permiso sin crear otra compra.";
  }
  return "Revisando el permiso de USDC de prueba.";
}

export function expectedNetworkBody(isExpectedNetwork: boolean) {
  return isExpectedNetwork ? "Lista para esta compra de prueba." : "Cambia la red antes de continuar.";
}
