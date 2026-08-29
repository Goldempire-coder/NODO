import { useCallback, useRef, useState } from "react";
import type { Dispatch, SetStateAction } from "react";
import { listArchivedBusinessAds, listBusinessAds } from "../../api/businessAds";
import type { AuthenticatedRequest } from "../../api/client";
import type { BusinessMiniAppView } from "../../constants/businessViews";
import type { AdFormState, AdSummary, AdUpdatePayload } from "../../types/ads";
import type { BusinessSummary } from "../../types/business";
import { handleBusinessPinError as routeBusinessPinError, requireUnlockedBusinessPin } from "./businessPinGuards";
import { useBusinessAdActionsModel } from "./useBusinessAdActionsModel";

type BusinessAdsPage = {
  items: AdSummary[];
  next_cursor?: string | null;
};

const BUSINESS_AD_PAGE_SIZE = 20;

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
  const [ownAdsNextCursor, setOwnAdsNextCursor] = useState<string | null>(null);
  const [ownAdsLoadingMore, setOwnAdsLoadingMore] = useState(false);
  const [archivedAds, setArchivedAds] = useState<AdSummary[]>([]);
  const [archivedAdsNextCursor, setArchivedAdsNextCursor] = useState<string | null>(null);
  const [archivedAdsLoadingMore, setArchivedAdsLoadingMore] = useState(false);
  const [selectedAdId, setSelectedAdId] = useState<string | null>(null);
  const [isEditingSelectedAd, setIsEditingSelectedAd] = useState(false);
  const [loadingScreen, setLoadingScreen] = useState<BusinessMiniAppView | null>(null);
  const [adEditForm, setAdEditForm] = useState<AdUpdatePayload>({
    payment_method_id: "",
    amount_max_usd: "",
    amount_min_usd: "",
    rate_bs_per_usd: ""
  });
  const ownAdsRequestIdRef = useRef(0);
  const archivedAdsRequestIdRef = useRef(0);

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
    const requestId = ownAdsRequestIdRef.current + 1;
    ownAdsRequestIdRef.current = requestId;
    setView("my-ads");
    setLoadingScreen("my-ads");
    try {
      const data = await listBusinessAds<BusinessAdsPage>(request, BUSINESS_AD_PAGE_SIZE);
      if (ownAdsRequestIdRef.current !== requestId) {
        return;
      }
      setOwnAds(data.items);
      setOwnAdsNextCursor(data.next_cursor ?? null);
      setNotice(data.items.length ? "Anuncios cargados." : "Aun no tienes anuncios activos o pausados.");
    } catch (error) {
      if (ownAdsRequestIdRef.current === requestId) {
        setNotice(error instanceof Error ? error.message : "No pudimos cargar tus anuncios.");
      }
    } finally {
      if (ownAdsRequestIdRef.current === requestId) {
        setLoadingScreen(null);
      }
    }
  }, [request, setNotice, setView]);

  const refreshMyAds = useCallback(async () => {
    const requestId = ownAdsRequestIdRef.current + 1;
    ownAdsRequestIdRef.current = requestId;
    try {
      const data = await listBusinessAds<BusinessAdsPage>(request, BUSINESS_AD_PAGE_SIZE);
      if (ownAdsRequestIdRef.current !== requestId) {
        return false;
      }
      setOwnAds(data.items);
      setOwnAdsNextCursor(data.next_cursor ?? null);
      return true;
    } catch {
      if (ownAdsRequestIdRef.current === requestId) {
        setNotice("No pudimos actualizar anuncios; dejamos la ultima lista cargada.");
      }
      return false;
    }
  }, [request, setNotice]);

  const loadMoreOwnAds = useCallback(async () => {
    const cursor = ownAdsNextCursor;
    const requestId = ownAdsRequestIdRef.current;
    if (!cursor || ownAdsLoadingMore) {
      return false;
    }
    setOwnAdsLoadingMore(true);
    try {
      const data = await listBusinessAds<BusinessAdsPage>(request, BUSINESS_AD_PAGE_SIZE, cursor);
      if (ownAdsRequestIdRef.current !== requestId) {
        return false;
      }
      setOwnAds((current) => {
        const knownIds = new Set(current.map((item) => item.id));
        return [
          ...current,
          ...data.items.filter((item) => !knownIds.has(item.id))
        ];
      });
      setOwnAdsNextCursor(data.next_cursor ?? null);
      return true;
    } catch (error) {
      if (ownAdsRequestIdRef.current === requestId) {
        setNotice(error instanceof Error ? error.message : "No pudimos cargar mas anuncios.");
      }
      return false;
    } finally {
      setOwnAdsLoadingMore(false);
    }
  }, [ownAdsLoadingMore, ownAdsNextCursor, request, setNotice]);

  const loadArchivedAds = useCallback(async () => {
    const requestId = archivedAdsRequestIdRef.current + 1;
    archivedAdsRequestIdRef.current = requestId;
    setView("archived-ads");
    setLoadingScreen("archived-ads");
    try {
      const data = await listArchivedBusinessAds<BusinessAdsPage>(request, BUSINESS_AD_PAGE_SIZE);
      if (archivedAdsRequestIdRef.current !== requestId) {
        return;
      }
      setArchivedAds(data.items);
      setArchivedAdsNextCursor(data.next_cursor ?? null);
      setNotice(data.items.length ? "Historial de anuncios cargado." : "Aun no hay anuncios archivados.");
    } catch (error) {
      if (archivedAdsRequestIdRef.current === requestId) {
        setNotice(error instanceof Error ? error.message : "No pudimos cargar el historial.");
      }
    } finally {
      if (archivedAdsRequestIdRef.current === requestId) {
        setLoadingScreen(null);
      }
    }
  }, [request, setNotice, setView]);

  const loadMoreArchivedAds = useCallback(async () => {
    const cursor = archivedAdsNextCursor;
    const requestId = archivedAdsRequestIdRef.current;
    if (!cursor || archivedAdsLoadingMore) {
      return false;
    }
    setArchivedAdsLoadingMore(true);
    try {
      const data = await listArchivedBusinessAds<BusinessAdsPage>(request, BUSINESS_AD_PAGE_SIZE, cursor);
      if (archivedAdsRequestIdRef.current !== requestId) {
        return false;
      }
      setArchivedAds((current) => {
        const knownIds = new Set(current.map((item) => item.id));
        return [
          ...current,
          ...data.items.filter((item) => !knownIds.has(item.id))
        ];
      });
      setArchivedAdsNextCursor(data.next_cursor ?? null);
      return true;
    } catch (error) {
      if (archivedAdsRequestIdRef.current === requestId) {
        setNotice(error instanceof Error ? error.message : "No pudimos cargar mas archivados.");
      }
      return false;
    } finally {
      setArchivedAdsLoadingMore(false);
    }
  }, [archivedAdsLoadingMore, archivedAdsNextCursor, request, setNotice]);

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
    archivedAdsLoadingMore,
    archivedAdsNextCursor,
    cancelEditingAd,
    closeAdDetail,
    createAd: actions.createAd,
    deleteAd: actions.deleteAd,
    deletingAdId: actions.deletingAdId,
    isEditingSelectedAd,
    loadArchivedAds,
    loadMoreArchivedAds,
    loadingScreen,
    loadMoreOwnAds,
    loadMyAds,
    mutateAd: actions.mutateAd,
    ownAds,
    ownAdsLoadingMore,
    ownAdsNextCursor,
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
