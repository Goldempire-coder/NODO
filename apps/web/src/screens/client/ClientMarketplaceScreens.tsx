import { Button, Text, Title } from "@telegram-apps/telegram-ui";
import { ORDER_DISCLAIMER } from "../../constants/copy";
import { paymentMethodCurrencyPresentation } from "../../constants/paymentLabels";
import { sanitizeDecimalInput } from "../../lib/numericInput";
import { formatClientMethodLine } from "./clientMethodCopy";
import { ClientMarketplaceAdCard } from "./marketplace/ClientMarketplaceAdCard";
import { ClientMarketplaceCurrencyLabel } from "./marketplace/ClientMarketplaceCurrencyLabel";
import { displayBusinessName, type RemitterScreensModel } from "./RemitterScreens.types";

function MarketplaceBusinessList({
  emptyMessage,
  model
}: {
  emptyMessage: string;
  model: RemitterScreensModel;
}) {
  const {
    loadMoreActiveMarketplace,
    loadingMoreMarketplace,
    openAdDetail,
    openingMarketplaceAdId,
    searchResults,
    searchResultsNextCursor
  } = model;
  return (
    <div className="marketplace-list">
      {searchResults.length === 0 ? (
        <div className="trusted-empty">
          <span className="status-dot status-dot--muted" aria-hidden="true" />
          <Text>{emptyMessage}</Text>
        </div>
      ) : null}
      {searchResults.map((ad) => (
        <ClientMarketplaceAdCard
          ad={ad}
          key={ad.id}
          opening={openingMarketplaceAdId === ad.id}
          onOpen={(adId) => void openAdDetail(adId)}
        />
      ))}
      {searchResultsNextCursor ? (
        <Button mode="outline" size="s" disabled={loadingMoreMarketplace} onClick={() => void loadMoreActiveMarketplace()}>
          {loadingMoreMarketplace ? "Cargando..." : "Cargar más ofertas"}
        </Button>
      ) : null}
    </div>
  );
}

export function ClientMarketplaceScreens({ model }: { model: RemitterScreensModel }) {
  const {
    notice,
    searchAds,
    searchForm,
    searchingMarketplace,
    selectMarketplacePaymentMethod,
    selectedAd,
    setOrderForm,
    setSearchForm,
    setView,
    view
  } = model;
  const searchCurrency = paymentMethodCurrencyPresentation(searchForm.payment_method);
  const selectedAdCurrency = selectedAd
    ? paymentMethodCurrencyPresentation(selectedAd.payment_method)
    : null;

  return (
    <>
      {view === "marketplace-search" ? (
        <div className="marketplace-home">
          <div className="exchange-card">
            <Text className="exchange-card__eyebrow">Directorio de ofertas</Text>
            <Title level="2" className="exchange-card__title">¿Qué monto buscas?</Title>
            <div className={searchCurrency.amountSymbol ? "amount-input" : "amount-input amount-input--without-symbol"}>
              {searchCurrency.amountSymbol ? <span aria-hidden="true">{searchCurrency.amountSymbol}</span> : null}
              <input
                aria-label={`Monto en ${searchCurrency.currencyLabel}`}
                value={searchForm.amount_usd}
                onChange={(event) => setSearchForm((current) => ({
                  ...current,
                  amount_usd: sanitizeDecimalInput(event.target.value, {
                    maxDecimals: 2,
                    maxIntegerDigits: 6
                  })
                }))}
                inputMode="decimal"
                pattern="[0-9]*[.]?[0-9]*"
                autoComplete="off"
              />
              <strong>
                <ClientMarketplaceCurrencyLabel presentation={searchCurrency} />
              </strong>
            </div>
            <Text className="auth-entry__session-meta">
              Monto mínimo: {searchCurrency.amountSymbol}20.00 {searchCurrency.currencyLabel}
            </Text>
            <Text className="exchange-card__section-label">Elige un método publicado</Text>
            <div className="payment-choice">
              <button
                className={searchForm.payment_method === "zelle" ? "is-active" : ""}
                type="button"
                onClick={() => selectMarketplacePaymentMethod("zelle")}
              >
                <span className="payment-choice__brand payment-choice__brand--zelle">Zelle</span>
              </button>
              <button
                className={searchForm.payment_method === "usdt_trc20" ? "is-active" : ""}
                type="button"
                onClick={() => selectMarketplacePaymentMethod("usdt_trc20")}
              >
                <span className="coin-badge">T</span>
                USDT
              </button>
            </div>
            <div className="receiver-note">
              <span className="status-dot" aria-hidden="true" />
              <Text>Entrega publicada: Pago Móvil en Venezuela. Coordina los detalles directamente con el negocio.</Text>
            </div>
            <Button mode="filled" stretched disabled={searchingMarketplace} onClick={() => void searchAds()}>
              {searchingMarketplace ? "Buscando..." : "Buscar ofertas"}
            </Button>
          </div>
          {notice ? <Text className="auth-entry__session-meta">{notice}</Text> : null}

          <div className="marketplace-toolbar">
            <Title level="3" className="business-shell__title">Ofertas disponibles</Title>
            <Text className="auth-entry__session-meta">{searchCurrency.offerLabel} - condiciones publicadas</Text>
          </div>

          <MarketplaceBusinessList
            emptyMessage="Ingresa un monto para ver ofertas disponibles."
            model={model}
          />

          <div className="trust-banner">
            <span className="status-dot" aria-hidden="true" />
            <Text>Revisa monto, condiciones y disponibilidad. Cada negocio publica sus datos.</Text>
          </div>
        </div>
      ) : null}

      {view === "marketplace-list" ? (
        <div className="marketplace-home marketplace-home--list">
          <div className="marketplace-toolbar">
            <div>
              <Text className="exchange-card__eyebrow">Directorio</Text>
              <Title level="3" className="business-shell__title">Ofertas disponibles</Title>
            </div>
            <Text className="auth-entry__session-meta">{searchCurrency.offerLabel} - condiciones publicadas</Text>
          </div>

          <MarketplaceBusinessList
            emptyMessage={`No hay ofertas ${searchCurrency.offerLabel} disponibles en este momento.`}
            model={model}
          />

          <div className="trust-banner">
            <span className="status-dot" aria-hidden="true" />
            <Text>Cuando haya ofertas para {searchCurrency.offerLabel}, elige una y coordina directamente con el negocio.</Text>
          </div>
        </div>
      ) : null}

      {view === "marketplace-detail" ? (
        <div className="business-card marketplace-detail-card">
          <Text className="business-card__label">Perfil registrado</Text>
          {selectedAd && selectedAdCurrency ? (
            <>
              <Title level="3" className="business-shell__title">{displayBusinessName(selectedAd)}</Title>
              <Text>{formatClientMethodLine(selectedAd.payment_method, selectedAd.delivery_method)}</Text>
              <Text>
                Rango {selectedAdCurrency.amountSymbol}{selectedAd.amount_min_usd} - {selectedAdCurrency.amountSymbol}{selectedAd.amount_max_usd}{" "}
                <ClientMarketplaceCurrencyLabel presentation={selectedAdCurrency} /> - referencia Bs. {selectedAd.rate_bs_per_usd} /{" "}
                <ClientMarketplaceCurrencyLabel presentation={selectedAdCurrency} />
              </Text>
              <Text className="auth-entry__session-meta">{ORDER_DISCLAIMER}</Text>
              <Button mode="filled" stretched onClick={() => {
                setOrderForm({ amount_usd: searchForm.amount_usd });
                setView("create-order");
              }}>
                Continuar con este negocio
              </Button>
            </>
          ) : (
            <Text>Anuncio no disponible.</Text>
          )}
        </div>
      ) : null}
    </>
  );
}
