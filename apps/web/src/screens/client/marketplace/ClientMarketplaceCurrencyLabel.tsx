import type { PaymentMethodCurrencyPresentation } from "../../../constants/paymentLabels";

export function ClientMarketplaceCurrencyLabel({
  presentation
}: {
  presentation: PaymentMethodCurrencyPresentation;
}) {
  return (
    <span
      className={`client-marketplace-currency client-marketplace-currency--${presentation.currencyTone}`}
    >
      {presentation.currencyLabel}
    </span>
  );
}
