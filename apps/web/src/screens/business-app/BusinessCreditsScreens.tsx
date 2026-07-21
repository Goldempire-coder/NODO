import { Button, Text, Title } from "@telegram-apps/telegram-ui";
import { useEffect, useState } from "react";
import { humanizePurchaseStatus } from "../../hooks/business-mini-app/helpers";
import type { BusinessMiniAppModel } from "../../hooks/useBusinessMiniAppModel";

const CREDIT_PACKAGES = [
  { code: "starter", name: "Starter", credits: 5, price: "10.00", hint: "Para probar anuncios." },
  { code: "pro", name: "Pro", credits: 15, price: "25.00", hint: "Para operar varios anuncios." },
  { code: "business", name: "Business", credits: 50, price: "75.00", hint: "Mejor costo por credito." },
  { code: "enterprise", name: "Enterprise", credits: 200, price: "250.00", hint: "Alto volumen." }
];

function packageLabel(packageCode: string | null | undefined) {
  return CREDIT_PACKAGES.find((item) => item.code === packageCode) || null;
}

function shortWallet(value: string | null | undefined) {
  if (!value) {
    return "No disponible";
  }
  if (value.length <= 18) {
    return value;
  }
  return `${value.slice(0, 8)}...${value.slice(-6)}`;
}

async function copyText(value: string) {
  if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(value);
    return;
  }

  const textarea = document.createElement("textarea");
  textarea.value = value;
  textarea.setAttribute("readonly", "true");
  textarea.style.position = "fixed";
  textarea.style.left = "-9999px";
  document.body.appendChild(textarea);
  textarea.select();
  document.execCommand("copy");
  document.body.removeChild(textarea);
}

export function CreditsDashboardScreen({ model }: { model: BusinessMiniAppModel }) {
  const { busy, creditWallet, openBuyCredits } = model;
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
      ) : <Text>Carga tu balance para ver el resumen.</Text>}
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
    continuePendingBaseUsdcPayment,
    creditPackage,
    generatingCreditPayment,
    loadingPendingPurchase,
    pendingCreditPurchase,
    setCreditPackage,
    startBaseUsdcPayment
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
              <small>Continualo solo si ya enviaste o vas a enviar ese pago.</small>
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
            <b>{item.price} USDC</b>
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
                <strong>{selected.name}: {selected.price} USDC</strong>
                <Text>{selected.credits} creditos</Text>
                <small>Pago en USDC sobre red Base.</small>
              </>
            ) : (
              <>
                <strong>Selecciona un paquete</strong>
                <Text>Elige un paquete para generar el pago.</Text>
                <small>NODO acreditara automaticamente cuando la tx confirme en Base.</small>
              </>
            )}
          </div>
        </div>
      </div>
      <button
        className="mini-action-button mini-action-button--filled mini-action-button--full"
        type="button"
        disabled={generatingCreditPayment || !creditPackage}
        onClick={() => void startBaseUsdcPayment()}
      >
        {generatingCreditPayment ? "Generando..." : creditPackage ? "Generar datos de pago" : "Elige un paquete"}
      </button>
    </div>
  );
}

export function CreditPaymentPendingScreen({ model }: { model: BusinessMiniAppModel }) {
  const { baseUsdcTxHash, refreshingCreditPurchase, refreshSelectedCreditPurchase, selectedCreditPurchase, setBaseUsdcTxHash, setNotice, submitBaseUsdcTxHash, verifyingCreditTx } = model;
  const [copiedTarget, setCopiedTarget] = useState<"wallet" | "amount" | null>(null);
  const selected = selectedCreditPurchase ? packageLabel(selectedCreditPurchase.package_code) : null;
  const walletAddress = selectedCreditPurchase?.destination_wallet_address || "";
  const amount = selectedCreditPurchase?.price_usd || "";
  const walletButtonLabel = copiedTarget === "wallet" ? "Copiado" : "Copiar wallet";
  const amountButtonLabel = copiedTarget === "amount" ? "Copiado" : "Copiar monto";

  useEffect(() => {
    if (!copiedTarget) {
      return undefined;
    }
    const timeoutId = window.setTimeout(() => setCopiedTarget(null), 1800);
    return () => window.clearTimeout(timeoutId);
  }, [copiedTarget]);

  const copyWalletAddress = async () => {
    if (!walletAddress) {
      setNotice("Wallet destino no disponible.");
      return;
    }
    try {
      await copyText(walletAddress);
      setCopiedTarget("wallet");
      setNotice("Wallet copiada.");
    } catch {
      setNotice("No pudimos copiar la wallet. Manten presionada la direccion para copiarla.");
    }
  };
  const copyAmount = async () => {
    if (!amount) {
      setNotice("Monto no disponible.");
      return;
    }
    try {
      await copyText(amount);
      setCopiedTarget("amount");
      setNotice("Monto copiado.");
    } catch {
      setNotice("No pudimos copiar el monto. Manten presionado el monto para copiarlo.");
    }
  };
  return (
    <div className="business-card">
      <Text className="business-card__label">Pago Base USDC</Text>
      {selectedCreditPurchase ? (
        <>
          <Title level="3" className="business-shell__title">
            Envia {selectedCreditPurchase.price_usd} USDC
          </Title>
          <div className="business-status-panel">
            <div>
              <span className="status-dot" aria-hidden="true" />
              <div>
                <strong>{selected?.name || selectedCreditPurchase.package_code}: {selectedCreditPurchase.credits_amount} creditos</strong>
                <Text>Monto exacto: {selectedCreditPurchase.price_usd} USDC</Text>
                <small>NODO acredita automaticamente cuando la tx confirma en Base.</small>
              </div>
            </div>
          </div>
          <div className="payment-step-grid" aria-label="Pasos para pagar">
            <div>
              <strong>1</strong>
              <span>Red Base</span>
            </div>
            <div>
              <strong>2</strong>
              <span>Monto exacto</span>
            </div>
            <div>
              <strong>3</strong>
              <span>Pegar tx hash</span>
            </div>
          </div>
          <div className={copiedTarget === "wallet" ? "payment-copy-box is-copied" : "payment-copy-box"}>
            <div className="payment-copy-box__header">
              <span>Wallet destino</span>
              <strong>{shortWallet(selectedCreditPurchase.destination_wallet_address)}</strong>
            </div>
            <code className="payment-copy-box__value">{selectedCreditPurchase.destination_wallet_address || "Wallet no disponible"}</code>
            <button
              className={copiedTarget === "wallet" ? "mini-action-button mini-action-button--filled mini-action-button--full mini-action-button--copied" : "mini-action-button mini-action-button--filled mini-action-button--full"}
              type="button"
              disabled={!walletAddress}
              onClick={() => void copyWalletAddress()}
            >
              {walletButtonLabel}
            </button>
            {copiedTarget === "wallet" ? <span className="payment-copy-box__feedback" role="status">Wallet copiada.</span> : null}
          </div>
          <div className={copiedTarget === "amount" ? "payment-copy-box payment-copy-box--compact is-copied" : "payment-copy-box payment-copy-box--compact"}>
            <div className="payment-copy-box__header">
              <span>Monto exacto</span>
              <strong>{selectedCreditPurchase.price_usd} USDC</strong>
            </div>
            <button className={copiedTarget === "amount" ? "mini-action-button mini-action-button--copied" : "mini-action-button"} type="button" disabled={!amount} onClick={() => void copyAmount()}>
              {amountButtonLabel}
            </button>
          </div>
          <div className="business-grid">
            <Text>Estado: {humanizePurchaseStatus(selectedCreditPurchase.status)}</Text>
            <Text>Confirmaciones: {selectedCreditPurchase.confirmations ?? 0}</Text>
            {selectedCreditPurchase.expires_at ? <Text>Vence: {new Date(selectedCreditPurchase.expires_at).toLocaleString("es-VE")}</Text> : null}
          </div>
          <label className="business-field">
            <span>Tx hash despues de pagar</span>
            <input value={baseUsdcTxHash} onChange={(event) => setBaseUsdcTxHash(event.target.value.trim())} placeholder="0x..." />
          </label>
          <div className="business-shell__tabs">
            <button
              className="mini-action-button mini-action-button--filled"
              type="button"
              disabled={verifyingCreditTx || !baseUsdcTxHash.trim()}
              onClick={() => void submitBaseUsdcTxHash()}
            >
              {verifyingCreditTx ? "Verificando..." : "Verificar tx"}
            </button>
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
  const { applyReferral, busy, referralCodeInput, referralData, setReferralCodeInput } = model;
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
      <div className="business-grid">
        <label className="business-field"><span>Aplicar codigo</span><input value={referralCodeInput} onChange={(event) => setReferralCodeInput(event.target.value.toUpperCase())} /></label>
        <Button mode="outline" disabled={busy || !referralCodeInput.trim()} onClick={() => void applyReferral()}>Aplicar</Button>
      </div>
    </div>
  );
}
