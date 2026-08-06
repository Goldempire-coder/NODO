import { humanizeAdStatus } from "../../../hooks/business-mini-app/helpers";
import type { AdSummary } from "../../../types/ads";
import type { BusinessPaymentMethod } from "../../../types/business";

const AD_AMOUNT_PRESENTATION = {
  zelle: { currencyLabel: "USD", currencyTone: "usd" },
  usdt_trc20: { currencyLabel: "USDT", currencyTone: "usdt" }
} as const;

export type BusinessAdCurrencyPresentation = (typeof AD_AMOUNT_PRESENTATION)[keyof typeof AD_AMOUNT_PRESENTATION];

export function adAmountCurrencyPresentation(methodType: string | null | undefined) {
  return methodType === "usdt_trc20" ? AD_AMOUNT_PRESENTATION.usdt_trc20 : AD_AMOUNT_PRESENTATION.zelle;
}

export function adPaymentMethodType(ad: AdSummary, paymentMethods: BusinessPaymentMethod[] = []) {
  const fromMethod = paymentMethods.find((method) => method.id === ad.payment_method_id);
  return ad.payment_method_details?.method_type || fromMethod?.receive_method || ad.payment_method;
}

export function adAmountPresentation(ad: AdSummary, paymentMethods: BusinessPaymentMethod[] = []) {
  const methodType = adPaymentMethodType(ad, paymentMethods);
  const currency = adAmountCurrencyPresentation(methodType);
  return {
    rangeText: `${ad.amount_min_usd} - ${ad.amount_max_usd}`,
    ...currency
  };
}

export function displayRate(ad: AdSummary) {
  return `Bs. ${ad.rate_bs_per_usd}`;
}

export function displayAdDate(value: string | null | undefined) {
  if (!value) {
    return "-";
  }
  return new Date(value).toLocaleDateString("es-VE", { day: "2-digit", month: "short" });
}

export function paymentMethodDisplayName(methodType: string | null | undefined) {
  return methodType === "usdt_trc20" ? "USDT" : "Zelle";
}

export function paymentMethodLabel(ad: AdSummary, paymentMethods: BusinessPaymentMethod[]) {
  const fromMethod = paymentMethods.find((method) => method.id === ad.payment_method_id);
  const methodName = paymentMethodDisplayName(adPaymentMethodType(ad, paymentMethods));
  const holder = ad.payment_method_details?.holder_name || fromMethod?.holder_name || methodName;
  const account = ad.payment_method_details?.account_masked || fromMethod?.masked_account || "guardado";
  const active = ad.payment_method_details?.active ?? fromMethod?.is_available;
  return `${methodName} - ${holder} - ${account}${active === false ? " (borrado)" : ""}`;
}

export function canDeleteAd(ad: AdSummary) {
  const status = ad.effective_status || ad.status;
  return status === "active" || status === "paused" || status === "expired";
}

export function canRepublishAd(ad: AdSummary) {
  const status = ad.effective_status || ad.status;
  return status === "archived" || status === "expired";
}

export function paymentMethodCanReceive(ad: AdSummary, paymentMethods: BusinessPaymentMethod[]) {
  const fromMethod = paymentMethods.find((method) => method.id === ad.payment_method_id);
  if (ad.payment_method_details) {
    return ad.payment_method_details.active !== false && (ad.payment_method_details.verified_status || "approved") === "approved";
  }
  return fromMethod ? fromMethod.is_available : true;
}

export { humanizeAdStatus };
