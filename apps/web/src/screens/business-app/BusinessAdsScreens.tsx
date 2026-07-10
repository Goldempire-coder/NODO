import { Button, Text, Title } from "@telegram-apps/telegram-ui";
import { humanizeAdStatus } from "../../hooks/business-mini-app/helpers";
import type { BusinessMiniAppModel } from "../../hooks/useBusinessMiniAppModel";
import { sanitizeDecimalInput } from "../../lib/numericInput";

export function CreateAdScreen({ model }: { model: BusinessMiniAppModel }) {
  const { adForm, busy, createAd, loadPaymentMethods, paymentMethods, selectPaymentMethod, setAdForm } = model;
  const selectedMethod = paymentMethods.find((item) => item.id === adForm.payment_method_id);

  return (
    <div className="business-card">
      <Text className="business-card__label">Nuevo anuncio</Text>
      <Title level="3" className="business-shell__title">Publicar anuncio</Title>
      {paymentMethods.length === 0 ? (
        <div className="trusted-empty">
          <span className="status-dot status-dot--muted" aria-hidden="true" />
          <Text>Aun no tienes metodos aprobados. Contacta a NODO para activarlos.</Text>
          <Button mode="outline" size="s" onClick={() => void loadPaymentMethods()}>
            Recargar metodos
          </Button>
        </div>
      ) : (
        <label className="business-field">
          <span>Metodo aprobado</span>
          <select value={adForm.payment_method_id} onChange={(event) => selectPaymentMethod(event.target.value)}>
            {paymentMethods.map((method) => (
              <option key={method.id} value={method.id}>
                {method.label}
              </option>
            ))}
          </select>
        </label>
      )}
      {selectedMethod ? (
        <div className="business-grid">
          <Text>Recibes: {selectedMethod.receive_display}</Text>
          <Text>Entregas: {selectedMethod.delivery_display} {selectedMethod.delivery_currency}</Text>
          <Text>Limites: {selectedMethod.limits.min_amount_usd} - {selectedMethod.limits.max_amount_usd} USD</Text>
          <Text>Cuenta: {selectedMethod.masked_account || "enmascarada"}</Text>
        </div>
      ) : null}
      <label className="business-field">
        <span>Tasa Bs/USD</span>
        <input value={adForm.rate_bs_per_usd} onChange={(event) => setAdForm((current) => ({ ...current, rate_bs_per_usd: sanitizeDecimalInput(event.target.value, { maxDecimals: 4, maxIntegerDigits: 5 }) }))} inputMode="decimal" pattern="[0-9]*[.]?[0-9]*" autoComplete="off" />
      </label>
      <div className="business-grid">
        <label className="business-field">
          <span>Min USD</span>
          <input value={adForm.amount_min_usd} onChange={(event) => setAdForm((current) => ({ ...current, amount_min_usd: sanitizeDecimalInput(event.target.value, { maxDecimals: 2, maxIntegerDigits: 6 }) }))} inputMode="decimal" pattern="[0-9]*[.]?[0-9]*" autoComplete="off" />
        </label>
        <label className="business-field">
          <span>Max USD</span>
          <input value={adForm.amount_max_usd} onChange={(event) => setAdForm((current) => ({ ...current, amount_max_usd: sanitizeDecimalInput(event.target.value, { maxDecimals: 2, maxIntegerDigits: 6 }) }))} inputMode="decimal" pattern="[0-9]*[.]?[0-9]*" autoComplete="off" />
        </label>
      </div>
      <Button mode="filled" stretched disabled={busy || !adForm.payment_method_id || !adForm.rate_bs_per_usd} onClick={() => void createAd()}>
        Publicar anuncio
      </Button>
    </div>
  );
}

export function MyAdsScreen({ model }: { model: BusinessMiniAppModel }) {
  const { busy, loadArchivedAds, mutateAd, ownAds, setView } = model;
  return (
    <div className="business-card">
      <Text className="business-card__label">Anuncios</Text>
      <div className="business-shell__tabs">
        <Button mode="filled" size="s" onClick={() => setView("create-ad")}>Crear</Button>
        <Button mode="outline" size="s" onClick={() => void loadArchivedAds()}>Archivados</Button>
        <Button mode="outline" size="s" onClick={() => setView("payment-methods")}>Metodos</Button>
      </div>
      <div className="business-list">
        {ownAds.length === 0 ? <Text>Aun no tienes anuncios activos.</Text> : null}
        {ownAds.map((ad) => (
          <div className="business-row ad-row" key={ad.id}>
            <span>{humanizeAdStatus(ad.status)}</span>
            <span>{ad.amount_min_usd}-{ad.amount_max_usd} USD</span>
            <span>{ad.required_credits} creditos</span>
            <Button mode="outline" size="s" disabled={busy || ad.status !== "active"} onClick={() => void mutateAd(ad.id, "pause")}>Pausar</Button>
            <Button mode="outline" size="s" disabled={busy || (ad.status !== "paused" && ad.status !== "expired")} onClick={() => void mutateAd(ad.id, "archive")}>Archivar</Button>
          </div>
        ))}
      </div>
    </div>
  );
}

export function ArchivedAdsScreen({ model }: { model: BusinessMiniAppModel }) {
  const { archivedAds } = model;
  return (
    <div className="business-card">
      <Text className="business-card__label">Archivados</Text>
      <div className="business-list">
        {archivedAds.length === 0 ? <Text>No hay anuncios archivados.</Text> : null}
        {archivedAds.map((ad) => (
          <div className="business-row ad-row" key={ad.id}>
            <span>{humanizeAdStatus(ad.status)}</span>
            <span>{ad.amount_min_usd}-{ad.amount_max_usd} USD</span>
            <span>{ad.expires_at || "sin fecha"}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

export function PaymentMethodsScreen({ model }: { model: BusinessMiniAppModel }) {
  const { paymentMethods } = model;
  return (
    <div className="business-card">
      <Text className="business-card__label">Metodos</Text>
      <Title level="3" className="business-shell__title">Metodos aprobados</Title>
      <Text className="auth-entry__session-meta">NODO activa y revisa los metodos del negocio.</Text>
      <div className="business-list">
        {paymentMethods.length === 0 ? <Text>Aun no tienes metodos aprobados. Contacta a NODO para activarlos.</Text> : null}
        {paymentMethods.map((method) => (
          <div className="business-row ad-row" key={method.id}>
            <span>{method.label}</span>
            <span>{method.masked_account || "enmascarada"}</span>
            <span>{method.limits.min_amount_usd}-{method.limits.max_amount_usd} USD</span>
          </div>
        ))}
      </div>
    </div>
  );
}
