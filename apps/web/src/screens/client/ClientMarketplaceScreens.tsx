import { Button, Text, Title } from "@telegram-apps/telegram-ui";
import { ORDER_DISCLAIMER } from "../../constants/copy";
import { formatExchangeRoute } from "../../constants/paymentLabels";
import { sanitizeDecimalInput } from "../../lib/numericInput";
import type { AdSummary } from "../../types/ads";
import { displayBusinessName, type RemitterScreensModel } from "./RemitterScreens.types";

function businessReputationSummary(ad: AdSummary): string {
  const rating = ad.business?.reputation?.rating_avg || ad.business?.rating_avg;
  const completedOrders = ad.business?.reputation?.completed_orders_count ?? ad.business?.completed_orders_count ?? 0;
  return `${rating ? `★ ${rating}` : "★ Verificado"} - ${completedOrders} órdenes`;
}

function MarketplaceBusinessList({ model }: { model: RemitterScreensModel }) {
  const { openAdDetail, openingMarketplaceAdId, searchResults } = model;
  return (
    <div className="marketplace-list">
      {searchResults.length === 0 ? (
        <div className="trusted-empty">
          <span className="status-dot status-dot--muted" aria-hidden="true" />
          <Text>Busca un monto para ver negocios verificados por NODO.</Text>
        </div>
      ) : null}
      {searchResults.map((ad) => (
        <button className="marketplace-business" disabled={openingMarketplaceAdId === ad.id} key={ad.id} type="button" onClick={() => void openAdDetail(ad.id)}>
          <span className="business-avatar">{displayBusinessName(ad).slice(0, 2).toUpperCase()}</span>
          <span className="business-main">
            <strong>{displayBusinessName(ad)}</strong>
            <small>{businessReputationSummary(ad)}</small>
            <small>Límites: ${ad.amount_min_usd} - ${ad.amount_max_usd}</small>
          </span>
          <span className="business-rate">
            <strong>{ad.rate_bs_per_usd}</strong>
            <small>Bs / USD</small>
            <em>{openingMarketplaceAdId === ad.id ? "Abriendo..." : "Disponible"}</em>
          </span>
        </button>
      ))}
    </div>
  );
}

export function ClientMarketplaceScreens({ model }: { model: RemitterScreensModel }) {
  const {
    loadActiveMarketplace,
    loadingMarketplace,
    openingMarketplaceAdId,
    searchAds,
    searchForm,
    searchResults,
    searchingMarketplace,
    selectedAd,
    setOrderForm,
    setSearchForm,
    setView,
    view
  } = model;

  return (
    <>
      {view === "marketplace-search" ? (
        <div className="marketplace-home">
          <div className="exchange-card">
            <Text className="exchange-card__eyebrow">Busca negocios verificados</Text>
            <Title level="2" className="exchange-card__title">¿Cuánto quieres cambiar?</Title>
            <div className="amount-input">
              <span>$</span>
              <input aria-label="Monto en USD" value={searchForm.amount_usd} onChange={(event) => setSearchForm((current) => ({ ...current, amount_usd: sanitizeDecimalInput(event.target.value, { maxDecimals: 2, maxIntegerDigits: 6 }) }))} inputMode="decimal" pattern="[0-9]*[.]?[0-9]*" autoComplete="off" />
              <strong>USD</strong>
            </div>
            <Text className="auth-entry__session-meta">Monto mínimo: $20.00</Text>
            <Text className="exchange-card__section-label">Método de pago que usarás</Text>
            <div className="payment-choice">
              <button className={searchForm.payment_method === "zelle" ? "is-active" : ""} type="button" onClick={() => setSearchForm((current) => ({ ...current, payment_method: "zelle" }))}>
                <span className="payment-choice__brand payment-choice__brand--zelle">Zelle</span>
              </button>
              <button className={searchForm.payment_method === "usdt_trc20" ? "is-active" : ""} type="button" onClick={() => setSearchForm((current) => ({ ...current, payment_method: "usdt_trc20" }))}>
                <span className="coin-badge">T</span>
                USDT TRC20
              </button>
            </div>
            <div className="receiver-note">
              <span className="status-dot" aria-hidden="true" />
              <Text>Tu familiar recibe por pago móvil en Venezuela.</Text>
            </div>
            <Button mode="filled" stretched disabled={searchingMarketplace} onClick={() => void searchAds()}>
              {searchingMarketplace ? "Buscando..." : `Ver negocios para $${searchForm.amount_usd || "0.00"}`}
            </Button>
          </div>

          <div className="marketplace-toolbar">
            <Title level="3" className="business-shell__title">Negocios disponibles</Title>
            <div className="sort-pills" aria-label="Ordenar negocios">
              <button className={searchForm.sort === "trust" ? "is-active" : ""} type="button" onClick={() => setSearchForm((current) => ({ ...current, sort: "trust" }))}>Mejor confianza</button>
              <button className={searchForm.sort === "rate" ? "is-active" : ""} type="button" onClick={() => setSearchForm((current) => ({ ...current, sort: "rate" }))}>Mejor tasa</button>
              <button className={searchForm.sort === "speed" ? "is-active" : ""} type="button" onClick={() => setSearchForm((current) => ({ ...current, sort: "speed" }))}>Más rápido</button>
            </div>
          </div>

          <MarketplaceBusinessList model={model} />

          <div className="trust-banner">
            <span className="status-dot" aria-hidden="true" />
            <Text>Negocios verificados por NODO. Compara tasa, limites y disponibilidad antes de elegir.</Text>
          </div>
        </div>
      ) : null}

      {view === "marketplace-list" ? (
        <div className="marketplace-home marketplace-home--list">
          <div className="marketplace-toolbar">
            <div>
              <Text className="exchange-card__eyebrow">Marketplace</Text>
              <Title level="3" className="business-shell__title">Negocios activos</Title>
            </div>
            <div className="sort-pills" aria-label="Ordenar negocios">
              {(["trust", "rate", "speed"] as const).map((sort) => (
                <button key={sort} className={searchForm.sort === sort ? "is-active" : ""} type="button" onClick={() => {
                  setSearchForm((current) => ({ ...current, sort }));
                  void loadActiveMarketplace(sort);
                }}>
                  {loadingMarketplace && searchForm.sort === sort ? "Cargando..." : sort === "trust" ? "Mejor confianza" : sort === "rate" ? "Mejor tasa" : "Más rápido"}
                </button>
              ))}
            </div>
          </div>

          <div className="marketplace-list">
            {searchResults.length === 0 ? (
              <div className="trusted-empty">
                <span className="status-dot status-dot--muted" aria-hidden="true" />
                <Text>No hay negocios activos disponibles en este momento.</Text>
              </div>
            ) : null}
            {searchResults.map((ad) => (
              <button className="marketplace-business" disabled={openingMarketplaceAdId === ad.id} key={ad.id} type="button" onClick={() => void model.openAdDetail(ad.id)}>
                <span className="business-avatar">{displayBusinessName(ad).slice(0, 2).toUpperCase()}</span>
                <span className="business-main">
                  <strong>{displayBusinessName(ad)}</strong>
                  <small>{businessReputationSummary(ad)}</small>
                  <small>Límites: ${ad.amount_min_usd} - ${ad.amount_max_usd}</small>
                </span>
                <span className="business-rate">
                  <strong>{ad.rate_bs_per_usd}</strong>
                  <small>Bs / USD</small>
                  <em>{openingMarketplaceAdId === ad.id ? "Abriendo..." : "Disponible"}</em>
                </span>
              </button>
            ))}
          </div>

          <div className="trust-banner">
            <span className="status-dot" aria-hidden="true" />
            <Text>Todos los negocios activos del marketplace. Usa el inicio cuando quieras filtrar por monto.</Text>
          </div>
        </div>
      ) : null}

      {view === "marketplace-detail" ? (
        <div className="business-card marketplace-detail-card">
          <Text className="business-card__label">Negocio verificado</Text>
          {selectedAd ? (
            <>
              <Title level="3" className="business-shell__title">{displayBusinessName(selectedAd)}</Title>
              <Text>{formatExchangeRoute(selectedAd.payment_method, selectedAd.delivery_method)}</Text>
              <Text>Rango ${selectedAd.amount_min_usd} - ${selectedAd.amount_max_usd} - tasa {selectedAd.rate_bs_per_usd} Bs/USD</Text>
              <Text className="auth-entry__session-meta">Cuenta: {selectedAd.payment_method_details?.account_masked || "masked"}</Text>
              <Text className="auth-entry__session-meta">{ORDER_DISCLAIMER}</Text>
              <Button mode="filled" stretched onClick={() => {
                setOrderForm((current) => ({ ...current, amount_usd: selectedAd.amount_min_usd }));
                setView("create-order");
              }}>
                Crear orden con este negocio
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
