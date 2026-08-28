import { getPublicEnv } from "../../lib/env";

export type BusinessCreditPackage = {
  code: string;
  name: string;
  credits: number;
  priceUsdc: string;
  hint: string;
};

// Display-only mirror; backend signs the authoritative amount before payment.
const BASE_CREDIT_PACKAGES: BusinessCreditPackage[] = [
  { code: "starter", name: "Starter", credits: 5, priceUsdc: "10", hint: "Para probar anuncios." },
  { code: "pro", name: "Pro", credits: 15, priceUsdc: "25", hint: "Para operar varios anuncios." },
  { code: "business", name: "Business", credits: 50, priceUsdc: "75", hint: "Mejor costo por credito." },
  { code: "enterprise", name: "Enterprise", credits: 200, priceUsdc: "250", hint: "Alto volumen." },
];
const TESTNET_CREDIT_PACKAGE_PRICE_SCALE = 0.01;
const TESTNET_CREDIT_PACKAGE_PRICE_ENVS = new Set(["local", "test", "staging"]);

export const AUTO_REFRESH_CREDIT_HANDOFF_MS = 3000;
export const AUTO_REFRESH_CREDIT_HANDOFF_LIMIT = 5;
export const AUTO_REFRESH_PENDING_CREDIT_PAYMENT_MS = 5000;
export const AUTO_REFRESH_PENDING_CREDIT_PAYMENT_LIMIT = 18;

const AUTO_REFRESHABLE_CREDIT_PAYMENT_STATUSES = new Set([
  "pending_payment",
  "pending_onchain_confirmation",
  "detected",
]);

function formatContractTestnetPrice(priceUsdc: string) {
  const numericPrice = Number(priceUsdc);
  if (!Number.isFinite(numericPrice)) {
    return priceUsdc;
  }
  return (numericPrice * TESTNET_CREDIT_PACKAGE_PRICE_SCALE).toFixed(2);
}

export function contractCreditPackagesForCurrentEnv() {
  const appEnv = getPublicEnv().NEXT_PUBLIC_APP_ENV.trim().toLowerCase();
  if (!TESTNET_CREDIT_PACKAGE_PRICE_ENVS.has(appEnv)) {
    return BASE_CREDIT_PACKAGES;
  }
  return BASE_CREDIT_PACKAGES.map((item) => ({
    ...item,
    priceUsdc: formatContractTestnetPrice(item.priceUsdc),
  }));
}

export function packageLabel(
  packageCode: string | null | undefined,
  packages = contractCreditPackagesForCurrentEnv(),
) {
  return packages.find((item) => item.code === packageCode) || null;
}

export function isAutoRefreshableCreditPaymentStatus(status: string | null | undefined) {
  return Boolean(status && AUTO_REFRESHABLE_CREDIT_PAYMENT_STATUSES.has(status));
}

export function paymentProgressCopy(status: string | null | undefined, canPay: boolean) {
  if (status === "credited") {
    return {
      title: "Pago exitoso",
      body: "Los creditos ya estan disponibles en tu negocio.",
    };
  }
  if (status === "pending_onchain_confirmation" || status === "detected") {
    return {
      title: "Estamos acreditando",
      body: "Ya vimos el pago. Normalmente termina en menos de un minuto. Esta pantalla se actualiza sola.",
    };
  }
  if (status === "under_review") {
    return {
      title: "Pago en revision",
      body: "NODO esta revisando este pago. No necesitas enviar otro intento.",
    };
  }
  if (canPay) {
    return {
      title: "Falta enviar el pago final",
      body: "La wallet ya esta preparada. Abre MetaMask y confirma el pago final.",
    };
  }
  return {
    title: "Nueva preparacion necesaria",
    body: "Este intento ya no puede pagarse. Prepara una compra nueva.",
  };
}

export function shouldContinueCreditPayment(status: string | null | undefined, canPay: boolean) {
  return status === "pending_payment" && canPay;
}

export function shouldOfferNewCreditPurchase(status: string | null | undefined, canPay: boolean) {
  if (canPay) {
    return false;
  }
  return !["pending_onchain_confirmation", "detected", "under_review", "credited"].includes(status || "");
}

export function creditedCreditsLabel(credits: number | null | undefined) {
  if (typeof credits === "number" && Number.isFinite(credits)) {
    return `${credits} creditos`;
  }
  return "tus creditos";
}

export function availableCreditsLabel(availableCredits: number | null | undefined) {
  if (typeof availableCredits === "number" && Number.isFinite(availableCredits)) {
    return {
      label: "Creditos disponibles",
      value: availableCredits,
    };
  }
  return null;
}
