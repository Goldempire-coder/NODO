import { useCallback, useState } from "react";
import type { Dispatch, SetStateAction } from "react";
import { createBusinessPaymentMethod, deleteBusinessPaymentMethod, listBusinessPaymentMethods, updateBusinessPaymentMethod } from "../../api/businesses";
import { ApiClientError, type AuthenticatedRequest } from "../../api/client";
import type { BusinessMiniAppView } from "../../constants/businessViews";
import { recordActionBreadcrumb } from "../../observability/clientTelemetry";
import type { AdFormState } from "../../types/ads";
import type { BusinessPaymentMethod, BusinessPaymentMethodFormState, BusinessSummary } from "../../types/business";
import { useStableIdempotencyKeys } from "../useStableIdempotencyKeys";
import { businessPinActionMessage, isBusinessPinError } from "./businessPinGuards";
import { activeBusinessPaymentMethods, emptyPaymentMethodForm, paymentMethodDisplay, paymentMethodTelemetry } from "./businessPaymentMethodHelpers";

type PaymentMethodSaveInput = {
  accountValue: string;
  editingPaymentMethodId: string | null;
  holderName: string;
  methodType: BusinessPaymentMethodFormState["method_type"];
  returnView: BusinessMiniAppView | null;
};

export function useBusinessPaymentMethodsModel({
  business,
  handleBusinessPinError,
  request,
  requireBusinessPinFor,
  setAdForm,
  setNotice,
  setView
}: {
  business: BusinessSummary | null;
  handleBusinessPinError: (error: unknown, action: string) => boolean;
  request: AuthenticatedRequest;
  requireBusinessPinFor: (action: string) => boolean;
  setAdForm: Dispatch<SetStateAction<AdFormState>>;
  setNotice: (notice: string) => void;
  setView: (view: BusinessMiniAppView) => void;
}) {
  const [paymentMethods, setPaymentMethods] = useState<BusinessPaymentMethod[]>([]);
  const [paymentMethodForm, setPaymentMethodForm] = useState<BusinessPaymentMethodFormState>(emptyPaymentMethodForm());
  const [editingPaymentMethodId, setEditingPaymentMethodId] = useState<string | null>(null);
  const [pendingPaymentMethodDeleteId, setPendingPaymentMethodDeleteId] = useState<string | null>(null);
  const [pendingPaymentMethodSave, setPendingPaymentMethodSave] = useState<PaymentMethodSaveInput | null>(null);
  const [deletingPaymentMethodId, setDeletingPaymentMethodId] = useState<string | null>(null);
  const [savingPaymentMethodId, setSavingPaymentMethodId] = useState<string | null>(null);
  const [paymentMethodReturnView, setPaymentMethodReturnView] = useState<BusinessMiniAppView | null>(null);
  const { clearIdempotencyKey, getIdempotencyKey } = useStableIdempotencyKeys();

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
  }, [paymentMethods, setAdForm]);

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
  }, [paymentMethods, setAdForm]);

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
  }, [request, setAdForm]);

  const clearPendingPaymentMethodSave = useCallback(() => {
    setPendingPaymentMethodSave(null);
  }, []);

  const savePaymentMethodUnlocked = useCallback(async (saveInput: PaymentMethodSaveInput) => {
    const { accountValue, editingPaymentMethodId: paymentMethodId, holderName, methodType, returnView } = saveInput;
    const methodLabel = paymentMethodDisplay(methodType);
    const action = paymentMethodId ? `editar este ${methodLabel}` : `agregar ${methodLabel}`;
    const telemetryAction = paymentMethodTelemetry(methodType, paymentMethodId ? "edit" : "add");
    setSavingPaymentMethodId(paymentMethodId || "new");
    recordActionBreadcrumb(telemetryAction, { screen: "payment-methods", status: "started" });
    const idempotencyScope = paymentMethodId
      ? `business_payment_method_update_${paymentMethodId}`
      : `business_payment_method_create_${methodType}`;
    try {
      const data = paymentMethodId
        ? await updateBusinessPaymentMethod<{ payment_method: BusinessPaymentMethod }>(
          request,
          paymentMethodId,
          accountValue ? { account_value: accountValue, holder_name: holderName } : { holder_name: holderName },
          getIdempotencyKey(idempotencyScope, { paymentMethodId, accountValue, holderName })
        )
        : await createBusinessPaymentMethod<{ payment_method: BusinessPaymentMethod; created: boolean }>(request, {
          method_type: methodType,
          account_value: accountValue,
          holder_name: holderName
        }, getIdempotencyKey(idempotencyScope, { methodType, accountValue, holderName }));
      clearIdempotencyKey(idempotencyScope);
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
      setPendingPaymentMethodSave(null);
      setPaymentMethodReturnView(null);
      setNotice(paymentMethodId ? `${methodLabel} actualizado.` : "created" in data && data.created ? `${methodLabel} guardado.` : `Ese ${methodLabel} ya estaba guardado.`);
      setView(returnView || "payment-methods");
      recordActionBreadcrumb(telemetryAction, { screen: "payment-methods", status: "completed" });
      return true;
    } catch (error) {
      recordActionBreadcrumb(telemetryAction, { screen: "payment-methods", status: "failed", errorCode: error instanceof ApiClientError ? error.code : undefined });
      if (handleBusinessPinError(error, action)) {
        setPendingPaymentMethodSave(saveInput);
        return false;
      }
      setNotice(error instanceof Error ? error.message : `No pudimos guardar ${methodLabel}.`);
      return false;
    } finally {
      setSavingPaymentMethodId(null);
    }
  }, [clearIdempotencyKey, getIdempotencyKey, handleBusinessPinError, request, setAdForm, setNotice, setView]);

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
    const saveInput: PaymentMethodSaveInput = {
      accountValue,
      editingPaymentMethodId,
      holderName,
      methodType,
      returnView: paymentMethodReturnView
    };
    if (!requireBusinessPinFor(action)) {
      setPendingPaymentMethodSave(saveInput);
      return;
    }
    setPendingPaymentMethodSave(null);
    await savePaymentMethodUnlocked(saveInput);
  }, [editingPaymentMethodId, paymentMethodForm.account_value, paymentMethodForm.holder_name, paymentMethodForm.method_type, paymentMethodReturnView, paymentMethods, requireBusinessPinFor, savePaymentMethodUnlocked, setNotice]);

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
  }, [editingPaymentMethodId, setAdForm]);

  const queuePaymentMethodDeleteUntilPin = useCallback((paymentMethodId: string, errorCode: string, methodType: BusinessPaymentMethodFormState["method_type"] = "zelle") => {
    setPendingPaymentMethodDeleteId(paymentMethodId);
    setNotice(businessPinActionMessage(errorCode, `borrar este ${paymentMethodDisplay(methodType)}`));
    setView("business-pin");
  }, [setNotice, setView]);

  const clearPendingPaymentMethodDelete = useCallback(() => {
    setPendingPaymentMethodDeleteId(null);
  }, []);

  const deletePaymentMethodUnlocked = useCallback(async (paymentMethodId: string) => {
    const idempotencyScope = `business_payment_method_delete_${paymentMethodId}`;
    await deleteBusinessPaymentMethod<{ deleted: boolean; payment_method_id: string }>(
      request,
      paymentMethodId,
      getIdempotencyKey(idempotencyScope, { paymentMethodId })
    );
    clearIdempotencyKey(idempotencyScope);
    clearDeletedPaymentMethod(paymentMethodId);
    const methods = await loadPaymentMethods();
    if (methods.some((method) => method.id === paymentMethodId)) {
      clearDeletedPaymentMethod(paymentMethodId);
    }
    setNotice("Metodo borrado.");
  }, [clearDeletedPaymentMethod, clearIdempotencyKey, getIdempotencyKey, loadPaymentMethods, request, setNotice]);

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

  return {
    cancelPaymentMethodEdit,
    clearPendingPaymentMethodDelete,
    clearPendingPaymentMethodSave,
    createPaymentMethod,
    deletePaymentMethod,
    deletePaymentMethodUnlocked,
    deletingPaymentMethodId,
    editPaymentMethod,
    editingPaymentMethodId,
    loadPaymentMethods,
    paymentMethodForm,
    paymentMethods,
    pendingPaymentMethodDeleteId,
    pendingPaymentMethodSave,
    savePaymentMethodUnlocked,
    savingPaymentMethodId,
    selectAdPaymentType,
    selectPaymentMethod,
    setPaymentMethodForm,
    startAddingPaymentMethod,
    startPaymentMethodCreate
  };
}
