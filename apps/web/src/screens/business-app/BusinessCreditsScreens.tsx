import { Button, Text, Title } from "@telegram-apps/telegram-ui";
import { humanizePurchaseStatus } from "../../hooks/business-mini-app/helpers";
import type { BusinessMiniAppModel } from "../../hooks/useBusinessMiniAppModel";

// Display-only mirror; backend signs the authoritative amount before payment.
const CREDIT_PACKAGES = [
  { code: "starter", name: "Starter", credits: 5, priceUsdc: "10", hint: "Para probar anuncios." },
  { code: "pro", name: "Pro", credits: 15, priceUsdc: "25", hint: "Para operar varios anuncios." },
  { code: "business", name: "Business", credits: 50, priceUsdc: "75", hint: "Mejor costo por credito." },
  { code: "enterprise", name: "Enterprise", credits: 200, priceUsdc: "250", hint: "Alto volumen." }
];

function packageLabel(packageCode: string | null | undefined) {
  return CREDIT_PACKAGES.find((item) => item.code === packageCode) || null;
}

function shortAddress(value: string | null | undefined) {
  if (!value) {
    return "No disponible";
  }
  if (value.length <= 18) {
    return value;
  }
  return `${value.slice(0, 8)}...${value.slice(-6)}`;
}

function authorizationStatusCopy(status: string | undefined, canPay: boolean) {
  if (status === "valid" && canPay) {
    return {
      title: "Autorizacion lista",
      body: "El siguiente paso sera pagar con tu wallet cuando activemos el contrato."
    };
  }
  if (status === "expired") {
    return {
      title: "Autorizacion vencida",
      body: "La autorizacion vencio. Genera una nueva compra."
    };
  }
  return {
    title: "Nueva autorizacion necesaria",
    body: "Esta compra necesita una nueva autorizacion."
  };
}

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
          disabled={busy}
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
    connectWallet,
    connectingWallet,
    connectedWalletAddress,
    connectedWalletAddressMasked,
    continuePendingBaseUsdcPayment,
    creditPackage,
    generatingCreditPayment,
    loadingPendingPurchase,
    openMetaMaskWalletProbe,
    pendingCreditPurchase,
    setCreditPackage,
    startBaseUsdcPayment,
    walletChainId,
    walletError,
    walletIsBase,
    walletProviderStatus
  } = model;
  const selected = packageLabel(creditPackage);
  return (
    <div className="business-card">
      <Text className="business-card__label">Comprar creditos</Text>
      <Title level="3" className="business-shell__title">Elige un paquete</Title>
      {pendingCreditPurchase ? (
        <div className="business-status-panel" role="status">
          <div>
            <span className="status-dot" aria-hidden="true" />
            <div>
              <strong>Tienes un pago pendiente</strong>
              <Text>
                {packageLabel(pendingCreditPurchase.package_code)?.name || pendingCreditPurchase.package_code}: {pendingCreditPurchase.price_usd} USDC
              </Text>
              <small>Continualo para revisar la autorizacion preparada.</small>
            </div>
          </div>
          <button className="mini-action-button" type="button" disabled={loadingPendingPurchase} onClick={() => void continuePendingBaseUsdcPayment()}>
            {loadingPendingPurchase ? "Cargando..." : "Continuar pago pendiente"}
          </button>
        </div>
      ) : loadingPendingPurchase ? (
        <div className="business-status-panel" role="status">
          <Text>Revisando pagos pendientes...</Text>
        </div>
      ) : null}
      <div className="credit-package-grid">
        {CREDIT_PACKAGES.map((item) => (
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
      <div className="business-status-panel" role="region" aria-label="Wallet pagadora">
        <div>
          <span className="status-dot" aria-hidden="true" />
          <div>
            <strong>Conecta la wallet desde donde pagarás.</strong>
            <Text>NODO no ve ni guarda tu clave privada.</Text>
            <small>Esta wallet será la que firma y paga.</small>
          </div>
        </div>
        <button
          className="mini-action-button"
          type="button"
          disabled={connectingWallet || walletProviderStatus === "checking"}
          onClick={() => {
            if (walletProviderStatus === "unavailable") {
              openMetaMaskWalletProbe();
              return;
            }
            void connectWallet();
          }}
        >
          {connectingWallet
            ? "Conectando..."
            : connectedWalletAddress
              ? "Cambiar wallet"
              : walletProviderStatus === "unavailable"
                ? "Abrir MetaMask para probar conexión"
                : "Conectar wallet"}
        </button>
      </div>
      {walletProviderStatus === "checking" ? (
        <Text role="status">
          Buscando una wallet compatible en este navegador.
        </Text>
      ) : null}
      {walletProviderStatus === "unavailable" ? (
        <Text role="alert">
          No detectamos una wallet compatible en este navegador. NODO no puede conectar tu wallet desde aqui; reintenta solo si abriste desde una wallet compatible con Base.
        </Text>
      ) : null}
      {connectedWalletAddress ? (
        <div className="business-status-panel" role="status">
          <div>
            <span className="status-dot" aria-hidden="true" />
            <div>
              <strong>{connectedWalletAddressMasked}</strong>
              <Text>{walletIsBase ? "Red Base conectada." : `Red actual: ${walletChainId ?? "desconocida"}.`}</Text>
              {!walletIsBase ? <small>Cambia tu wallet a Base para preparar el pago.</small> : null}
            </div>
          </div>
        </div>
      ) : null}
      {walletError ? <Text role="alert">{walletError}</Text> : null}
      <div className="business-status-panel" role="note">
        <Text>{selected ? `Pagarás ${selected.priceUsdc} USDC en red Base.` : "Elige un paquete para ver el monto."}</Text>
        <Text>Necesitas USDC y un poco de ETH en Base para gas.</Text>
        <small>No pegues hashes en este flujo.</small>
      </div>
      <button
        className="mini-action-button mini-action-button--filled mini-action-button--full"
        type="button"
        disabled={generatingCreditPayment || !creditPackage || !connectedWalletAddress || !walletIsBase}
        onClick={() => void startBaseUsdcPayment()}
      >
        {generatingCreditPayment ? "Generando..." : creditPackage ? "Preparar autorizacion" : "Elige un paquete"}
      </button>
    </div>
  );
}

export function CreditPaymentPendingScreen({ model }: { model: BusinessMiniAppModel }) {
  const {
    openBuyCredits,
    refreshingCreditPurchase,
    refreshSelectedCreditPurchase,
    selectedCreditPayment,
    selectedCreditPurchase
  } = model;
  const selected = selectedCreditPurchase ? packageLabel(selectedCreditPurchase.package_code) : null;
  const canPay = selectedCreditPayment?.capabilities.can_pay === true;
  const authorizationCopy = authorizationStatusCopy(
    selectedCreditPayment?.authorization_status,
    canPay
  );
  const validUntil = selectedCreditPayment?.authorization_valid_until;
  return (
    <div className="business-card">
      <Text className="business-card__label">Compra contractual USDC</Text>
      {selectedCreditPurchase ? (
        <>
          <Title level="3" className="business-shell__title">
            Autorizacion de pago
          </Title>
          <div className="business-status-panel" role="status">
            <div>
              <span className="status-dot" aria-hidden="true" />
              <div>
                <strong>{authorizationCopy.title}</strong>
                <Text>{authorizationCopy.body}</Text>
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
          <div className="payment-copy-box payment-copy-box--compact">
            <div className="payment-copy-box__header">
              <span>Wallet pagadora</span>
              <strong>{shortAddress(selectedCreditPayment?.payer_wallet_address)}</strong>
            </div>
          </div>
          <div className="business-grid">
            <Text>Estado: {humanizePurchaseStatus(selectedCreditPurchase.status)}</Text>
            <Text>Red: {selectedCreditPayment?.network === "base_mainnet" ? "Base" : selectedCreditPayment?.network || "No disponible"}</Text>
            <Text>Token: {selectedCreditPayment?.token_symbol || "No disponible"}</Text>
            <Text>Contrato: {shortAddress(selectedCreditPayment?.contract_address)}</Text>
            <Text>Version: {selectedCreditPayment?.contract_version ?? "No disponible"}</Text>
            <Text>Autorizacion: {selectedCreditPayment?.authorization_status || "reissue_required"}</Text>
            <Text>Puede pagar: {selectedCreditPayment?.capabilities.can_pay ? "Si" : "No"}</Text>
            {validUntil ? <Text>Vence: {new Date(validUntil * 1000).toLocaleString("es-VE")}</Text> : null}
          </div>
          <div className="business-shell__tabs">
            {!canPay ? (
              <button className="mini-action-button mini-action-button--filled" type="button" onClick={() => void openBuyCredits()}>
                Preparar nueva compra
              </button>
            ) : null}
            <button className="mini-action-button" type="button" disabled={refreshingCreditPurchase} onClick={() => void refreshSelectedCreditPurchase()}>
              {refreshingCreditPurchase ? "Actualizando..." : "Actualizar estado"}
            </button>
          </div>
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
