import type { AdSummary } from "../../../types/ads";
import type { BusinessPaymentMethod } from "../../../types/business";
import { BusinessAdCurrencyLabel } from "./BusinessAdCurrencyLabel";
import { adAmountPresentation } from "./businessAdViewHelpers";

export function BusinessAdAmount({ ad, paymentMethods = [] }: { ad: AdSummary; paymentMethods?: BusinessPaymentMethod[] }) {
  const { rangeText, ...currencyPresentation } = adAmountPresentation(ad, paymentMethods);

  return (
    <>
      <span className="business-ad-amount__range">{rangeText}</span>{" "}
      <BusinessAdCurrencyLabel presentation={currencyPresentation} />
    </>
  );
}
