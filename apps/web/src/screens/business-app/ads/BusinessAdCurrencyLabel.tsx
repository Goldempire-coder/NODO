import type { BusinessAdCurrencyPresentation } from "./businessAdViewHelpers";

export function BusinessAdCurrencyLabel({ presentation }: { presentation: BusinessAdCurrencyPresentation }) {
  return (
    <span className={`business-ad-currency business-ad-currency--${presentation.currencyTone}`}>
      {presentation.currencyLabel}
    </span>
  );
}
