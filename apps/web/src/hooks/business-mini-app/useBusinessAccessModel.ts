import { useCallback, useState } from "react";
import { listBusinessPaymentMethods } from "../../api/businesses";
import type { AuthenticatedRequest } from "../../api/client";
import { getBusinessSurfaceSession } from "../../api/surface";
import type { AdFormState } from "../../types/ads";
import type { BusinessPaymentMethod, BusinessSummary } from "../../types/business";
import { accessStateFromError, type BusinessAccessState } from "./helpers";

export function useBusinessAccessModel({ request, setBusy, setNotice }: { request: AuthenticatedRequest; setBusy: (busy: boolean) => void; setNotice: (notice: string) => void }) {
  const [accessState, setAccessState] = useState<BusinessAccessState>("loading");
  const [business, setBusiness] = useState<BusinessSummary | null>(null);
  const [paymentMethods, setPaymentMethods] = useState<BusinessPaymentMethod[]>([]);
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

  const loadPaymentMethods = useCallback(async () => {
    const data = await listBusinessPaymentMethods<BusinessPaymentMethod[]>(request);
    const methods = data as BusinessPaymentMethod[];
    setPaymentMethods(methods);
    setAdForm((current) => {
      if (!methods.length || methods.some((method) => method.id === current.payment_method_id)) {
        return current;
      }
      const first = methods[0];
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

  return {
    accessState,
    business,
    paymentMethods,
    adForm,
    setAdForm,
    loadBusinessProfile,
    loadPaymentMethods,
    selectPaymentMethod
  };
}
