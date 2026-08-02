import { Button, Text, Title } from "@telegram-apps/telegram-ui";
import { useState } from "react";
import type { BusinessMiniAppModel } from "../../hooks/useBusinessMiniAppModel";
import { sanitizeDecimalInput } from "../../lib/numericInput";
import { BusinessAdCard } from "./ads/BusinessAdCard";
import { BusinessAdDetailPanel } from "./ads/BusinessAdDetailPanel";
import { paymentMethodCanReceive } from "./ads/businessAdViewHelpers";

function paymentMethodName(methodType: "zelle" | "usdt_trc20") {
  return methodType === "usdt_trc20" ? "USDT TRC20" : "Zelle";
}

function adRouteName(methodType: "zelle" | "usdt_trc20") {
  return methodType === "usdt_trc20" ? "USDT -> Bs" : "Zelle -> Bs";
}

export function CreateAdScreen({ model }: { model: BusinessMiniAppModel }) {
  const { adForm, business, createAd, paymentMethods, savingAdId, selectAdPaymentType, selectPaymentMethod, setAdForm, startAddingPaymentMethod } = model;
  const routeMethods = paymentMethods.filter((item) => item.receive_method === adForm.payment_method);
  const selectedMethod = routeMethods.find((item) => item.id === adForm.payment_method_id);
  const previewAmount = adForm.amount_max_usd || adForm.amount_min_usd;
  const previewBs = Number(previewAmount || "0") * Number(adForm.rate_bs_per_usd || "0");
  const isSaving = savingAdId === "new";
  const selectedRouteName = adRouteName(adForm.payment_method);
  const selectedMethodName = paymentMethodName(adForm.payment_method);
  const methodFieldLabel = adForm.payment_method === "usdt_trc20" ? "Wallet USDT TRC20 donde recibes" : "Zelle donde recibes";
  const methodEmptyCopy = adForm.payment_method === "usdt_trc20"
    ? "Agrega una wallet USDT TRC20 para publicar USDT -> Bs."
    : "Agrega un Zelle para publicar Zelle -> Bs.";

  return (
    <div className="business-card">
      <Text className="business-card__label">Nuevo anuncio</Text>
      <Title level="3" className="business-shell__title">Publicar anuncio</Title>
      <Text className="auth-entry__session-meta">Rango autorizado: {business?.min_order_amount_usd || "20.00"} - {business?.max_order_amount_usd || "100.00"} USD</Text>
      <div className="business-shell__tabs business-shell__tabs--two">
        <Button mode={adForm.payment_method === "zelle" ? "filled" : "outline"} size="s" disabled={isSaving} onClick={() => selectAdPaymentType("zelle")}>
          Zelle - Bs
        </Button>
        <Button mode={adForm.payment_method === "usdt_trc20" ? "filled" : "outline"} size="s" disabled={isSaving} onClick={() => selectAdPaymentType("usdt_trc20")}>
          USDT - Bs
        </Button>
      </div>
      {routeMethods.length === 0 ? (
        <div className="trusted-empty">
          <span className="status-dot status-dot--muted" aria-hidden="true" />
          <Text>{methodEmptyCopy}</Text>
          <Button mode="outline" size="s" onClick={() => startAddingPaymentMethod("create-ad", adForm.payment_method)}>
            Agregar {selectedMethodName}
          </Button>
        </div>
      ) : (
        <label className="business-field">
          <span>{methodFieldLabel}</span>
          <select value={adForm.payment_method_id} onChange={(event) => selectPaymentMethod(event.target.value)}>
            {routeMethods.map((method) => (
              <option key={method.id} value={method.id}>
                {paymentMethodName(method.receive_method)} - {method.holder_name ? `${method.holder_name} - ${method.masked_account || method.label}` : method.masked_account || method.label}
              </option>
            ))}
          </select>
        </label>
      )}
      {selectedMethod ? (
        <div className="business-grid">
          <Text>Recibes: {selectedMethod.receive_display}</Text>
          {selectedMethod.network ? <Text>Red: {selectedMethod.network}</Text> : null}
          <Text>Entregas: {selectedMethod.delivery_display} {selectedMethod.delivery_currency}</Text>
          <Text>Limites: {selectedMethod.limits.min_amount_usd} - {selectedMethod.limits.max_amount_usd} USD</Text>
          <Text>{selectedMethod.receive_method === "usdt_trc20" ? "Wallet" : "Zelle"}: {selectedMethod.masked_account || "enmascarado"}</Text>
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
      {selectedMethod && previewAmount && adForm.rate_bs_per_usd ? (
        <div className="payment-instruction-box">
          <span>Resumen {selectedRouteName}</span>
          <strong>Recibiras {previewAmount} USD y entregaras aprox. Bs. {previewBs.toFixed(2)}</strong>
        </div>
      ) : null}
      <Button mode="filled" stretched disabled={isSaving || !adForm.payment_method_id || !adForm.rate_bs_per_usd} onClick={() => void createAd()}>
        {isSaving ? "Guardando..." : "Publicar anuncio"}
      </Button>
    </div>
  );
}

export function MyAdsScreen({ model }: { model: BusinessMiniAppModel }) {
  const { business, deleteAd, deletingAdId, loadArchivedAds, mutateAd, ownAds, pausingAdId, paymentMethods, reactivatingAdId, selectAd, selectedAdId, setView } = model;
  const [confirmDeleteAdId, setConfirmDeleteAdId] = useState<string | null>(null);
  const selectedAd = ownAds.find((ad) => ad.id === selectedAdId) || null;
  const isAcceptingOrders = business?.is_accepting_orders !== false;
  const activeCount = isAcceptingOrders
    ? ownAds.filter((ad) => (ad.effective_status || ad.status) === "active" && paymentMethodCanReceive(ad, paymentMethods)).length
    : 0;
  const occupiedCount = ownAds.filter((ad) => ad.status === "in_order").length;
  const pausedCount = ownAds.filter((ad) => ad.status === "paused").length;
  return (
    <div className="business-card">
      <Text className="business-card__label">Anuncios</Text>
      <Title level="3" className="business-shell__title">Ofertas publicadas</Title>
      <div className="business-priority-list">
        <button type="button" onClick={() => setView("create-ad")}>
          <span>Disponibles</span>
          <strong>{activeCount}</strong>
        </button>
        <button type="button">
          <span>Ocupados</span>
          <strong>{occupiedCount}</strong>
        </button>
        <button type="button">
          <span>Pausados</span>
          <strong>{pausedCount}</strong>
        </button>
      </div>
      <div className="business-shell__tabs">
        <Button mode="filled" size="s" onClick={() => setView("create-ad")}>Crear</Button>
        <Button mode="outline" size="s" onClick={() => void loadArchivedAds()}>Archivados</Button>
        <Button mode="outline" size="s" onClick={() => setView("payment-methods")}>Zelle / USDT</Button>
      </div>
      <div className="business-list business-list--scrollable">
        {selectedAd ? (
          <BusinessAdDetailPanel ad={selectedAd} model={model} />
        ) : (
          <>
            {ownAds.length === 0 ? <Text>Aun no tienes anuncios activos.</Text> : null}
            {ownAds.map((ad) => (
              <BusinessAdCard
                ad={ad}
                isDeleting={deletingAdId === ad.id}
                isDeleteConfirming={confirmDeleteAdId === ad.id}
                isPausing={pausingAdId === ad.id}
                isReactivating={reactivatingAdId === ad.id}
                isSelected={false}
                key={ad.id}
                onDelete={() => {
                  if (confirmDeleteAdId !== ad.id) {
                    setConfirmDeleteAdId(ad.id);
                    return;
                  }
                  setConfirmDeleteAdId(null);
                  void deleteAd(ad);
                }}
                onOpen={() => selectAd(ad)}
                onPause={() => void mutateAd(ad.id, "pause")}
                onReactivate={() => void mutateAd(ad.id, "reactivate")}
                paymentMethods={paymentMethods}
              />
            ))}
          </>
        )}
      </div>
    </div>
  );
}

export function ArchivedAdsScreen({ model }: { model: BusinessMiniAppModel }) {
  const { archivedAds, deletingAdId, pausingAdId, paymentMethods, reactivatingAdId, republishAd, republishingAdId, selectAd, selectedAdId } = model;
  const selectedAd = archivedAds.find((ad) => ad.id === selectedAdId) || null;
  return (
    <div className="business-card">
      <Text className="business-card__label">Archivados</Text>
      <div className="business-list business-list--scrollable">
        {selectedAd ? (
          <BusinessAdDetailPanel ad={selectedAd} model={model} />
        ) : (
          <>
            {archivedAds.length === 0 ? <Text>No hay anuncios archivados.</Text> : null}
            {archivedAds.map((ad) => (
              <BusinessAdCard
                ad={ad}
                isDeleting={deletingAdId === ad.id}
                isPausing={pausingAdId === ad.id}
                isReactivating={reactivatingAdId === ad.id}
                isRepublishing={republishingAdId === ad.id}
                isSelected={false}
                key={ad.id}
                onDelete={() => undefined}
                onOpen={() => selectAd(ad)}
                onPause={() => undefined}
                onReactivate={() => undefined}
                onRepublish={() => void republishAd(ad)}
                paymentMethods={paymentMethods}
              />
            ))}
          </>
        )}
      </div>
    </div>
  );
}

export function PaymentMethodsScreen({ model }: { model: BusinessMiniAppModel }) {
  const {
    cancelPaymentMethodEdit,
    createPaymentMethod,
    deletePaymentMethod,
    deletingPaymentMethodId,
    editingPaymentMethodId,
    editPaymentMethod,
    paymentMethodForm,
    paymentMethods,
    savingPaymentMethodId,
    startPaymentMethodCreate,
    setPaymentMethodForm
  } = model;
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);
  const editingMethod = paymentMethods.find((method) => method.id === editingPaymentMethodId);
  const formMethodName = paymentMethodName(paymentMethodForm.method_type);
  const canSave = Boolean(paymentMethodForm.holder_name.trim() && (editingPaymentMethodId || paymentMethodForm.account_value.trim()));
  const isSavingPaymentMethod = Boolean(savingPaymentMethodId);
  return (
    <div className="business-card">
      <Text className="business-card__label">Zelle / USDT</Text>
      <Title level="3" className="business-shell__title">Zelle y wallets USDT</Title>
      <Text className="auth-entry__session-meta">Organiza tus Zelle y wallets USDT TRC20 antes de comprar creditos o publicar anuncios.</Text>
      <div className="business-shell__tabs business-shell__tabs--two">
        <Button mode={!editingPaymentMethodId && paymentMethodForm.method_type === "zelle" ? "filled" : "outline"} size="s" disabled={isSavingPaymentMethod} onClick={() => startPaymentMethodCreate("zelle")}>
          Zelle
        </Button>
        <Button mode={!editingPaymentMethodId && paymentMethodForm.method_type === "usdt_trc20" ? "filled" : "outline"} size="s" disabled={isSavingPaymentMethod} onClick={() => startPaymentMethodCreate("usdt_trc20")}>
          USDT TRC20
        </Button>
        <span className="zelle-count-pill">
          {paymentMethods.length} guardado{paymentMethods.length === 1 ? "" : "s"}
        </span>
      </div>
      {editingMethod ? (
        <div className="payment-instruction-box">
          <span>Editando</span>
          <strong>{paymentMethodName(editingMethod.receive_method)} - {editingMethod.holder_name || "Titular"} - {editingMethod.masked_account || "guardado"}</strong>
        </div>
      ) : null}
      <div className="business-grid">
        <label className="business-field">
          <span>{formMethodName}</span>
          <input
            value={paymentMethodForm.account_value}
            onChange={(event) => setPaymentMethodForm((current) => ({ ...current, account_value: event.target.value }))}
            autoComplete="off"
            autoCapitalize="none"
            autoCorrect="off"
            inputMode="text"
            spellCheck={false}
            placeholder={editingMethod ? `${paymentMethodName(editingMethod.receive_method)} nuevo opcional` : formMethodName}
          />
        </label>
        <label className="business-field">
          <span>Titular</span>
          <input
            value={paymentMethodForm.holder_name}
            onChange={(event) => setPaymentMethodForm((current) => ({ ...current, holder_name: event.target.value }))}
            autoComplete="name"
          />
        </label>
      </div>
      {editingMethod ? (
        <Text className="auth-entry__session-meta">Si dejas Zelle o wallet vacio, se conserva el actual. Escribe uno nuevo para reemplazarlo.</Text>
      ) : null}
      <Button mode="filled" stretched disabled={isSavingPaymentMethod || !canSave} onClick={() => void createPaymentMethod()}>
        {isSavingPaymentMethod ? "Guardando..." : editingPaymentMethodId ? "Guardar cambios" : `Agregar ${formMethodName}`}
      </Button>
      {editingPaymentMethodId ? (
        <Button mode="outline" stretched disabled={isSavingPaymentMethod} onClick={cancelPaymentMethodEdit}>
          Cancelar
        </Button>
      ) : null}
      <Text className="business-card__label">Tus Zelle / USDT</Text>
      <div className="business-list business-list--scrollable">
        {paymentMethods.length === 0 ? <Text>Aun no tienes Zelle ni wallets USDT guardadas.</Text> : null}
        {paymentMethods.map((method) => (
          <div className="business-row zelle-row" key={method.id}>
            <div>
              <strong>{paymentMethodName(method.receive_method)} - {method.holder_name || "Titular"}</strong>
              <span>{method.network ? `${method.network} - ` : ""}{method.masked_account || "guardado"}</span>
            </div>
            <div className="zelle-row__actions">
              <button
                className="mini-action-button"
                type="button"
                disabled={savingPaymentMethodId === method.id || deletingPaymentMethodId === method.id}
                onClick={() => {
                  setConfirmDeleteId(null);
                  editPaymentMethod(method);
                }}
              >
                Editar
              </button>
              <button
                className={`mini-action-button mini-action-button--danger${confirmDeleteId === method.id ? " mini-action-button--confirm-danger" : ""}`}
                type="button"
                disabled={deletingPaymentMethodId === method.id}
                onClick={() => {
                  if (confirmDeleteId !== method.id) {
                    setConfirmDeleteId(method.id);
                    return;
                  }
                  setConfirmDeleteId(null);
                  void deletePaymentMethod(method.id);
                }}
              >
                {deletingPaymentMethodId === method.id ? "Borrando..." : confirmDeleteId === method.id ? "Confirmar borrar" : "Borrar"}
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
