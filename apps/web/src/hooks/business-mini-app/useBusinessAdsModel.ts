import { useCallback, useState } from "react";
import type { Dispatch, SetStateAction } from "react";
import { listArchivedBusinessAds, listBusinessAds } from "../../api/businessAds";
import type { AuthenticatedRequest } from "../../api/client";
import type { BusinessMiniAppView } from "../../constants/businessViews";
import type { AdFormState, AdSummary, AdUpdatePayload } from "../../types/ads";
import type { BusinessSummary } from "../../types/business";
import { handleBusinessPinError as routeBusinessPinError, requireUnlockedBusinessPin } from "./businessPinGuards";
import { useBusinessAdActionsModel } from "./useBusinessAdActionsModel";

export function useBusinessAdsModel({
  adForm,
  business,
  request,
  refreshCreditWallet,
  setAdForm,
  setNotice,
  setView
}: {
  adForm: AdFormState;
  business: BusinessSummary | null;
  request: AuthenticatedRequest;
  refreshCreditWallet: () => Promise<unknown>;
  setAdForm: Dispatch<SetStateAction<AdFormState>>;
  setNotice: (notice: string) => void;
  setView: (view: BusinessMiniAppView) => void;
}) {
  const [ownAds, setOwnAds] = useState<AdSummary[]>([]);
  const [archivedAds, setArchivedAds] = useState<AdSummary[]>([]);
  const [selectedAdId, setSelectedAdId] = useState<string | null>(null);
  const [isEditingSelectedAd, setIsEditingSelectedAd] = useState(false);
  const [loadingScreen, setLoadingScreen] = useState<BusinessMiniAppView | null>(null);
  const [adEditForm, setAdEditForm] = useState<AdUpdatePayload>({
    payment_method_id: "",
    amount_max_usd: "",
    amount_min_usd: "",
    rate_bs_per_usd: ""
  });

  const fillAdEditForm = useCallback((ad: AdSummary) => {
    setAdEditForm({
      payment_method_id: ad.payment_method_id,
      amount_max_usd: ad.amount_max_usd,
      amount_min_usd: ad.amount_min_usd,
      rate_bs_per_usd: ad.rate_bs_per_usd
    });
  }, []);

  const selectAd = useCallback((ad: AdSummary) => {
    setSelectedAdId(ad.id);
    setIsEditingSelectedAd(false);
    fillAdEditForm(ad);
  }, [fillAdEditForm]);

  const replaceOwnAd = useCallback((ad: AdSummary) => {
    setOwnAds((current) => {
      const next = current.map((item) => item.id === ad.id ? ad : item);
      return next.some((item) => item.id === ad.id) ? next : [ad, ...next];
    });
  }, []);

  const removeOwnAd = useCallback((adId: string) => {
    setOwnAds((current) => current.filter((item) => item.id !== adId));
    setSelectedAdId((current) => current === adId ? null : current);
  }, []);

  const closeAdDetail = useCallback(() => {
    setSelectedAdId(null);
    setIsEditingSelectedAd(false);
  }, []);

  const cancelEditingAd = useCallback(() => {
    setIsEditingSelectedAd(false);
  }, []);

  const requireBusinessPinFor = useCallback((action: string) => {
    return requireUnlockedBusinessPin({ action, business, setNotice, setView });
  }, [business?.access_link, setNotice, setView]);

  const handleBusinessPinError = useCallback((error: unknown, action: string) => {
    return routeBusinessPinError({ action, error, setNotice, setView });
  }, [setNotice, setView]);

  const startEditingAd = useCallback((ad: AdSummary) => {
    if (!requireBusinessPinFor("editar anuncios")) {
      return;
    }
    setSelectedAdId(ad.id);
    setIsEditingSelectedAd(true);
    fillAdEditForm(ad);
  }, [fillAdEditForm, requireBusinessPinFor]);

  const loadMyAds = useCallback(async () => {
    setView("my-ads");
    setLoadingScreen("my-ads");
    try {
      const data = await listBusinessAds<{ items: AdSummary[] }>(request);
      setOwnAds(data.items);
      setNotice(data.items.length ? "Anuncios cargados." : "Aun no tienes anuncios activos o pausados.");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "No pudimos cargar tus anuncios.");
    } finally {
      setLoadingScreen(null);
    }
  }, [request, setNotice, setView]);

  const refreshMyAds = useCallback(async () => {
    try {
      const data = await listBusinessAds<{ items: AdSummary[] }>(request);
      setOwnAds(data.items);
      return true;
    } catch {
      setNotice("No pudimos actualizar anuncios; dejamos la ultima lista cargada.");
      return false;
    }
  }, [request, setNotice]);

  const loadArchivedAds = useCallback(async () => {
    setView("archived-ads");
    setLoadingScreen("archived-ads");
    try {
      const data = await listArchivedBusinessAds<{ items: AdSummary[] }>(request);
      setArchivedAds(data.items);
      setNotice(data.items.length ? "Historial de anuncios cargado." : "Aun no hay anuncios archivados.");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "No pudimos cargar el historial.");
    } finally {
      setLoadingScreen(null);
    }
  }, [request, setNotice, setView]);

  const actions = useBusinessAdActionsModel({
    adEditForm,
    adForm,
    business,
    closeAdDetail,
    handleBusinessPinError,
    ownAds,
    refreshCreditWallet,
    refreshMyAds,
    removeOwnAd,
    replaceOwnAd,
    request,
    requireBusinessPinFor,
    selectAd,
    selectedAdId,
    setAdForm,
    setIsEditingSelectedAd,
    setNotice,
    setView
  });

  return {
    adEditForm,
    archivedAds,
    cancelEditingAd,
    closeAdDetail,
    createAd: actions.createAd,
    deleteAd: actions.deleteAd,
    deletingAdId: actions.deletingAdId,
    isEditingSelectedAd,
    loadArchivedAds,
    loadingScreen,
    loadMyAds,
    mutateAd: actions.mutateAd,
    ownAds,
    pausingAdId: actions.pausingAdId,
    reactivatingAdId: actions.reactivatingAdId,
    republishingAdId: actions.republishingAdId,
    republishAd: actions.republishAd,
    refreshMyAds,
    savingAdId: actions.savingAdId,
    selectAd,
    selectedAdId,
    setAdEditForm,
    startEditingAd,
    updateSelectedAd: actions.updateSelectedAd
  };
}
