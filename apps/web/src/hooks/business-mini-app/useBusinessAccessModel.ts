import { useCallback, useState } from "react";
import { createBusinessPaymentMethod, deleteBusinessPaymentMethod, listBusinessPaymentMethods, lockBusinessPin, setupBusinessPin, updateBusinessAvailability, updateBusinessPaymentMethod, verifyBusinessPin } from "../../api/businesses";
import { ApiClientError, type AuthenticatedRequest } from "../../api/client";
import { getBusinessSurfaceSession } from "../../api/surface";
import type { BusinessMiniAppView } from "../../constants/businessViews";
import { recordActionBreadcrumb } from "../../observability/clientTelemetry";
import type { AdFormState } from "../../types/ads";
import type { BusinessPaymentMethod, BusinessPaymentMethodFormState, BusinessSummary } from "../../types/business";
import { actionStartedAt, recordBusinessActionCompleted, recordBusinessActionFailed, recordBusinessActionStarted } from "./actionTelemetry";
import { businessPinActionMessage, handleBusinessPinError as routeBusinessPinError, isBusinessPinError, requireUnlockedBusinessPin } from "./businessPinGuards";
import { accessStateFromError, idempotencyKey, type BusinessAccessState } from "./helpers";

function activeBusinessPaymentMethods(methods: BusinessPaymentMethod[]) {
  return methods.filter((method) => method.is_available !== false);
}

function emptyPaymentMethodForm(methodType: BusinessPaymentMethodFormState["method_type"] = "zelle"): BusinessPaymentMethodFormState {
  return { method_type: methodType, account_value: "", holder_name: "" };
}

function paymentMethodDisplay(methodType: BusinessPaymentMethodFormState["method_type"]) {
  return methodType === "usdt_trc20" ? "USDT TRC20" : "Zelle";
}

const PAYMENT_METHOD_TELEMETRY_ACTIONS = {
  zelle_add: "zelle_add",
  zelle_edit: "zelle_edit",
  zelle_delete: "zelle_delete",
  usdt_wallet_add: "usdt_wallet_add",
  usdt_wallet_edit: "usdt_wallet_edit",
  usdt_wallet_delete: "usdt_wallet_delete"
} as const;

function paymentMethodTelemetry(methodType: BusinessPaymentMethodFormState["method_type"], action: "add" | "edit" | "delete") {
  return methodType === "usdt_trc20"
    ? PAYMENT_METHOD_TELEMETRY_ACTIONS[`usdt_wallet_${action}`]
    : PAYMENT_METHOD_TELEMETRY_ACTIONS[`zelle_${action}`];
}

export function useBusinessAccessModel({
  request,
  setBusy,
  setNotice,
  setView
}: {
  request: AuthenticatedRequest;
  setBusy: (busy: boolean) => void;
  setNotice: (notice: string) => void;
  setView: (view: BusinessMiniAppView) => void;
}) {
  const [accessState, setAccessState] = useState<BusinessAccessState>("loading");
  const [business, setBusiness] = useState<BusinessSummary | null>(null);
  const [paymentMethods, setPaymentMethods] = useState<BusinessPaymentMethod[]>([]);
  const [pinForm, setPinForm] = useState({ pin: "", confirm_pin: "", current_pin: "" });
  const [paymentMethodForm, setPaymentMethodForm] = useState<BusinessPaymentMethodFormState>(emptyPaymentMethodForm());
  const [editingPaymentMethodId, setEditingPaymentMethodId] = useState<string | null>(null);
  const [pendingPaymentMethodDeleteId, setPendingPaymentMethodDeleteId] = useState<string | null>(null);
  const [pendingAvailabilityTarget, setPendingAvailabilityTarget] = useState<boolean | null>(null);
  const [deletingPaymentMethodId, setDeletingPaymentMethodId] = useState<string | null>(null);
  const [savingPaymentMethodId, setSavingPaymentMethodId] = useState<string | null>(null);
  const [updatingAvailability, setUpdatingAvailability] = useState(false);
  const [paymentMethodReturnView, setPaymentMethodReturnView] = useState<BusinessMiniAppView | null>(null);
  const [adForm, setAdForm] = useState<AdFormState>({
    payment_method_id: "",
    payment_method: "zelle",
    delivery_method: "pago_movil_ve",
    rate_bs_per_usd: "",
    amount_min_usd: "20.00",
    amount_max_usd: "100.00"
  });

  const selectPaymentMethod = useCallback((methodId: string) => {
    const method = paymentMethods.find((item) => item.id === methodId);
    if (!method) {
      setAdForm((current) => ({ ...current, payment_method_id: "" }));
      return;
    }
    setAdForm((current) => ({
      ...current,
      payment_method_id: method.id,
      payment_method: method.receive_method,
      delivery_method: method.delivery_method,
      amount_min_usd: method.limits.min_amount_usd,
      amount_max_usd: method.limits.max_amount_usd
    }));
  }, [paymentMethods]);

  const selectAdPaymentType = useCallback((methodType: AdFormState["payment_method"]) => {
    const firstMethod = paymentMethods.find((method) => method.receive_method === methodType);
    setAdForm((current) => ({
      ...current,
      payment_method: methodType,
      payment_method_id: firstMethod?.id || "",
      delivery_method: firstMethod?.delivery_method || "pago_movil_ve",
      amount_min_usd: firstMethod?.limits.min_amount_usd || current.amount_min_usd,
      amount_max_usd: firstMethod?.limits.max_amount_usd || current.amount_max_usd
    }));
  }, [paymentMethods]);

  const loadPaymentMethods = useCallback(async () => {
    const data = await listBusinessPaymentMethods<BusinessPaymentMethod[]>(request);
    const methods = activeBusinessPaymentMethods(data as BusinessPaymentMethod[]);
    setPaymentMethods(methods);
    setAdForm((current) => {
      if (!methods.length) {
        return current.payment_method_id ? { ...current, payment_method_id: "" } : current;
      }
      if (methods.some((method) => method.id === current.payment_method_id)) {
        return current;
      }
      const first = methods.find((method) => method.receive_method === current.payment_method) || methods[0];
      return {
        ...current,
        payment_method_id: first.id,
        payment_method: first.receive_method,
        delivery_method: first.delivery_method,
        amount_min_usd: first.limits.min_amount_usd,
        amount_max_usd: first.limits.max_amount_usd
      };
    });
    return methods;
  }, [request]);

  const requireBusinessPinFor = useCallback((action: string) => {
    return requireUnlockedBusinessPin({ action, business, setNotice, setView });
  }, [business?.access_link, setNotice, setView]);

  const handleBusinessPinError = useCallback((error: unknown, action: string) => {
    return routeBusinessPinError({ action, error, setNotice, setView });
  }, [setNotice, setView]);

  const createPaymentMethod = useCallback(async () => {
    const accountValue = paymentMethodForm.account_value.trim();
    const holderName = paymentMethodForm.holder_name.trim();
    const editingMethod = editingPaymentMethodId ? paymentMethods.find((method) => method.id === editingPaymentMethodId) || null : null;
    const methodType = editingMethod?.receive_method || paymentMethodForm.method_type;
    const methodLabel = paymentMethodDisplay(methodType);
    const action = editingPaymentMethodId ? `editar este ${methodLabel}` : `agregar ${methodLabel}`;
    if ((!editingPaymentMethodId && !accountValue) || !holderName) {
      setNotice(`Agrega ${methodLabel} y titular para guardar.`);
      return;
    }
    if (!requireBusinessPinFor(action)) {
      return;
    }
    const telemetryAction = paymentMethodTelemetry(methodType, editingPaymentMethodId ? "edit" : "add");
    setSavingPaymentMethodId(editingPaymentMethodId || "new");
    recordActionBreadcrumb(telemetryAction, { screen: "payment-methods", status: "started" });
    try {
      const data = editingPaymentMethodId
        ? await updateBusinessPaymentMethod<{ payment_method: BusinessPaymentMethod }>(
          request,
          editingPaymentMethodId,
          accountValue ? { account_value: accountValue, holder_name: holderName } : { holder_name: holderName },
          idempotencyKey(`business_payment_method_update_${editingPaymentMethodId}`)
        )
        : await createBusinessPaymentMethod<{ payment_method: BusinessPaymentMethod; created: boolean }>(request, {
          method_type: methodType,
          account_value: accountValue,
          holder_name: holderName
        }, idempotencyKey("business_payment_method_create"));
      const saved = data.payment_method;
      setPaymentMethods((current) => {
        const others = current.filter((method) => method.id !== saved.id);
        return activeBusinessPaymentMethods([saved, ...others]);
      });
      setAdForm((current) => ({
        ...current,
        payment_method_id: saved.id,
        payment_method: saved.receive_method,
        delivery_method: saved.delivery_method,
        amount_min_usd: saved.limits.min_amount_usd,
        amount_max_usd: saved.limits.max_amount_usd
      }));
      setPaymentMethodForm(emptyPaymentMethodForm(methodType));
      setEditingPaymentMethodId(null);
      setNotice(editingPaymentMethodId ? `${methodLabel} actualizado.` : "created" in data && data.created ? `${methodLabel} guardado.` : `Ese ${methodLabel} ya estaba guardado.`);
      if (!editingPaymentMethodId && paymentMethodReturnView) {
        setPaymentMethodReturnView(null);
        setView(paymentMethodReturnView);
      }
      recordActionBreadcrumb(telemetryAction, { screen: "payment-methods", status: "completed" });
    } catch (error) {
      if (handleBusinessPinError(error, action)) {
        recordActionBreadcrumb(telemetryAction, { screen: "payment-methods", status: "failed", errorCode: "BUSINESS_PIN_REQUIRED" });
        return;
      }
      recordActionBreadcrumb(telemetryAction, { screen: "payment-methods", status: "failed", errorCode: error instanceof ApiClientError ? error.code : undefined });
      setNotice(error instanceof Error ? error.message : `No pudimos guardar ${methodLabel}.`);
    } finally {
      setSavingPaymentMethodId(null);
    }
  }, [editingPaymentMethodId, handleBusinessPinError, paymentMethodForm.account_value, paymentMethodForm.holder_name, paymentMethodForm.method_type, paymentMethodReturnView, paymentMethods, request, requireBusinessPinFor, setNotice, setView]);

  const editPaymentMethod = useCallback((method: BusinessPaymentMethod) => {
    setEditingPaymentMethodId(method.id);
    setPaymentMethodForm({
      method_type: method.receive_method,
      account_value: "",
      holder_name: method.holder_name || ""
    });
    setNotice(`Edita el titular. Si quieres cambiar ${paymentMethodDisplay(method.receive_method)}, escribelo de nuevo.`);
  }, [setNotice]);

  const cancelPaymentMethodEdit = useCallback(() => {
    setEditingPaymentMethodId(null);
    setPaymentMethodForm(emptyPaymentMethodForm());
    setNotice("");
  }, [setNotice]);

  const startPaymentMethodCreate = useCallback((methodType: BusinessPaymentMethodFormState["method_type"] = "zelle") => {
    setEditingPaymentMethodId(null);
    setPaymentMethodForm(emptyPaymentMethodForm(methodType));
    setPaymentMethodReturnView(null);
    setNotice(`Agrega ${paymentMethodDisplay(methodType)} y titular.`);
  }, [setNotice]);

  const startAddingPaymentMethod = useCallback((returnView?: BusinessMiniAppView, methodType: BusinessPaymentMethodFormState["method_type"] = "zelle") => {
    setEditingPaymentMethodId(null);
    setPaymentMethodForm(emptyPaymentMethodForm(methodType));
    setPaymentMethodReturnView(returnView || null);
    setNotice(`Agrega ${paymentMethodDisplay(methodType)} y titular.`);
    setView("payment-methods");
  }, [setNotice, setView]);

  const clearDeletedPaymentMethod = useCallback((paymentMethodId: string) => {
    setPaymentMethods((current) => current.filter((method) => method.id !== paymentMethodId));
    setAdForm((current) => current.payment_method_id === paymentMethodId ? { ...current, payment_method_id: "" } : current);
    if (editingPaymentMethodId === paymentMethodId) {
      setEditingPaymentMethodId(null);
      setPaymentMethodForm(emptyPaymentMethodForm());
    }
  }, [editingPaymentMethodId]);

  const queuePaymentMethodDeleteUntilPin = useCallback((paymentMethodId: string, errorCode: string, methodType: BusinessPaymentMethodFormState["method_type"] = "zelle") => {
    setPendingPaymentMethodDeleteId(paymentMethodId);
    setNotice(businessPinActionMessage(errorCode, `borrar este ${paymentMethodDisplay(methodType)}`));
    setView("business-pin");
  }, [setNotice, setView]);

  const deletePaymentMethodUnlocked = useCallback(async (paymentMethodId: string) => {
    await deleteBusinessPaymentMethod<{ deleted: boolean; payment_method_id: string }>(
      request,
      paymentMethodId,
      idempotencyKey(`business_payment_method_delete_${paymentMethodId}`)
    );
    clearDeletedPaymentMethod(paymentMethodId);
    const methods = await loadPaymentMethods();
    if (methods.some((method) => method.id === paymentMethodId)) {
      clearDeletedPaymentMethod(paymentMethodId);
    }
    setNotice("Metodo borrado.");
  }, [clearDeletedPaymentMethod, loadPaymentMethods, request, setNotice]);

  const deletePaymentMethod = useCallback(async (paymentMethodId: string) => {
    const methodType = paymentMethods.find((method) => method.id === paymentMethodId)?.receive_method || "zelle";
    const link = business?.access_link;
    if (link?.pin_required && !link.pin_configured) {
      queuePaymentMethodDeleteUntilPin(paymentMethodId, "BUSINESS_PIN_NOT_SET", methodType);
      return;
    }
    if (link?.pin_required && !link.pin_unlocked) {
      queuePaymentMethodDeleteUntilPin(paymentMethodId, "BUSINESS_PIN_REQUIRED", methodType);
      return;
    }
    setDeletingPaymentMethodId(paymentMethodId);
    const telemetryAction = paymentMethodTelemetry(methodType, "delete");
    recordActionBreadcrumb(telemetryAction, { screen: "payment-methods", status: "started" });
    try {
      await deletePaymentMethodUnlocked(paymentMethodId);
      recordActionBreadcrumb(telemetryAction, { screen: "payment-methods", status: "completed" });
    } catch (error) {
      if (isBusinessPinError(error)) {
        queuePaymentMethodDeleteUntilPin(paymentMethodId, error.code, methodType);
        recordActionBreadcrumb(telemetryAction, { screen: "payment-methods", status: "failed", errorCode: error.code });
        return;
      }
      recordActionBreadcrumb(telemetryAction, { screen: "payment-methods", status: "failed", errorCode: error instanceof ApiClientError ? error.code : undefined });
      setNotice(error instanceof Error ? error.message : "No pudimos borrar el metodo.");
    } finally {
      setDeletingPaymentMethodId(null);
    }
  }, [business?.access_link, deletePaymentMethodUnlocked, paymentMethods, queuePaymentMethodDeleteUntilPin, setNotice]);

  const loadBusinessProfile = useCallback(async () => {
    setBusy(true);
    try {
      const session = await getBusinessSurfaceSession<{ business: BusinessSummary | null }>(request);
      const currentBusiness = session.business as BusinessSummary | null;
      setBusiness(currentBusiness);
      await loadPaymentMethods();
      setAccessState("ready");
      setNotice("");
    } catch (error) {
      setBusiness(null);
      setAccessState(accessStateFromError(error));
      setNotice(error instanceof Error ? error.message : "No pudimos validar el acceso del negocio.");
    } finally {
      setBusy(false);
    }
  }, [loadPaymentMethods, request, setBusy, setNotice]);

  const setBusinessAvailabilityUnlocked = useCallback(async (acceptingOrders: boolean) => {
    setUpdatingAvailability(true);
    const startedAt = actionStartedAt();
    recordBusinessActionStarted("business_availability_update", "business-dashboard");
    try {
      const data = await updateBusinessAvailability<{ business: BusinessSummary }>(
        request,
        acceptingOrders,
        idempotencyKey(`business_availability_${acceptingOrders ? "online" : "offline"}`)
      );
      setBusiness(data.business);
      setNotice(acceptingOrders ? "Negocio online. Tus anuncios activos pueden recibir ordenes." : "Negocio offline. Tus anuncios no apareceran para nuevas ordenes.");
      recordBusinessActionCompleted("business_availability_update", "business-dashboard", startedAt);
    } catch (error) {
      if (handleBusinessPinError(error, acceptingOrders ? "poner el negocio online" : "poner el negocio offline")) {
        setPendingAvailabilityTarget(acceptingOrders);
        recordBusinessActionFailed("business_availability_update", "business-dashboard", startedAt, "BUSINESS_PIN_REQUIRED");
        return;
      }
      recordBusinessActionFailed("business_availability_update", "business-dashboard", startedAt, error instanceof ApiClientError ? error.code : undefined);
      setNotice(error instanceof Error ? error.message : "No pudimos cambiar tu estado online.");
    } finally {
      setUpdatingAvailability(false);
    }
  }, [handleBusinessPinError, request, setNotice]);

  const setBusinessAvailability = useCallback(async (acceptingOrders: boolean) => {
    const action = acceptingOrders ? "poner el negocio online" : "poner el negocio offline";
    if (!requireBusinessPinFor(action)) {
      setPendingAvailabilityTarget(acceptingOrders);
      return;
    }
    await setBusinessAvailabilityUnlocked(acceptingOrders);
  }, [requireBusinessPinFor, setBusinessAvailabilityUnlocked]);

  const refreshBusinessAfterPin = useCallback(async () => {
    const session = await getBusinessSurfaceSession<{ business: BusinessSummary | null }>(request);
    setBusiness(session.business as BusinessSummary | null);
  }, [request]);

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
      const pendingDeleteId = pendingPaymentMethodDeleteId;
      const pendingAvailability = pendingAvailabilityTarget;
      setPendingPaymentMethodDeleteId(null);
      setPendingAvailabilityTarget(null);
      if (pendingDeleteId) {
        try {
          await deletePaymentMethodUnlocked(pendingDeleteId);
        } catch (error) {
          setNotice(error instanceof Error ? error.message : "PIN activo, pero no pudimos borrar el metodo.");
        }
      } else if (pendingAvailability !== null) {
        await setBusinessAvailabilityUnlocked(pendingAvailability);
      } else {
        setNotice("PIN activo.");
      }
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "No pudimos guardar el PIN.");
    } finally {
      setBusy(false);
    }
  }, [deletePaymentMethodUnlocked, pendingAvailabilityTarget, pendingPaymentMethodDeleteId, pinForm.confirm_pin, pinForm.current_pin, pinForm.pin, refreshBusinessAfterPin, request, setBusinessAvailabilityUnlocked, setBusy, setNotice]);

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
      const pendingDeleteId = pendingPaymentMethodDeleteId;
      const pendingAvailability = pendingAvailabilityTarget;
      setPendingPaymentMethodDeleteId(null);
      setPendingAvailabilityTarget(null);
      if (pendingDeleteId) {
        try {
          await deletePaymentMethodUnlocked(pendingDeleteId);
        } catch (error) {
          setNotice(error instanceof Error ? error.message : "PIN verificado, pero no pudimos borrar el metodo.");
        }
      } else if (pendingAvailability !== null) {
        await setBusinessAvailabilityUnlocked(pendingAvailability);
      } else {
        setNotice("");
      }
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "No pudimos validar el PIN.");
    } finally {
      setBusy(false);
    }
  }, [deletePaymentMethodUnlocked, pendingAvailabilityTarget, pendingPaymentMethodDeleteId, pinForm.pin, refreshBusinessAfterPin, request, setBusinessAvailabilityUnlocked, setBusy, setNotice]);

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
    paymentMethods,
    pinForm,
    setPinForm,
    adForm,
    setAdForm,
    paymentMethodForm,
    setPaymentMethodForm,
    editingPaymentMethodId,
    pendingPaymentMethodDeleteId,
    deletingPaymentMethodId,
    savingPaymentMethodId,
    createPaymentMethod,
    editPaymentMethod,
    cancelPaymentMethodEdit,
    startPaymentMethodCreate,
    deletePaymentMethod,
    setBusinessAvailability,
    updatingAvailability,
    lockBusinessPinSession,
    loadBusinessProfile,
    loadPaymentMethods,
    startAddingPaymentMethod,
    submitBusinessPinSetup,
    submitBusinessPinVerify,
    selectAdPaymentType,
    selectPaymentMethod
  };
}
