import { useCallback, useState } from "react";
import type { Dispatch, SetStateAction } from "react";
import { createBusinessAd, mutateBusinessAd, updateBusinessAd } from "../../api/businessAds";
import { ApiClientError, type AuthenticatedRequest } from "../../api/client";
import type { BusinessMiniAppView } from "../../constants/businessViews";
import { recordActionBreadcrumb } from "../../observability/clientTelemetry";
import type { AdFormState, AdSummary, AdUpdatePayload } from "../../types/ads";
import type { BusinessSummary } from "../../types/business";
import { actionStartedAt, recordBusinessActionCompleted, recordBusinessActionFailed, recordBusinessActionStarted } from "../actionTelemetry";
import { useStableIdempotencyKeys } from "../useStableIdempotencyKeys";

type MutateAdAction = "pause" | "archive" | "reactivate";

function adActionErrorMessage(error: unknown, action: MutateAdAction) {
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

export function useBusinessAdActionsModel({
  adEditForm,
  adForm,
  business,
  closeAdDetail,
  ownAds,
  refreshCreditWallet,
  refreshMyAds,
  removeOwnAd,
  replaceOwnAd,
  request,
  requireBusinessPinFor,
  handleBusinessPinError,
  selectAd,
  selectedAdId,
  setAdForm,
  setIsEditingSelectedAd,
  setNotice,
  setView
}: {
  adEditForm: AdUpdatePayload;
  adForm: AdFormState;
  business: BusinessSummary | null;
  closeAdDetail: () => void;
  ownAds: AdSummary[];
  refreshCreditWallet: () => Promise<unknown>;
  refreshMyAds: () => Promise<boolean>;
  removeOwnAd: (adId: string) => void;
  replaceOwnAd: (ad: AdSummary) => void;
  request: AuthenticatedRequest;
  requireBusinessPinFor: (action: string) => boolean;
  handleBusinessPinError: (error: unknown, action: string) => boolean;
  selectAd: (ad: AdSummary) => void;
  selectedAdId: string | null;
  setAdForm: Dispatch<SetStateAction<AdFormState>>;
  setIsEditingSelectedAd: Dispatch<SetStateAction<boolean>>;
  setNotice: (notice: string) => void;
  setView: (view: BusinessMiniAppView) => void;
}) {
  const [savingAdId, setSavingAdId] = useState<string | null>(null);
  const [pausingAdId, setPausingAdId] = useState<string | null>(null);
  const [reactivatingAdId, setReactivatingAdId] = useState<string | null>(null);
  const [deletingAdId, setDeletingAdId] = useState<string | null>(null);
  const [republishingAdId, setRepublishingAdId] = useState<string | null>(null);
  const { clearIdempotencyKey, getIdempotencyKey } = useStableIdempotencyKeys();

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
    const idempotencyScope = `ad_create_${business.id}`;
    try {
      const data = await createBusinessAd<{ ad: AdSummary }>(
        request,
        { ...adForm, business_id: business.id },
        getIdempotencyKey(idempotencyScope, { ...adForm, business_id: business.id })
      );
      clearIdempotencyKey(idempotencyScope);
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
  }, [adForm, business, clearIdempotencyKey, getIdempotencyKey, handleBusinessPinError, refreshCreditWallet, refreshMyAds, replaceOwnAd, request, requireBusinessPinFor, selectAd, setAdForm, setNotice, setView]);

  const mutateAd = useCallback(async (adId: string, action: MutateAdAction) => {
    if (!requireBusinessPinFor("cambiar anuncios")) {
      return;
    }
    const telemetryAction = action === "pause" ? "ad_pause" : action === "reactivate" ? "ad_reactivate" : "ad_delete";
    const previousAd = ownAds.find((item) => item.id === adId) || null;
    if (action === "pause") {
      setPausingAdId(adId);
    } else if (action === "reactivate") {
      setReactivatingAdId(adId);
    } else {
      setDeletingAdId(adId);
    }
    recordActionBreadcrumb(telemetryAction, { screen: "my-ads", status: "started" });
    const idempotencyScope = `ad_${action}_${adId}`;
    try {
      setNotice(action === "reactivate" ? "Reactivando anuncio..." : action === "pause" ? "Pausando anuncio..." : "Archivando anuncio...");
      const data = await mutateBusinessAd<{ ad: AdSummary }>(request, adId, action, getIdempotencyKey(idempotencyScope, { action, adId }));
      clearIdempotencyKey(idempotencyScope);
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
  }, [clearIdempotencyKey, closeAdDetail, getIdempotencyKey, handleBusinessPinError, ownAds, refreshCreditWallet, refreshMyAds, removeOwnAd, replaceOwnAd, request, requireBusinessPinFor, selectAd, setNotice]);

  const republishAd = useCallback(async (ad: AdSummary) => {
    if (!requireBusinessPinFor("republicar anuncios")) {
      return;
    }
    setRepublishingAdId(ad.id);
    const startedAt = actionStartedAt();
    recordBusinessActionStarted("ad_republish", "archived-ads");
    const idempotencyScope = `ad_republish_${ad.id}`;
    try {
      const data = await mutateBusinessAd<{ ad: AdSummary; republished_from_ad_id: string }>(request, ad.id, "republish", getIdempotencyKey(idempotencyScope, { adId: ad.id, action: "republish" }));
      clearIdempotencyKey(idempotencyScope);
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
  }, [clearIdempotencyKey, getIdempotencyKey, handleBusinessPinError, refreshCreditWallet, refreshMyAds, replaceOwnAd, request, requireBusinessPinFor, selectAd, setNotice, setView]);

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
    const idempotencyScope = `ad_delete_archive_${ad.id}`;
    try {
      await mutateBusinessAd<{ ad: AdSummary }>(request, ad.id, "archive", getIdempotencyKey(idempotencyScope, { adId: ad.id, action: "archive" }));
      clearIdempotencyKey(idempotencyScope);
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
  }, [clearIdempotencyKey, closeAdDetail, getIdempotencyKey, handleBusinessPinError, refreshCreditWallet, refreshMyAds, removeOwnAd, replaceOwnAd, request, requireBusinessPinFor, selectAd, setNotice]);

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
    const idempotencyScope = `ad_update_${selectedAdId}`;
    try {
      const data = await updateBusinessAd<{ ad: AdSummary }>(request, selectedAdId, adEditForm, getIdempotencyKey(idempotencyScope, { adId: selectedAdId, ...adEditForm }));
      clearIdempotencyKey(idempotencyScope);
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
  }, [adEditForm, clearIdempotencyKey, getIdempotencyKey, handleBusinessPinError, refreshMyAds, replaceOwnAd, request, requireBusinessPinFor, selectAd, selectedAdId, setIsEditingSelectedAd, setNotice]);

  return {
    createAd,
    deleteAd,
    deletingAdId,
    mutateAd,
    pausingAdId,
    reactivatingAdId,
    republishingAdId,
    republishAd,
    savingAdId,
    updateSelectedAd
  };
}
