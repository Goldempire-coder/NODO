import { Button, Text, Title } from "@telegram-apps/telegram-ui";
import { useState } from "react";
import type { BusinessMiniAppModel } from "../../../hooks/useBusinessMiniAppModel";
import { sanitizeDecimalInput } from "../../../lib/numericInput";
import type { AdSummary } from "../../../types/ads";
import { BusinessAdAmount } from "./BusinessAdAmount";
import { BusinessAdCurrencyLabel } from "./BusinessAdCurrencyLabel";
import { adAmountCurrencyPresentation, adAmountPresentation, canDeleteAd, canRepublishAd, displayAdDate, displayRate, humanizeAdStatus, paymentMethodCanReceive, paymentMethodDisplayName, paymentMethodLabel } from "./businessAdViewHelpers";

export function BusinessAdDetailPanel({ ad, model }: { ad: AdSummary; model: BusinessMiniAppModel }) {
  const {
    adEditForm,
    cancelEditingAd,
    closeAdDetail,
    deleteAd,
    deletingAdId,
    isEditingSelectedAd,
    mutateAd,
    pausingAdId,
    paymentMethods,
    reactivatingAdId,
    republishAd,
    republishingAdId,
    savingAdId,
    setAdEditForm,
    startAddingPaymentMethod,
    startEditingAd,
    updateSelectedAd
  } = model;
  const status = ad.effective_status || ad.status;
  const canEdit = status === "active" || status === "paused";
  const republishable = canRepublishAd(ad);
  const canReactivate = status === "paused" && paymentMethodCanReceive(ad, paymentMethods);
  const activePaymentMethods = paymentMethods.filter((method) => method.is_available);
  const selectedEditPaymentMethodIsActive = activePaymentMethods.some((method) => method.id === adEditForm.payment_method_id);
  const editPaymentMethodValue = selectedEditPaymentMethodIsActive ? adEditForm.payment_method_id : "";
  const selectedEditPaymentMethod = activePaymentMethods.find((method) => method.id === editPaymentMethodValue);
  const currencyPresentation = adAmountPresentation(ad, paymentMethods);
  const editCurrencyPresentation = adAmountCurrencyPresentation(
    selectedEditPaymentMethod?.receive_method || ad.payment_method_details?.method_type || ad.payment_method
  );
  const canSaveEdit = Boolean(selectedEditPaymentMethodIsActive && adEditForm.rate_bs_per_usd && adEditForm.amount_min_usd && adEditForm.amount_max_usd);
  const isDeleting = deletingAdId === ad.id;
  const isPausing = pausingAdId === ad.id;
  const isReactivating = reactivatingAdId === ad.id;
  const isRepublishing = republishingAdId === ad.id;
  const isSaving = savingAdId === ad.id;
  const [confirmDelete, setConfirmDelete] = useState(false);

  return (
    <section className="business-ad-detail">
      <div className="business-ad-detail__header">
        <div>
          <Text className="business-card__label">Anuncio abierto</Text>
          <Title level="3" className="business-shell__title"><BusinessAdAmount ad={ad} paymentMethods={paymentMethods} /></Title>
        </div>
        <button className="icon-button" type="button" aria-label="Cerrar detalle" onClick={closeAdDetail}>
          x
        </button>
      </div>

      <div className="business-ad-detail__grid">
        <div>
          <span>Estado</span>
          <strong>{humanizeAdStatus(status)}</strong>
        </div>
        <div>
          <span>Tasa</span>
          <strong>{displayRate(ad)} / <BusinessAdCurrencyLabel presentation={currencyPresentation} /></strong>
        </div>
        <div>
          <span>Metodo</span>
          <strong>{paymentMethodLabel(ad, paymentMethods)}</strong>
        </div>
        <div>
          <span>Creditos</span>
          <strong>{ad.required_credits}</strong>
        </div>
        <div>
          <span>Publicado</span>
          <strong>{displayAdDate(ad.activated_at || ad.created_at)}</strong>
        </div>
        <div>
          <span>Vence</span>
          <strong>{displayAdDate(ad.expires_at)}</strong>
        </div>
      </div>

      {status === "paused" && !paymentMethodCanReceive(ad, paymentMethods) ? (
        <div className="payment-instruction-box">
          <strong>Este anuncio usa un metodo borrado.</strong>
          <Text>Edita el anuncio y selecciona un metodo activo para poder reactivarlo.</Text>
        </div>
      ) : null}

      {republishable ? (
        <div className="business-ad-detail__actions">
          <Button mode="filled" size="s" disabled={isRepublishing} onClick={() => void republishAd(ad)}>
            {isRepublishing ? "Republicando..." : "Republicar"}
          </Button>
        </div>
      ) : isEditingSelectedAd ? (
        <div className="business-ad-edit">
          {activePaymentMethods.length ? (
            <label className="business-field">
              <span>Metodo donde recibes</span>
              <select value={editPaymentMethodValue} onChange={(event) => setAdEditForm((current) => ({ ...current, payment_method_id: event.target.value }))}>
                <option value="">Selecciona un metodo activo</option>
                {activePaymentMethods.map((method) => (
                  <option key={method.id} value={method.id}>
                    {paymentMethodDisplayName(method.receive_method)} - {method.holder_name ? `${method.holder_name} - ${method.masked_account || method.label}` : method.masked_account || method.label}
                  </option>
                ))}
              </select>
            </label>
          ) : (
            <div className="trusted-empty">
              <span className="status-dot status-dot--muted" aria-hidden="true" />
              <Text>Agrega un metodo activo para poder reactivar este anuncio.</Text>
            </div>
          )}
          <Button mode="outline" size="s" onClick={() => startAddingPaymentMethod("my-ads")}>
            Agregar metodo
          </Button>
          <label className="business-field">
            <span>Tasa Bs/<BusinessAdCurrencyLabel presentation={editCurrencyPresentation} /></span>
            <input value={adEditForm.rate_bs_per_usd} onChange={(event) => setAdEditForm((current) => ({ ...current, rate_bs_per_usd: sanitizeDecimalInput(event.target.value, { maxDecimals: 4, maxIntegerDigits: 5 }) }))} inputMode="decimal" pattern="[0-9]*[.]?[0-9]*" autoComplete="off" />
          </label>
          <div className="business-grid">
            <label className="business-field">
              <span>Min <BusinessAdCurrencyLabel presentation={editCurrencyPresentation} /></span>
              <input value={adEditForm.amount_min_usd} onChange={(event) => setAdEditForm((current) => ({ ...current, amount_min_usd: sanitizeDecimalInput(event.target.value, { maxDecimals: 2, maxIntegerDigits: 6 }) }))} inputMode="decimal" pattern="[0-9]*[.]?[0-9]*" autoComplete="off" />
            </label>
            <label className="business-field">
              <span>Max <BusinessAdCurrencyLabel presentation={editCurrencyPresentation} /></span>
              <input value={adEditForm.amount_max_usd} onChange={(event) => setAdEditForm((current) => ({ ...current, amount_max_usd: sanitizeDecimalInput(event.target.value, { maxDecimals: 2, maxIntegerDigits: 6 }) }))} inputMode="decimal" pattern="[0-9]*[.]?[0-9]*" autoComplete="off" />
            </label>
          </div>
          <div className="business-ad-detail__actions">
            <Button mode="filled" size="s" disabled={isSaving || !canSaveEdit} onClick={() => void updateSelectedAd()}>
              {isSaving ? "Guardando..." : "Guardar"}
            </Button>
            <Button mode="outline" size="s" disabled={isSaving} onClick={cancelEditingAd}>Cancelar</Button>
          </div>
        </div>
      ) : (
        <div className="business-ad-detail__actions">
          <Button mode="filled" size="s" disabled={!canEdit} onClick={() => startEditingAd(ad)}>Editar</Button>
          <Button mode="outline" size="s" disabled={isPausing || status !== "active"} onClick={() => void mutateAd(ad.id, "pause")}>
            {isPausing ? "Pausando..." : "Pausar"}
          </Button>
          <Button mode="outline" size="s" disabled={isReactivating || !canReactivate} onClick={() => void mutateAd(ad.id, "reactivate")}>
            {isReactivating ? "Reactivando..." : "Reactivar"}
          </Button>
          <Button
            mode="outline"
            size="s"
            disabled={isDeleting || !canDeleteAd(ad)}
            onClick={() => {
              if (!confirmDelete) {
                setConfirmDelete(true);
                return;
              }
              setConfirmDelete(false);
              void deleteAd(ad);
            }}
          >
            {isDeleting ? "Borrando..." : confirmDelete ? "Confirmar borrar" : "Borrar"}
          </Button>
          {confirmDelete ? <Text className="auth-entry__session-meta">Consume el credito de esta publicacion.</Text> : null}
        </div>
      )}
    </section>
  );
}
