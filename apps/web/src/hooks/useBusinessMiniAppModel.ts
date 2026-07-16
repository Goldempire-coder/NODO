"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { apiRequest } from "../api/client";
import { isBusinessMiniAppView, type BusinessMiniAppView } from "../constants/businessViews";
import type { PublicUser } from "../types/auth";
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
  const viewHistoryRef = useRef<BusinessMiniAppView[]>([]);
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);

  const request = useCallback(
    async (path: string, options: RequestInit = {}) => {
      const headers = new Headers(options.headers || {});
      headers.set("X-NODO-Surface", "business_mini_app");
      return apiRequest<any>(path, token, { ...options, headers });
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
    void orders.pollBusinessOrderUpdates();
    const interval = window.setInterval(() => {
      void orders.pollBusinessOrderUpdates();
    }, 10000);
    return () => window.clearInterval(interval);
  }, [access.accessState, orders.pollBusinessOrderUpdates]);

  useBusinessTelegramControls({
    adForm: access.adForm,
    busy: busy || ads.savingAdId === "new",
    canGoBack,
    createAd: ads.createAd,
    goBack,
    view
  });

  return {
    user,
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
