import { useCallback, useState } from "react";
import type { Dispatch, SetStateAction } from "react";
import { createBusinessAd, listArchivedBusinessAds, listBusinessAds, mutateBusinessAd, updateBusinessAd } from "../../api/businessAds";
import { ApiClientError } from "../../api/client";
import type { AuthenticatedRequest } from "../../api/client";
import type { BusinessMiniAppView } from "../../constants/businessViews";
import { recordActionBreadcrumb } from "../../observability/clientTelemetry";
import type { AdFormState, AdSummary, AdUpdatePayload } from "../../types/ads";
import type { BusinessSummary } from "../../types/business";
import { actionStartedAt, recordBusinessActionCompleted, recordBusinessActionFailed, recordBusinessActionStarted } from "./actionTelemetry";
import { handleBusinessPinError as routeBusinessPinError, requireUnlockedBusinessPin } from "./businessPinGuards";
import { idempotencyKey } from "./helpers";

function adActionErrorMessage(error: unknown, action: "pause" | "archive" | "reactivate") {
  if (!(error instanceof ApiClientError)) {
    return null;
  }
  if (error.code === "PAYMENT_METHOD_NOT_APPROVED") {
    return "Ese anuncio usa un metodo de cobro que ya no esta activo. Editalo y selecciona un metodo activo.";
  }
  if (error.code === "AD_LIMIT_NOT_ALLOWED") {
    return "Ese anuncio ya no esta dentro del rango autorizado para tu negocio.";
  }
  if (error.code === "AD_OVERLAP_NOT_ALLOWED") {
    return "Ya tienes otro anuncio activo con ese mismo rango.";
  }
  if (error.code === "AD_STATUS_INVALID") {
    return action === "reactivate" ? "Este anuncio no se puede reactivar en su estado actual." : "Este anuncio no se puede cambiar en su estado actual.";
  }
  return error.message;
}

function telemetryErrorCode(error: unknown) {
  return error instanceof ApiClientError ? error.code : undefined;
}

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
  const [savingAdId, setSavingAdId] = useState<string | null>(null);
  const [pausingAdId, setPausingAdId] = useState<string | null>(null);
  const [reactivatingAdId, setReactivatingAdId] = useState<string | null>(null);
  const [deletingAdId, setDeletingAdId] = useState<string | null>(null);
  const [republishingAdId, setRepublishingAdId] = useState<string | null>(null);
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

  const patchOwnAd = useCallback((adId: string, patch: Partial<AdSummary>) => {
    setOwnAds((current) => current.map((item) => item.id === adId ? { ...item, ...patch } : item));
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
      setOwnAds([]);
      return false;
    }
  }, [request]);

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

  const createAd = useCallback(async () => {
    if (!business) {
      setNotice("Necesitas un negocio aprobado para publicar.");
      return;
    }
    if (!requireBusinessPinFor("publicar anuncios")) {
      return;
    }
    if (!adForm.payment_method_id) {
      setNotice("Agrega un metodo de cobro para publicar anuncios.");
      return;
    }
    setSavingAdId("new");
    recordActionBreadcrumb("ad_create", { screen: "create-ad", status: "started" });
    try {
      const data = await createBusinessAd<{ ad: AdSummary }>(
        request,
        { ...adForm, business_id: business.id },
        idempotencyKey(`ad_create_${business.id}`)
      );
      replaceOwnAd(data.ad);
      setAdForm((current) => ({ ...current, rate_bs_per_usd: "" }));
      selectAd(data.ad);
      setView("my-ads");
      await refreshMyAds();
      await refreshCreditWallet();
      setNotice(`Anuncio activo por ${data.ad.required_credits} credito(s).`);
      recordActionBreadcrumb("ad_create", { screen: "create-ad", status: "completed" });
    } catch (error) {
      if (!handleBusinessPinError(error, "publicar anuncios")) {
        setNotice(error instanceof Error ? error.message : "No pudimos publicar el anuncio.");
      }
      recordActionBreadcrumb("ad_create", { screen: "create-ad", status: "failed", errorCode: telemetryErrorCode(error) });
    } finally {
      setSavingAdId(null);
    }
  }, [adForm, business, handleBusinessPinError, refreshCreditWallet, refreshMyAds, replaceOwnAd, request, requireBusinessPinFor, selectAd, setAdForm, setNotice, setView]);

  const mutateAd = useCallback(async (adId: string, action: "pause" | "archive" | "reactivate") => {
    if (!requireBusinessPinFor("cambiar anuncios")) {
      return;
    }
    const telemetryAction = action === "pause" ? "ad_pause" : action === "reactivate" ? "ad_reactivate" : "ad_delete";
    const previousAd = ownAds.find((item) => item.id === adId) || null;
    if (action === "pause") {
      setPausingAdId(adId);
      patchOwnAd(adId, { effective_status: "paused", status: "paused" });
    } else if (action === "reactivate") {
      setReactivatingAdId(adId);
      patchOwnAd(adId, { effective_status: "active", status: "active" });
    } else {
      setDeletingAdId(adId);
    }
    recordActionBreadcrumb(telemetryAction, { screen: "my-ads", status: "started" });
    try {
      setNotice(action === "reactivate" ? "Reactivando anuncio..." : action === "pause" ? "Pausando anuncio..." : "Archivando anuncio...");
      const data = await mutateBusinessAd<{ ad: AdSummary }>(request, adId, action, idempotencyKey(`ad_${action}_${adId}`));
      const messageByAction = {
        archive: "Anuncio archivado.",
        pause: "Anuncio pausado.",
        reactivate: "Anuncio activo otra vez."
      };
      if (action === "archive") {
        removeOwnAd(adId);
        closeAdDetail();
      } else {
        replaceOwnAd(data.ad);
        selectAd(data.ad);
      }
      await refreshMyAds();
      await refreshCreditWallet();
      setNotice(messageByAction[action]);
      recordActionBreadcrumb(telemetryAction, { screen: "my-ads", status: "completed" });
    } catch (error) {
      if (previousAd) {
        replaceOwnAd(previousAd);
        selectAd(previousAd);
      } else {
        await refreshMyAds();
      }
      if (!handleBusinessPinError(error, "cambiar anuncios")) {
        setNotice(adActionErrorMessage(error, action) || "No pudimos cambiar el anuncio.");
      }
      recordActionBreadcrumb(telemetryAction, { screen: "my-ads", status: "failed", errorCode: telemetryErrorCode(error) });
    } finally {
      if (action === "pause") {
        setPausingAdId(null);
      } else if (action === "reactivate") {
        setReactivatingAdId(null);
      } else {
        setDeletingAdId(null);
      }
    }
  }, [closeAdDetail, handleBusinessPinError, ownAds, patchOwnAd, refreshCreditWallet, refreshMyAds, removeOwnAd, replaceOwnAd, request, requireBusinessPinFor, selectAd, setNotice]);

  const republishAd = useCallback(async (ad: AdSummary) => {
    if (!requireBusinessPinFor("republicar anuncios")) {
      return;
    }
    setRepublishingAdId(ad.id);
    const startedAt = actionStartedAt();
    recordBusinessActionStarted("ad_republish", "archived-ads");
    try {
      const data = await mutateBusinessAd<{ ad: AdSummary; republished_from_ad_id: string }>(request, ad.id, "republish", idempotencyKey(`ad_republish_${ad.id}`));
      replaceOwnAd(data.ad);
      await refreshMyAds();
      await refreshCreditWallet();
      selectAd(data.ad);
      setView("my-ads");
      setNotice(`Anuncio republicado. Se bloqueo ${data.ad.required_credits} credito(s).`);
      recordBusinessActionCompleted("ad_republish", "archived-ads", startedAt);
    } catch (error) {
      if (!handleBusinessPinError(error, "republicar anuncios")) {
        setNotice(error instanceof Error ? error.message : "No pudimos republicar el anuncio.");
      }
      recordBusinessActionFailed("ad_republish", "archived-ads", startedAt, telemetryErrorCode(error));
    } finally {
      setRepublishingAdId(null);
    }
  }, [handleBusinessPinError, refreshCreditWallet, refreshMyAds, replaceOwnAd, request, requireBusinessPinFor, selectAd, setNotice, setView]);

  const deleteAd = useCallback(async (ad: AdSummary) => {
    if (!requireBusinessPinFor("borrar anuncios")) {
      return;
    }
    const status = ad.effective_status || ad.status;
    if (ad.status === "in_order" || status === "in_order") {
      setNotice("Este anuncio tiene una orden abierta. Cierra la orden antes de retirarlo.");
      return;
    }
    if (ad.status === "archived") {
      setNotice("Este anuncio ya esta archivado.");
      return;
    }
    setDeletingAdId(ad.id);
    recordActionBreadcrumb("ad_delete", { screen: "my-ads", status: "started" });
    try {
      await mutateBusinessAd<{ ad: AdSummary }>(request, ad.id, "archive", idempotencyKey(`ad_delete_archive_${ad.id}`));
      removeOwnAd(ad.id);
      closeAdDetail();
      await refreshMyAds();
      await refreshCreditWallet();
      setNotice("Anuncio retirado. Se consumio el credito de esta publicacion.");
      recordActionBreadcrumb("ad_delete", { screen: "my-ads", status: "completed" });
    } catch (error) {
      replaceOwnAd(ad);
      selectAd(ad);
      if (!handleBusinessPinError(error, "borrar anuncios")) {
        setNotice(error instanceof Error ? error.message : "No pudimos borrar el anuncio.");
      }
      recordActionBreadcrumb("ad_delete", { screen: "my-ads", status: "failed", errorCode: telemetryErrorCode(error) });
    } finally {
      setDeletingAdId(null);
    }
  }, [closeAdDetail, handleBusinessPinError, refreshCreditWallet, refreshMyAds, removeOwnAd, replaceOwnAd, request, requireBusinessPinFor, selectAd, setNotice]);

  const updateSelectedAd = useCallback(async () => {
    if (!selectedAdId) {
      setNotice("Abre un anuncio para editarlo.");
      return;
    }
    if (!requireBusinessPinFor("editar anuncios")) {
      return;
    }
    setSavingAdId(selectedAdId);
    recordActionBreadcrumb("ad_edit", { screen: "my-ads", status: "started" });
    try {
      const data = await updateBusinessAd<{ ad: AdSummary }>(request, selectedAdId, adEditForm, idempotencyKey(`ad_update_${selectedAdId}`));
      replaceOwnAd(data.ad);
      setNotice("Anuncio actualizado.");
      setIsEditingSelectedAd(false);
      selectAd(data.ad);
      await refreshMyAds();
      recordActionBreadcrumb("ad_edit", { screen: "my-ads", status: "completed" });
    } catch (error) {
      if (!handleBusinessPinError(error, "editar anuncios")) {
        setNotice(error instanceof Error ? error.message : "No pudimos actualizar el anuncio.");
      }
      recordActionBreadcrumb("ad_edit", { screen: "my-ads", status: "failed", errorCode: telemetryErrorCode(error) });
    } finally {
      setSavingAdId(null);
    }
  }, [adEditForm, handleBusinessPinError, refreshMyAds, replaceOwnAd, request, requireBusinessPinFor, selectAd, selectedAdId, setNotice]);

  return {
    adEditForm,
    archivedAds,
    cancelEditingAd,
    closeAdDetail,
    createAd,
    deleteAd,
    deletingAdId,
    isEditingSelectedAd,
    loadArchivedAds,
    loadingScreen,
    loadMyAds,
    mutateAd,
    ownAds,
    pausingAdId,
    reactivatingAdId,
    republishingAdId,
    republishAd,
    refreshMyAds,
    savingAdId,
    selectAd,
    selectedAdId,
    setAdEditForm,
    startEditingAd,
    updateSelectedAd
  };
}
