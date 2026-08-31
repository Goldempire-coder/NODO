import { Button, Text, Title } from "@telegram-apps/telegram-ui";
import type { BusinessMiniAppModel } from "../../hooks/useBusinessMiniAppModel";

function sanitizePin(value: string) {
  return value.replace(/\D/g, "").slice(0, 6);
}

export function BusinessPinScreen({ model }: { model: BusinessMiniAppModel }) {
  const { business, busy, goBack, pendingBusinessOrderPinAction, pendingPaymentMethodDeleteId, pendingPaymentMethodSave, pinForm, setPinForm, submitBusinessPinSetup, submitBusinessPinVerify } = model;
  const access = business?.access_link;
  const isConfigured = Boolean(access?.pin_configured);
  const isUnlocked = Boolean(access?.pin_unlocked);
  const isLocked = Boolean(access?.pin_locked_until);
  const isDeletingPaymentMethod = Boolean(pendingPaymentMethodDeleteId);
  const isSavingPaymentMethod = Boolean(pendingPaymentMethodSave);
  const isDecliningOrder = pendingBusinessOrderPinAction?.action === "cannot-attend";
  const isConfirmingPayment = pendingBusinessOrderPinAction?.action === "confirm-payment";
  const canSubmitSetup = pinForm.pin.length >= 4 && pinForm.pin === pinForm.confirm_pin;
  const canSubmitVerify = pinForm.pin.length >= 4;
  const title = isConfirmingPayment
    ? isConfigured
      ? "PIN para confirmar pago"
      : "Crear PIN para confirmar pago"
    : isDecliningOrder
    ? isConfigured
      ? "PIN para cancelar orden"
      : "Crear PIN para cancelar orden"
    : isDeletingPaymentMethod
    ? isConfigured
      ? "PIN para borrar metodo"
      : "Crear PIN para borrar metodo"
    : isSavingPaymentMethod
      ? isConfigured
        ? "PIN para guardar metodo"
        : "Crear PIN para guardar metodo"
    : isConfigured
      ? isUnlocked ? "PIN activo" : "Desbloquear"
      : "Crear PIN";
  const submitLabel = isConfirmingPayment ? "Confirmar pago" : isDecliningOrder ? "Continuar cancelacion" : isDeletingPaymentMethod ? "Borrar metodo" : isSavingPaymentMethod ? "Guardar metodo" : "Entrar";

  return (
    <div className="business-card">
      <Text className="business-card__label">Seguridad</Text>
      <Title level="3" className="business-shell__title">{title}</Title>
      {isLocked ? (
        <Text className="auth-entry__session-meta">Demasiados intentos. Intenta de nuevo mas tarde.</Text>
      ) : null}
      {isConfigured && isUnlocked ? (
        <>
          <Text className="auth-entry__session-meta">Ya puedes volver y completar la accion.</Text>
          <Button mode="filled" stretched disabled={busy} onClick={goBack}>
            Volver
          </Button>
        </>
      ) : !isConfigured ? (
        <>
          <label className="business-field">
            <span>PIN</span>
            <input
              value={pinForm.pin}
              onChange={(event) => setPinForm((current) => ({ ...current, pin: sanitizePin(event.target.value) }))}
              inputMode="numeric"
              pattern="[0-9]*"
              type="password"
              autoComplete="off"
            />
          </label>
          <label className="business-field">
            <span>Confirmar PIN</span>
            <input
              value={pinForm.confirm_pin}
              onChange={(event) => setPinForm((current) => ({ ...current, confirm_pin: sanitizePin(event.target.value) }))}
              inputMode="numeric"
              pattern="[0-9]*"
              type="password"
              autoComplete="off"
            />
          </label>
          <Button mode="filled" stretched disabled={busy || isLocked || !canSubmitSetup} onClick={() => void submitBusinessPinSetup()}>
            {isConfirmingPayment ? "Activar PIN y confirmar" : isDecliningOrder ? "Activar PIN y continuar" : isDeletingPaymentMethod ? "Activar PIN y borrar metodo" : isSavingPaymentMethod ? "Activar PIN y guardar metodo" : "Activar PIN"}
          </Button>
        </>
      ) : (
        <>
          <label className="business-field">
            <span>PIN</span>
            <input
              value={pinForm.pin}
              onChange={(event) => setPinForm((current) => ({ ...current, pin: sanitizePin(event.target.value) }))}
              inputMode="numeric"
              pattern="[0-9]*"
              type="password"
              autoComplete="off"
            />
          </label>
          <Button mode="filled" stretched disabled={busy || isLocked || !canSubmitVerify} onClick={() => void submitBusinessPinVerify()}>
            {submitLabel}
          </Button>
        </>
      )}
    </div>
  );
}
