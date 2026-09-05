import { paymentMethodCurrencyPresentation } from "../../../constants/paymentLabels";
import type { AdSummary } from "../../../types/ads";
import { displayBusinessName } from "../RemitterScreens.types";
import { ClientMarketplaceCurrencyLabel } from "./ClientMarketplaceCurrencyLabel";

function businessReputationSummary(ad: AdSummary): string {
  return ad.business?.reputation?.label || "Perfil registrado";
}

function businessAvailabilitySummary(ad: AdSummary): string {
  return ad.business?.availability?.status === "offline"
    ? "No disponible para nuevas solicitudes"
    : "Disponible para solicitudes";
}

function businessRatingSummary(ad: AdSummary): string | null {
  const ratingAvg = ad.business?.reputation?.rating_avg;
  const ratingsCount = ad.business?.reputation?.ratings_count;
  if (!ratingAvg || !ratingsCount) {
    return null;
  }
  const parsedRating = Number(ratingAvg);
  const displayRating = Number.isFinite(parsedRating) ? parsedRating.toFixed(1) : ratingAvg;
  return `Calificación: ${displayRating}/5 (${ratingsCount})`;
}

function businessAvailabilityBadge(ad: AdSummary): string {
  return ad.business?.availability?.status === "offline" ? "No disponible" : "Disponible";
}

export function ClientMarketplaceAdCard({
  ad,
  opening,
  onOpen
}: {
  ad: AdSummary;
  opening: boolean;
  onOpen: (adId: string) => void;
}) {
  const businessName = displayBusinessName(ad);
  const presentation = paymentMethodCurrencyPresentation(ad.payment_method);
  const ratingSummary = businessRatingSummary(ad);

  return (
    <button
      aria-label={`Abrir oferta ${presentation.offerLabel} de ${businessName}`}
      className="marketplace-business"
      disabled={opening}
      type="button"
      onClick={() => onOpen(ad.id)}
    >
      <span className="business-avatar">{businessName.slice(0, 2).toUpperCase()}</span>
      <span className="business-main">
        <strong>{businessName}</strong>
        <small className="client-marketplace-method">{presentation.offerLabel}</small>
        <small>{businessReputationSummary(ad)}</small>
        {ratingSummary ? <small>{ratingSummary}</small> : null}
        <small>{businessAvailabilitySummary(ad)}</small>
        <small>
          Límites: {ad.amount_min_usd} - {ad.amount_max_usd}{" "}
          <ClientMarketplaceCurrencyLabel presentation={presentation} />
        </small>
      </span>
      <span className="business-rate">
        <strong>{ad.rate_bs_per_usd}</strong>
        <small>
          Bs. / <ClientMarketplaceCurrencyLabel presentation={presentation} />
        </small>
        <em>{opening ? "Abriendo..." : businessAvailabilityBadge(ad)}</em>
      </span>
    </button>
  );
}
