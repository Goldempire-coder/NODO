import { useCallback, useState } from "react";
import type { Dispatch, SetStateAction } from "react";
import { createBusinessAd, listArchivedBusinessAds, listBusinessAds, mutateBusinessAd } from "../../api/businessAds";
import type { AuthenticatedRequest } from "../../api/client";
import type { BusinessMiniAppView } from "../../constants/businessViews";
import type { AdFormState, AdSummary } from "../../types/ads";
import type { BusinessSummary } from "../../types/business";
import { idempotencyKey } from "./helpers";

export function useBusinessAdsModel({
  adForm,
  business,
  request,
  setAdForm,
  setBusy,
  setNotice,
  setView
}: {
  adForm: AdFormState;
  business: BusinessSummary | null;
  request: AuthenticatedRequest;
  setAdForm: Dispatch<SetStateAction<AdFormState>>;
  setBusy: (busy: boolean) => void;
  setNotice: (notice: string) => void;
  setView: (view: BusinessMiniAppView) => void;
}) {
  const [ownAds, setOwnAds] = useState<AdSummary[]>([]);
  const [archivedAds, setArchivedAds] = useState<AdSummary[]>([]);

  const loadMyAds = useCallback(async () => {
    setBusy(true);
    try {
      const data = await listBusinessAds<{ items: AdSummary[] }>(request);
      setOwnAds(data.items);
      setView("my-ads");
      setNotice(data.items.length ? "Anuncios cargados." : "Aun no tienes anuncios activos o pausados.");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "No pudimos cargar tus anuncios.");
    } finally {
      setBusy(false);
    }
  }, [request, setBusy, setNotice, setView]);

  const loadArchivedAds = useCallback(async () => {
    setBusy(true);
    try {
      const data = await listArchivedBusinessAds<{ items: AdSummary[] }>(request);
      setArchivedAds(data.items);
      setView("archived-ads");
      setNotice(data.items.length ? "Historial de anuncios cargado." : "Aun no hay anuncios archivados.");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "No pudimos cargar el historial.");
    } finally {
      setBusy(false);
    }
  }, [request, setBusy, setNotice, setView]);

  const createAd = useCallback(async () => {
    if (!business) {
      setNotice("Necesitas un negocio aprobado para publicar.");
      return;
    }
    if (!adForm.payment_method_id) {
      setNotice("Aun no tienes metodos aprobados. Contacta a NODO para activar tus metodos de operacion.");
      return;
    }
    setBusy(true);
    try {
      const data = await createBusinessAd<{ ad: AdSummary }>(request, { ...adForm, business_id: business.id }, idempotencyKey(`ad_create_${business.id}`));
      setNotice(`Anuncio activo por ${data.ad.required_credits} credito(s).`);
      setAdForm((current) => ({ ...current, rate_bs_per_usd: "" }));
      await loadMyAds();
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "No pudimos publicar el anuncio.");
    } finally {
      setBusy(false);
    }
  }, [adForm, business, loadMyAds, request, setAdForm, setBusy, setNotice]);

  const mutateAd = useCallback(async (adId: string, action: "pause" | "archive") => {
    setBusy(true);
    try {
      await mutateBusinessAd(request, adId, action, idempotencyKey(`ad_${action}_${adId}`));
      setNotice(action === "pause" ? "Anuncio pausado." : "Anuncio archivado.");
      await loadMyAds();
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "No pudimos cambiar el anuncio.");
    } finally {
      setBusy(false);
    }
  }, [loadMyAds, request, setBusy, setNotice]);

  return {
    archivedAds,
    createAd,
    loadArchivedAds,
    loadMyAds,
    mutateAd,
    ownAds
  };
}
