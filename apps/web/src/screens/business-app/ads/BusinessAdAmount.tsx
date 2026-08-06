import type { AdSummary } from "../../../types/ads";
import { BusinessAdCurrencyLabel } from "./BusinessAdCurrencyLabel";
import { adAmountPresentation } from "./businessAdViewHelpers";

export function BusinessAdAmount({ ad }: { ad: AdSummary }) {
  const { rangeText, ...currencyPresentation } = adAmountPresentation(ad);

  return (
    <>
      <span className="business-ad-amount__range">{rangeText}</span>{" "}
      <BusinessAdCurrencyLabel presentation={currencyPresentation} />
    </>
  );
}
