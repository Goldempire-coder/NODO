"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { acceptTerms as acceptUserTerms } from "../api/users";
import { ApiClientError, apiRequest } from "../api/client";
import { isBusinessMiniAppView, type BusinessMiniAppView } from "../constants/businessViews";
import { CURRENT_CLIENT_TERMS_VERSION, hasAcceptedCurrentClientTerms } from "../constants/legal";
import type { PublicUser } from "../types/auth";
import { configureTelemetryContext } from "../observability/clientTelemetry";
import { fallbackForBusinessMiniAppView, ROOT_BUSINESS_VIEWS } from "./business-mini-app/helpers";
import { useBusinessAccessModel } from "./business-mini-app/useBusinessAccessModel";
import { useBusinessAdsModel } from "./business-mini-app/useBusinessAdsModel";
import { useBusinessChatModel } from "./business-mini-app/useBusinessChatModel";
import { useBusinessCreditsModel } from "./business-mini-app/useBusinessCreditsModel";
import { useBusinessHomeSummaryModel } from "./business-mini-app/useBusinessHomeSummaryModel";
import { useBusinessOrdersModel } from "./business-mini-app/useBusinessOrdersModel";
import { useBusinessTelegramControls } from "./business-mini-app/useBusinessTelegramControls";
import { useSurfaceSupportModel } from "./useSurfaceSupportModel";

export function useBusinessMiniAppModel({ user, token }: { user: PublicUser; token: string }) {
  const [view, setCurrentView] = useState<BusinessMiniAppView>("business-dashboard");
  const [currentUser, setCurrentUser] = useState(user);
  const viewHistoryRef = useRef<BusinessMiniAppView[]>([]);
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);

  const request = useCallback(
    async (path: string, options: RequestInit = {}) => {
      const headers = new Headers(options.headers || {});
      headers.set("X-NODO-Surface", "business_mini_app");
      try {
        return await apiRequest<any>(path, token, { ...options, headers });
      } catch (error) {
        if (error instanceof ApiClientError && error.code === "TERMS_ACCEPTANCE_REQUIRED") {
          setNotice("Acepta los terminos de NODO Negocio para continuar.");
          setCurrentView("business-terms");
        }
        throw error;
      }
    },
    [token]
  );

  const setView = useCallback((nextView: BusinessMiniAppView) => {
    const safeView = isBusinessMiniAppView(nextView) ? nextView : "business-dashboard";
    setCurrentView((currentView) => {
      if (currentView === safeView) {
        return currentView;
      }
      viewHistoryRef.current = [...viewHistoryRef.current, currentView].slice(-20);
      return safeView;
    });
  }, []);

  const goBack = useCallback(() => {
    setCurrentView((currentView) => {
      const previousView = viewHistoryRef.current.pop();
      const fallback = fallbackForBusinessMiniAppView(currentView);
      return previousView && isBusinessMiniAppView(previousView) ? previousView : fallback;
    });
  }, []);

  const canGoBack = useMemo(() => !ROOT_BUSINESS_VIEWS.has(view), [view]);

  const acceptBusinessTerms = useCallback(async () => {
    setBusy(true);
    try {
      const acceptedUser = await acceptUserTerms<PublicUser>(request, CURRENT_CLIENT_TERMS_VERSION);
      setCurrentUser(acceptedUser);
      setNotice("Terminos aceptados. Ya puedes preparar tu negocio.");
      setView("business-dashboard");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "No se pudieron aceptar los terminos.");
    } finally {
      setBusy(false);
    }
  }, [request, setView]);

  const access = useBusinessAccessModel({ request, setBusy, setNotice, setView });
  const credits = useBusinessCreditsModel({ business: access.business, request, setBusy, setNotice, setView });
  const ads = useBusinessAdsModel({
    adForm: access.adForm,
    business: access.business,
    request,
    refreshCreditWallet: credits.refreshCreditWallet,
    setAdForm: access.setAdForm,
    setNotice,
    setView
  });
  const orders = useBusinessOrdersModel({ request, setBusy, setNotice, setView });
  const chat = useBusinessChatModel({ request, setBusy, setNotice, setView });
  const support = useSurfaceSupportModel({ request, setBusy, setNotice });
  const homeSummary = useBusinessHomeSummaryModel({
    accessState: access.accessState,
    refreshBusinessOrders: orders.refreshBusinessOrders,
    refreshCreditWallet: credits.refreshCreditWallet,
    refreshMyAds: ads.refreshMyAds,
    setCurrentView,
    view
  });
  const handledOrderDeepLinkRef = useRef(false);

  useEffect(() => {
    configureTelemetryContext(token, "business_mini_app");
    return () => configureTelemetryContext(null, null);
  }, [token]);

  useEffect(() => {
    void access.loadBusinessProfile();
  }, [access.loadBusinessProfile]);

  useEffect(() => {
    if (handledOrderDeepLinkRef.current || access.accessState !== "ready" || typeof window === "undefined") {
      return;
    }
    const params = new URLSearchParams(window.location.search);
    const orderId = params.get("order_id");
    if (params.get("view") !== "business-order-detail" || !orderId) {
      return;
    }
    handledOrderDeepLinkRef.current = true;
    void orders.openBusinessOrder(orderId);
  }, [access.accessState, orders.openBusinessOrder]);

  useEffect(() => {
    if (access.accessState !== "ready") {
      return;
    }
    if (!hasAcceptedCurrentClientTerms(currentUser)) {
      setCurrentView("business-terms");
      return;
    }
    void orders.pollBusinessOrderUpdates();
    const interval = window.setInterval(() => {
      void orders.pollBusinessOrderUpdates();
    }, 10000);
    return () => window.clearInterval(interval);
  }, [access.accessState, currentUser, orders.pollBusinessOrderUpdates]);

  useBusinessTelegramControls({
    adForm: access.adForm,
    busy: busy || ads.savingAdId === "new",
    canGoBack,
    createAd: ads.createAd,
    goBack,
    view
  });

  return {
    user: currentUser,
    acceptBusinessTerms,
    view,
    setView,
    loadHomeSummary: homeSummary.loadHomeSummary,
    goBack,
    canGoBack,
    notice,
    setNotice,
    busy,
    homeSummaryState: homeSummary.homeSummaryState,
    ...access,
    ...ads,
    ...orders,
    ...credits,
    ...chat,
    ...support
  };
}

export type BusinessMiniAppModel = ReturnType<typeof useBusinessMiniAppModel>;
