import { Button, Text, Title } from "@telegram-apps/telegram-ui";
import { useEffect, useRef } from "react";
import { humanizePurchaseStatus } from "../../hooks/business-mini-app/helpers";
import type { BusinessMiniAppModel } from "../../hooks/useBusinessMiniAppModel";
import {
  AUTO_REFRESH_CREDIT_HANDOFF_LIMIT,
  AUTO_REFRESH_CREDIT_HANDOFF_MS,
  AUTO_REFRESH_PENDING_CREDIT_PAYMENT_LIMIT,
  AUTO_REFRESH_PENDING_CREDIT_PAYMENT_MS,
  availableCreditsLabel,
  contractCreditPackagesForCurrentEnv,
  creditedCreditsLabel,
  isAutoRefreshableCreditPaymentStatus,
  packageLabel,
  paymentProgressCopy,
  paymentProgressIconClass,
  paymentProgressPanelClass,
  shouldOfferNewCreditPurchase,
} from "./businessCreditPresentation";

export function CreditsDashboardScreen({ model }: { model: BusinessMiniAppModel }) {
  const { busy, creditWallet, creditWalletRefreshState, openBuyCredits, refreshCreditWallet } = model;
  return (
    <div className="business-card">
      <Text className="business-card__label">Creditos</Text>
      <Title level="3" className="business-shell__title">Creditos para publicar</Title>
      {creditWallet ? (
        <div className="credit-state-grid">
          <div>
            <span>Disponibles</span>
            <strong>{creditWallet.available_credits}</strong>
          </div>
          <div>
            <span>Asignados</span>
            <strong>{creditWallet.blocked_credits}</strong>
          </div>
          <div>
            <span>Consumidos</span>
            <strong>{creditWallet.consumed_credits}</strong>
          </div>
          <div>
            <span>Comprados</span>
            <strong>{creditWallet.lifetime_purchased_credits}</strong>
          </div>
        </div>
      ) : <Text>{creditWalletRefreshState === "stale" ? "No pudimos cargar tu saldo. Reintenta." : "Carga tu balance para ver el resumen."}</Text>}
      {creditWalletRefreshState === "stale" ? (
        <div className="business-shell__tabs">
          <Text className="business-card__label" role="status">
            {creditWallet ? "Saldo sin actualizar. Mostramos el ultimo saldo conocido." : "Saldo no disponible. Reintenta en un momento."}
          </Text>
          <button className="mini-action-button" type="button" disabled={busy} onClick={() => void refreshCreditWallet()}>
            Reintentar saldo
          </button>
        </div>
      ) : null}
      <div className="business-shell__tabs">
        <button
          className="mini-action-button mini-action-button--filled mini-action-button--full"
          type="button"
          onClick={() => void openBuyCredits()}
        >
          Comprar
        </button>
      </div>
    </div>
  );
}

export function BuyCreditsScreen({ model }: { model: BusinessMiniAppModel }) {
  const {
    canPrepareCreditHandoffSilently,
    canDismissPendingCreditPurchase,
    continuePendingBaseUsdcPayment,
    creditHandoffError,
    creditHandoffId,
    creditHandoffLaunchReady,
    creditHandoffOpened,
    creditPackage,
    dismissPendingBaseUsdcPayment,
    dismissingPendingCreditPurchase,
    generatingCreditPayment,
    loadingPendingPurchase,
    openMetaMaskCreditHandoff,
    prepareMetaMaskCreditHandoff,
    pendingDismissConfirmationRequested,
    pendingCreditPurchase,
    preparingCreditHandoff,
    requestPendingCreditPurchaseDismiss,
    resetPendingCreditPurchaseDismiss,
    refreshCreditHandoff,
    refreshingCreditHandoff,
    setCreditPackage
  } = model;
  const packages = contractCreditPackagesForCurrentEnv();
  const selected = packageLabel(creditPackage, packages);
  const pendingSelected = packageLabel(pendingCreditPurchase?.package_code, packages);
  const displayedSelection = pendingSelected || selected;
  const handoffAutoRefreshAttemptsRef = useRef(0);

  useEffect(() => {
    handoffAutoRefreshAttemptsRef.current = 0;
  }, [creditHandoffId]);

  useEffect(() => {
    if (
      !creditHandoffId
      || !creditHandoffOpened
      || pendingCreditPurchase
      || refreshingCreditHandoff
      || handoffAutoRefreshAttemptsRef.current >= AUTO_REFRESH_CREDIT_HANDOFF_LIMIT
    ) {
      return undefined;
    }
    const timeoutId = window.setTimeout(() => {
      handoffAutoRefreshAttemptsRef.current += 1;
      void refreshCreditHandoff();
    }, AUTO_REFRESH_CREDIT_HANDOFF_MS);
    return () => window.clearTimeout(timeoutId);
  }, [creditHandoffId, creditHandoffOpened, pendingCreditPurchase, refreshCreditHandoff, refreshingCreditHandoff]);

  useEffect(() => {
    if (
      !canPrepareCreditHandoffSilently
      || !creditPackage
      || creditHandoffId
      || creditHandoffError
      || creditHandoffLaunchReady
      || pendingCreditPurchase
      || preparingCreditHandoff
      || loadingPendingPurchase
    ) {
      return;
    }
    void prepareMetaMaskCreditHandoff({ silent: true });
  }, [
    canPrepareCreditHandoffSilently,
    creditHandoffError,
    creditHandoffId,
    creditHandoffLaunchReady,
    creditPackage,
    loadingPendingPurchase,
    pendingCreditPurchase,
    prepareMetaMaskCreditHandoff,
    preparingCreditHandoff,
  ]);

  return (
    <div className="business-card">
      <Text className="business-card__label">Comprar creditos</Text>
      <Title level="3" className="business-shell__title">
        {pendingCreditPurchase ? "Continua tu pago" : "Elige un paquete"}
      </Title>
      {pendingCreditPurchase ? (
        <div className="business-status-panel" role="status">
          <div>
            <span className="status-dot" aria-hidden="true" />
            <div>
              <strong>Tienes un pago pendiente</strong>
              <Text>
                {pendingSelected?.name || pendingCreditPurchase.package_code}: {pendingCreditPurchase.price_usd} USDC
              </Text>
              <small>Continua en MetaMask o descartalo solo si no enviaste el pago.</small>
            </div>
          </div>
        </div>
      ) : loadingPendingPurchase ? (
        <div className="business-status-panel" role="status">
          <Text>Revisando pagos pendientes...</Text>
        </div>
      ) : null}
      {!pendingCreditPurchase ? (
        <div className="credit-package-grid">
          {packages.map((item) => (
            <button
              className={creditPackage === item.code ? "credit-package-button is-active" : "credit-package-button"}
              key={item.code}
              type="button"
              onClick={() => setCreditPackage(item.code)}
            >
              <strong>{item.name}</strong>
              <span>{item.credits} creditos</span>
              <b>{item.priceUsdc} USDC</b>
              <small>{item.hint}</small>
            </button>
          ))}
        </div>
      ) : null}
      {!pendingCreditPurchase ? (
        <div className="business-status-panel">
          <div>
            <span className="status-dot" aria-hidden="true" />
            <div>
              {selected ? (
                <>
                  <strong>{selected.name}: {selected.credits} creditos por {selected.priceUsdc} USDC</strong>
                  <small>La autorizacion final confirma el monto antes de pagar.</small>
                </>
              ) : (
                <>
                  <strong>Selecciona un paquete</strong>
                  <Text>Elige un paquete para generar el pago.</Text>
                  <small>NODO calcula el monto cuando preparas la compra.</small>
                </>
              )}
            </div>
          </div>
        </div>
      ) : null}
      <div className="business-status-panel" role="region" aria-label="Wallet pagadora: Pago de prueba con MetaMask">
        <div>
          <span className="status-dot" aria-hidden="true" />
          <div>
            <strong>{pendingCreditPurchase ? "Termina este pago en MetaMask." : "Paga con MetaMask."}</strong>
            <Text>NODO no ve ni guarda tu clave privada.</Text>
            <small>{pendingCreditPurchase ? "MetaMask abrira el paso que falta." : "MetaMask mostrara cada paso antes de enviarlo."}</small>
            <small>Esta wallet será la que firma y paga.</small>
          </div>
        </div>
        <button
          className="mini-action-button mini-action-button--filled mini-action-button--full"
          type="button"
          disabled={
            preparingCreditHandoff
            || generatingCreditPayment
            || loadingPendingPurchase
            || dismissingPendingCreditPurchase
            || (!pendingCreditPurchase && !creditPackage)
          }
          onClick={() => void (
            pendingCreditPurchase && pendingDismissConfirmationRequested
              ? dismissPendingBaseUsdcPayment()
              : pendingCreditPurchase
                ? continuePendingBaseUsdcPayment()
                : openMetaMaskCreditHandoff()
          )}
        >
          {preparingCreditHandoff
            ? "Preparando enlace..."
            : dismissingPendingCreditPurchase
              ? "Descartando..."
            : generatingCreditPayment
              ? "Preparando pago..."
            : loadingPendingPurchase
              ? "Revisando pago pendiente..."
            : pendingCreditPurchase && pendingDismissConfirmationRequested
              ? "Confirmar descarte"
            : pendingCreditPurchase
              ? creditHandoffLaunchReady
                ? "Continuar en MetaMask"
                : "Continuar pago"
              : creditHandoffLaunchReady
              ? "Enlace listo - Abrir MetaMask"
            : creditPackage
              ? "Abrir MetaMask"
              : "Elige un paquete"}
        </button>
        {canDismissPendingCreditPurchase ? (
          <>
            {pendingDismissConfirmationRequested ? (
              <Text role="alert">
                Descarta este intento solo si no enviaste el pago en MetaMask. Si lo enviaste, NODO todavia lo verificara.
              </Text>
            ) : null}
            <button
              className="mini-inline-action"
              type="button"
              disabled={dismissingPendingCreditPurchase}
              onClick={() => {
                if (pendingDismissConfirmationRequested) {
                  resetPendingCreditPurchaseDismiss();
                  return;
                }
                requestPendingCreditPurchaseDismiss();
              }}
            >
              {pendingDismissConfirmationRequested ? "Mantener pago pendiente" : "No envie el pago"}
            </button>
          </>
        ) : null}
        {creditHandoffError ? <Text role="alert">{creditHandoffError}</Text> : null}
      </div>
      {creditHandoffId && creditHandoffOpened ? (
        <div className="business-status-panel" role="status">
          <div>
            <span className="status-dot" aria-hidden="true" />
            <div>
              <strong>Intentamos abrir MetaMask</strong>
              <Text>Si MetaMask se abrio, completa las acciones. NODO revisara esta compra automaticamente.</Text>
            </div>
          </div>
        </div>
      ) : null}
      <div className="business-status-panel" role="note">
        <Text>
          {pendingCreditPurchase
            ? "Continua este intento o descartalo solo si no enviaste el pago."
            : displayedSelection
              ? `Pagaras ${displayedSelection.priceUsdc} USDC de prueba.`
              : "Elige un paquete para ver el monto."}
        </Text>
        <Text>Necesitas saldo USDC y gas de prueba.</Text>
        <Text>La wallet mostrara el permiso exacto y el pago antes de enviarlos.</Text>
        <small>NODO revisa el pago automaticamente.</small>
      </div>
    </div>
  );
}

export function CreditPaymentPendingScreen({ model }: { model: BusinessMiniAppModel }) {
  const {
    creditWallet,
    loadCreditDashboard,
    openBuyCredits,
    refreshingCreditPurchase,
    refreshSelectedCreditPurchase,
    selectedCreditPayment,
    selectedCreditPurchase
  } = model;
  const autoRefreshAttemptsRef = useRef(0);
  const packages = contractCreditPackagesForCurrentEnv();
  const selected = selectedCreditPurchase ? packageLabel(selectedCreditPurchase.package_code, packages) : null;
  const canPay = selectedCreditPayment?.capabilities.can_pay === true;
  const purchaseCredited = selectedCreditPurchase?.status === "credited";
  const successCopy = purchaseCredited ? {
    title: "Pago exitoso",
    body: `Se acreditaron ${creditedCreditsLabel(selectedCreditPurchase?.credits_amount)} a tu negocio.`
  } : null;
  const statusCopy = paymentProgressCopy(selectedCreditPurchase?.status, canPay);
  const statusIconClass = paymentProgressIconClass(selectedCreditPurchase?.status, canPay);
  const statusPanelClass = paymentProgressPanelClass(selectedCreditPurchase?.status, canPay);
  const selectedPurchaseId = selectedCreditPurchase?.id ?? null;
  const selectedPurchaseStatus = selectedCreditPurchase?.status ?? null;
  const availableCredits = availableCreditsLabel(creditWallet?.available_credits);
  const offerNewPurchase = shouldOfferNewCreditPurchase(selectedCreditPurchase?.status, canPay);

  useEffect(() => {
    autoRefreshAttemptsRef.current = 0;
  }, [selectedPurchaseId]);

  useEffect(() => {
    if (
      !selectedPurchaseId
      || !isAutoRefreshableCreditPaymentStatus(selectedPurchaseStatus)
      || refreshingCreditPurchase
      || autoRefreshAttemptsRef.current >= AUTO_REFRESH_PENDING_CREDIT_PAYMENT_LIMIT
    ) {
      return undefined;
    }
    const timeoutId = window.setTimeout(() => {
      autoRefreshAttemptsRef.current += 1;
      void refreshSelectedCreditPurchase({ silent: true });
    }, AUTO_REFRESH_PENDING_CREDIT_PAYMENT_MS);
    return () => window.clearTimeout(timeoutId);
  }, [refreshSelectedCreditPurchase, refreshingCreditPurchase, selectedPurchaseId, selectedPurchaseStatus]);

  if (purchaseCredited && selectedCreditPurchase) {
    return (
      <div className="business-card business-card--credit-success">
        <Text className="business-card__label">Compra finalizada</Text>
        <div className="credit-payment-success-hero" role="status">
          <div className="credit-payment-success-burst" aria-hidden="true">
            <span />
            <span />
            <span />
            <span />
            <span />
            <span />
          </div>
          <div>
            <Title level="3" className="business-shell__title">
              Pago <span className="credit-payment-success-title-accent">exitoso</span>
            </Title>
            <Text>Tus creditos ya estan disponibles.</Text>
          </div>
        </div>
        <div className="business-status-panel business-status-panel--payment-success" role="status">
          <div>
            <span className="status-dot status-dot--large" aria-hidden="true" />
            <div>
              <strong>{successCopy?.body}</strong>
              <Text>Ya puedes usar estos creditos para publicar anuncios.</Text>
            </div>
          </div>
        </div>
        <div className="payment-copy-box payment-copy-box--credit-package">
          <div className="payment-copy-box__header">
            <span>Paquete</span>
            <strong>{selected?.name || selectedCreditPurchase.package_code}</strong>
          </div>
          <span className="credit-accredited-pill">{selectedCreditPurchase.credits_amount} creditos acreditados</span>
        </div>
        {availableCredits ? (
          <div className="payment-copy-box payment-copy-box--credit-total">
            <span className="credit-total-icon" aria-hidden="true" />
            <div className="payment-copy-box__header">
              <span>{availableCredits.label}</span>
              <strong>{availableCredits.value}</strong>
            </div>
          </div>
        ) : null}
        <button
          className="mini-action-button mini-action-button--filled mini-action-button--full"
          type="button"
          onClick={() => void loadCreditDashboard()}
        >
          Ver mis creditos
        </button>
      </div>
    );
  }

  return (
    <div className="business-card">
      <Text className="business-card__label">Compra de creditos</Text>
      {selectedCreditPurchase ? (
        <>
          <Title level="3" className="business-shell__title">
            Estado del pago
          </Title>
          <div className={statusPanelClass} role="status">
            <div>
              <span className={statusIconClass} aria-hidden="true" />
              <div>
                <strong>{statusCopy.title}</strong>
                <Text>{statusCopy.body}</Text>
              </div>
            </div>
          </div>
          <div className="payment-copy-box">
            <div className="payment-copy-box__header">
              <span>Paquete</span>
              <strong>{selected?.name || selectedCreditPurchase.package_code}</strong>
            </div>
            <Text>{selectedCreditPurchase.credits_amount} creditos</Text>
            <Text>
              Monto esperado: {selectedCreditPayment?.expected_amount_display || selectedCreditPurchase.price_usd} {selectedCreditPayment?.token_symbol || "USDC"}
            </Text>
          </div>
          {offerNewPurchase ? (
            <div className="business-shell__tabs">
              <button className="mini-action-button mini-action-button--filled" type="button" onClick={() => void openBuyCredits()}>
                Preparar nueva compra
              </button>
            </div>
          ) : null}
        </>
      ) : <Text>No hay compra seleccionada.</Text>}
    </div>
  );
}

export function ReferralProgramScreen({ model }: { model: BusinessMiniAppModel }) {
  const { referralData } = model;
  return (
    <div className="business-card">
      <Text className="business-card__label">Referidos</Text>
      {referralData ? (
        <div className="business-grid">
          <Text>Codigo: {referralData.referral_code}</Text>
          <Text>Estado: {humanizePurchaseStatus(referralData.status)}</Text>
          <Text>Ganados: {referralData.earned_credits}</Text>
          <Text>Restantes: {referralData.remaining_bonus_credits}</Text>
        </div>
      ) : <Text>Carga o genera tu codigo.</Text>}
    </div>
  );
}
