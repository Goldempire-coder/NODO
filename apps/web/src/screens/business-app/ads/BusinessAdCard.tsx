import { Button } from "@telegram-apps/telegram-ui";
import type { AdSummary } from "../../../types/ads";
import type { BusinessPaymentMethod } from "../../../types/business";
import { BusinessAdAmount } from "./BusinessAdAmount";
import { BusinessAdCurrencyLabel } from "./BusinessAdCurrencyLabel";
import { adAmountPresentation, canDeleteAd, canRepublishAd, displayRate, humanizeAdStatus, paymentMethodCanReceive, paymentMethodLabel } from "./businessAdViewHelpers";

export function BusinessAdCard({
  ad,
  isDeleting,
  isDeleteConfirming,
  isSelected,
  isPausing,
  isReactivating,
  isRepublishing,
  onDelete,
  onOpen,
  onPause,
  onReactivate,
  onRepublish,
  paymentMethods
}: {
  ad: AdSummary;
  isDeleting: boolean;
  isDeleteConfirming?: boolean;
  isSelected: boolean;
  isPausing: boolean;
  isReactivating: boolean;
  isRepublishing?: boolean;
  onDelete: () => void;
  onOpen: () => void;
  onPause: () => void;
  onReactivate: () => void;
  onRepublish?: () => void;
  paymentMethods: BusinessPaymentMethod[];
}) {
  const status = ad.effective_status || ad.status;
  const republishable = canRepublishAd(ad);
  const canReactivate = status === "paused" && paymentMethodCanReceive(ad, paymentMethods);
  const currencyPresentation = adAmountPresentation(ad);
  return (
    <article className={isSelected ? "business-ad-card is-selected" : "business-ad-card"}>
      <div className="business-ad-card__main">
        <span className={`business-status-chip business-status-chip--${status}`}>{humanizeAdStatus(status)}</span>
        <strong><BusinessAdAmount ad={ad} /></strong>
        <span>{displayRate(ad)} / <BusinessAdCurrencyLabel presentation={currencyPresentation} /></span>
        <small>{paymentMethodLabel(ad, paymentMethods)}</small>
      </div>
      <div className="business-ad-card__actions">
        <Button mode="outline" size="s" onClick={onOpen}>Ver</Button>
        {republishable ? (
          <Button mode="filled" size="s" disabled={isRepublishing || !onRepublish} onClick={onRepublish}>{isRepublishing ? "Republicando..." : "Republicar"}</Button>
        ) : (
          <>
            <Button mode="outline" size="s" disabled={isPausing || status !== "active"} onClick={onPause}>{isPausing ? "Pausando..." : "Pausar"}</Button>
            <Button mode="outline" size="s" disabled={isReactivating || !canReactivate} onClick={onReactivate}>{isReactivating ? "Reactivando..." : "Reactivar"}</Button>
          </>
        )}
        <Button mode="outline" size="s" disabled={isDeleting || !canDeleteAd(ad)} onClick={onDelete}>{isDeleting ? "Borrando..." : isDeleteConfirming ? "Confirmar borrar" : "Borrar"}</Button>
        {isDeleteConfirming ? <small>Consume el credito de esta publicacion.</small> : null}
      </div>
    </article>
  );
}
