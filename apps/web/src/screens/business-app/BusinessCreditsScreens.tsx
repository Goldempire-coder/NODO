import { Button, Text } from "@telegram-apps/telegram-ui";
import { CREDITS_COPY } from "../../constants/copy";
import { humanizeLedgerType, humanizePurchaseStatus } from "../../hooks/business-mini-app/helpers";
import type { BusinessMiniAppModel } from "../../hooks/useBusinessMiniAppModel";

export function CreditsDashboardScreen({ model }: { model: BusinessMiniAppModel }) {
  const { busy, creditWallet, loadCreditLedger, loadReferrals, setView } = model;
  return (
    <div className="business-card">
      <Text className="business-card__label">Creditos</Text>
      <Text className="auth-entry__session-meta">{CREDITS_COPY}</Text>
      {creditWallet ? (
        <div className="business-grid">
          <Text>Disponibles: {creditWallet.available_credits}</Text>
          <Text>Bloqueados: {creditWallet.blocked_credits}</Text>
          <Text>Consumidos: {creditWallet.consumed_credits}</Text>
          <Text>Founder: {creditWallet.founder_status || "sin acceso activo"}</Text>
        </div>
      ) : <Text>Carga tu balance para ver el resumen.</Text>}
      <div className="business-shell__tabs">
        <Button size="s" mode="filled" disabled={busy} onClick={() => setView("buy-credits")}>Comprar</Button>
        <Button size="s" mode="outline" disabled={busy} onClick={() => void loadCreditLedger()}>Movimientos</Button>
        <Button size="s" mode="outline" disabled={busy} onClick={() => void loadReferrals()}>Referidos</Button>
      </div>
    </div>
  );
}

export function BuyCreditsScreen({ model }: { model: BusinessMiniAppModel }) {
  const {
    busy,
    creditPackage,
    manualPaymentMethod,
    manualPaymentReference,
    manualTxHash,
    setCreditPackage,
    setManualPaymentMethod,
    setManualPaymentReference,
    setManualTxHash,
    startStripeCheckout,
    submitManualCreditPayment
  } = model;
  return (
    <div className="business-card">
      <Text className="business-card__label">Comprar creditos</Text>
      <Text className="auth-entry__session-meta">Puedes pagar con tarjeta o enviar un comprobante para revision.</Text>
      <div className="business-grid">
        <label className="business-field">
          <span>Paquete</span>
          <select value={creditPackage} onChange={(event) => setCreditPackage(event.target.value)}>
            <option value="starter">Starter - 5 creditos</option>
            <option value="pro">Pro - 15 creditos</option>
            <option value="business">Business - 50 creditos</option>
            <option value="enterprise">Enterprise - 200 creditos</option>
          </select>
        </label>
        <Button mode="filled" disabled={busy} onClick={() => void startStripeCheckout()}>Pagar con tarjeta</Button>
      </div>
      <div className="business-grid">
        <label className="business-field">
          <span>Metodo manual</span>
          <select value={manualPaymentMethod} onChange={(event) => setManualPaymentMethod(event.target.value as "zelle_manual_admin_approved" | "usdt_manual_admin_approved")}>
            <option value="zelle_manual_admin_approved">Zelle manual</option>
            <option value="usdt_manual_admin_approved">USDT TRC20 manual</option>
          </select>
        </label>
        {manualPaymentMethod === "zelle_manual_admin_approved" ? (
          <label className="business-field"><span>Referencia</span><input value={manualPaymentReference} onChange={(event) => setManualPaymentReference(event.target.value)} /></label>
        ) : (
          <label className="business-field"><span>Tx hash</span><input value={manualTxHash} onChange={(event) => setManualTxHash(event.target.value)} /></label>
        )}
      </div>
      <label className="business-upload">
        <span>Comprobante privado</span>
        <input accept="image/jpeg,image/png,image/webp,application/pdf" disabled={busy} type="file" onChange={(event) => void submitManualCreditPayment(event.target.files?.[0] || null)} />
      </label>
    </div>
  );
}

export function CreditPaymentPendingScreen({ model }: { model: BusinessMiniAppModel }) {
  const { selectedCreditPurchase } = model;
  return (
    <div className="business-card">
      <Text className="business-card__label">Pago en revision</Text>
      {selectedCreditPurchase ? (
        <div className="business-grid">
          <Text>Compra: {selectedCreditPurchase.id}</Text>
          <Text>Paquete: {selectedCreditPurchase.package_code}</Text>
          <Text>Creditos: {selectedCreditPurchase.credits_amount}</Text>
          <Text>Estado: {humanizePurchaseStatus(selectedCreditPurchase.status)}</Text>
        </div>
      ) : <Text>No hay compra seleccionada.</Text>}
    </div>
  );
}

export function CreditsLedgerScreen({ model }: { model: BusinessMiniAppModel }) {
  const { creditLedger } = model;
  return (
    <div className="business-card">
      <Text className="business-card__label">Movimientos</Text>
      <div className="business-list">
        {creditLedger.length === 0 ? <Text>Aun no hay movimientos.</Text> : null}
        {creditLedger.map((entry) => (
          <div className="business-row ad-row" key={entry.id}>
            <span>{humanizeLedgerType(entry.type)}</span>
            <span>{entry.amount}</span>
            <span>{entry.balance_available_before} - {entry.balance_available_after}</span>
            <span>{new Date(entry.created_at).toLocaleString()}</span>
          </div>
        ))}
      </div>
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
