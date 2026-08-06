import { useCallback, useState } from "react";
import { lockBusinessPin, setupBusinessPin, verifyBusinessPin } from "../../api/businesses";
import type { AuthenticatedRequest } from "../../api/client";
import { getBusinessSurfaceSession } from "../../api/surface";
import type { BusinessMiniAppView } from "../../constants/businessViews";
import type { AdFormState } from "../../types/ads";
import type { BusinessSummary } from "../../types/business";
import { handleBusinessPinError as routeBusinessPinError, requireUnlockedBusinessPin } from "./businessPinGuards";
import { accessStateFromError, businessAccessNoticeFromError, type BusinessAccessState } from "./helpers";
import { useBusinessAvailabilityModel } from "./useBusinessAvailabilityModel";
import { useBusinessCapacityModel } from "./useBusinessCapacityModel";
import { useBusinessPaymentMethodsModel } from "./useBusinessPaymentMethodsModel";

export function useBusinessAccessModel({
  request,
  resumePendingOrderPinAction,
  setBusy,
  setNotice,
  setView
}: {
  request: AuthenticatedRequest;
  resumePendingOrderPinAction: () => Promise<boolean>;
  setBusy: (busy: boolean) => void;
  setNotice: (notice: string) => void;
  setView: (view: BusinessMiniAppView) => void;
}) {
  const [accessState, setAccessState] = useState<BusinessAccessState>("loading");
  const [business, setBusiness] = useState<BusinessSummary | null>(null);
  const [pinForm, setPinForm] = useState({ pin: "", confirm_pin: "", current_pin: "" });
  const [adForm, setAdForm] = useState<AdFormState>({
    payment_method_id: "",
    payment_method: "zelle",
    delivery_method: "pago_movil_ve",
    rate_bs_per_usd: "",
    amount_min_usd: "20.00",
    amount_max_usd: "100.00"
  });

  const requireBusinessPinFor = useCallback((action: string) => {
    return requireUnlockedBusinessPin({ action, business, setNotice, setView });
  }, [business?.access_link, setNotice, setView]);

  const handleBusinessPinError = useCallback((error: unknown, action: string) => {
    return routeBusinessPinError({ action, error, setNotice, setView });
  }, [setNotice, setView]);

  const paymentMethods = useBusinessPaymentMethodsModel({
    business,
    handleBusinessPinError,
    request,
    requireBusinessPinFor,
    setAdForm,
    setNotice,
    setView
  });

  const availability = useBusinessAvailabilityModel({
    business,
    handleBusinessPinError,
    request,
    requireBusinessPinFor,
    setBusiness,
    setNotice
  });

  const capacity = useBusinessCapacityModel({
    business,
    handleBusinessPinError,
    request,
    requireBusinessPinFor,
    setNotice
  });

  const loadBusinessProfile = useCallback(async () => {
    setBusy(true);
    try {
      const session = await getBusinessSurfaceSession<{ business: BusinessSummary | null }>(request);
      const currentBusiness = session.business as BusinessSummary | null;
      setBusiness(currentBusiness);
      await Promise.all([
        paymentMethods.loadPaymentMethods(),
        capacity.refreshBusinessCapacity().catch(() => null)
      ]);
      setAccessState("ready");
      setNotice("");
    } catch (error) {
      setBusiness(null);
      setAccessState(accessStateFromError(error));
      setNotice(businessAccessNoticeFromError(error));
    } finally {
      setBusy(false);
    }
  }, [capacity.refreshBusinessCapacity, paymentMethods.loadPaymentMethods, request, setBusy, setNotice]);

  const refreshBusinessAfterPin = useCallback(async () => {
    const session = await getBusinessSurfaceSession<{ business: BusinessSummary | null }>(request);
    setBusiness(session.business as BusinessSummary | null);
  }, [request]);

  const resumePendingPinAction = useCallback(async (successNotice: string) => {
    const pendingDeleteId = paymentMethods.pendingPaymentMethodDeleteId;
    const pendingSave = paymentMethods.pendingPaymentMethodSave;
    const pendingAvailability = availability.pendingAvailabilityTarget;
    const pendingCapacityAmount = capacity.pendingBusinessCapacityAmount;
    paymentMethods.clearPendingPaymentMethodDelete();
    paymentMethods.clearPendingPaymentMethodSave();
    availability.clearPendingAvailabilityTarget();
    capacity.setPendingBusinessCapacityAmount(null);
    if (pendingDeleteId) {
      try {
        await paymentMethods.deletePaymentMethodUnlocked(pendingDeleteId);
      } catch (error) {
        setNotice(error instanceof Error ? error.message : "PIN activo, pero no pudimos borrar el metodo.");
      }
      return;
    }
    if (pendingSave) {
      await paymentMethods.savePaymentMethodUnlocked(pendingSave);
      return;
    }
    if (pendingAvailability !== null) {
      await availability.setBusinessAvailabilityUnlocked(pendingAvailability);
      return;
    }
    if (pendingCapacityAmount !== null) {
      await capacity.saveBusinessCapacityUnlocked(pendingCapacityAmount);
      return;
    }
    if (await resumePendingOrderPinAction()) {
      return;
    }
    setNotice(successNotice);
  }, [availability, capacity, paymentMethods, resumePendingOrderPinAction, setNotice]);

  const submitBusinessPinSetup = useCallback(async () => {
    const pin = pinForm.pin.trim();
    const confirmPin = pinForm.confirm_pin.trim();
    const currentPin = pinForm.current_pin.trim();
    if (!/^[0-9]{4,6}$/.test(pin)) {
      setNotice("Usa un PIN de 4 a 6 numeros.");
      return;
    }
    if (pin !== confirmPin) {
      setNotice("El PIN no coincide.");
      return;
    }
    setBusy(true);
    try {
      await setupBusinessPin(request, currentPin ? { pin, current_pin: currentPin } : { pin });
      setPinForm({ pin: "", confirm_pin: "", current_pin: "" });
      await refreshBusinessAfterPin();
      await resumePendingPinAction("PIN activo.");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "No pudimos guardar el PIN.");
    } finally {
      setBusy(false);
    }
  }, [pinForm.confirm_pin, pinForm.current_pin, pinForm.pin, refreshBusinessAfterPin, request, resumePendingPinAction, setBusy, setNotice]);

  const submitBusinessPinVerify = useCallback(async () => {
    const pin = pinForm.pin.trim();
    if (!/^[0-9]{4,6}$/.test(pin)) {
      setNotice("Escribe tu PIN.");
      return;
    }
    setBusy(true);
    try {
      await verifyBusinessPin(request, pin);
      setPinForm({ pin: "", confirm_pin: "", current_pin: "" });
      await refreshBusinessAfterPin();
      await resumePendingPinAction("");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "No pudimos validar el PIN.");
    } finally {
      setBusy(false);
    }
  }, [pinForm.pin, refreshBusinessAfterPin, request, resumePendingPinAction, setBusy, setNotice]);

  const lockBusinessPinSession = useCallback(async () => {
    setBusy(true);
    try {
      await lockBusinessPin(request);
      await refreshBusinessAfterPin();
      setNotice("Mini app bloqueada.");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "No pudimos bloquear la mini app.");
    } finally {
      setBusy(false);
    }
  }, [refreshBusinessAfterPin, request, setBusy, setNotice]);

  return {
    accessState,
    business,
    pinForm,
    setPinForm,
    adForm,
    setAdForm,
    ...paymentMethods,
    ...availability,
    ...capacity,
    lockBusinessPinSession,
    loadBusinessProfile,
    submitBusinessPinSetup,
    submitBusinessPinVerify
  };
}
