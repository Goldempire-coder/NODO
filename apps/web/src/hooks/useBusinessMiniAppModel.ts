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
import { useBusinessOrdersModel } from "./business-mini-app/useBusinessOrdersModel";
import { useBusinessTelegramControls } from "./business-mini-app/useBusinessTelegramControls";

export function useBusinessMiniAppModel({ user, token }: { user: PublicUser; token: string }) {
  const [view, setCurrentView] = useState<BusinessMiniAppView>("business-dashboard");
  const viewHistoryRef = useRef<BusinessMiniAppView[]>([]);
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);

  const request = useCallback(
    async (path: string, options: RequestInit = {}) => apiRequest<any>(path, token, options),
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

  const access = useBusinessAccessModel({ request, setBusy, setNotice });
  const ads = useBusinessAdsModel({
    adForm: access.adForm,
    business: access.business,
    request,
    setAdForm: access.setAdForm,
    setBusy,
    setNotice,
    setView
  });
  const orders = useBusinessOrdersModel({ request, setBusy, setNotice, setView });
  const credits = useBusinessCreditsModel({ request, setBusy, setNotice, setView });
  const chat = useBusinessChatModel({ request, setBusy, setNotice, setView });

  useEffect(() => {
    void access.loadBusinessProfile();
  }, [access.loadBusinessProfile]);

  useBusinessTelegramControls({
    adForm: access.adForm,
    busy,
    canGoBack,
    createAd: ads.createAd,
    goBack,
    view
  });

  return {
    user,
    view,
    setView,
    goBack,
    canGoBack,
    notice,
    setNotice,
    busy,
    ...access,
    ...ads,
    ...orders,
    ...credits,
    ...chat
  };
}

export type BusinessMiniAppModel = ReturnType<typeof useBusinessMiniAppModel>;
