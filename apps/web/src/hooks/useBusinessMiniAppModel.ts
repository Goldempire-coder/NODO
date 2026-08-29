"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  acceptBusinessLegalTerms,
  BUSINESS_CREDIT_TERMS_DOCUMENT_SET,
  BUSINESS_TERMS_DOCUMENT_SET,
  getBusinessLegalRequirements
} from "../api/legal";
import { acceptTerms as acceptUserTerms } from "../api/users";
import { ApiClientError, apiRequest } from "../api/client";
import { isBusinessMiniAppView, type BusinessMiniAppView } from "../constants/businessViews";
import { CURRENT_CLIENT_TERMS_VERSION, hasAcceptedCurrentClientTerms } from "../constants/legal";
import type { PublicUser } from "../types/auth";
import type { BusinessLegalDocumentSet, BusinessLegalRequirement, BusinessLegalRequirements } from "../types/legal";
import { configureTelemetryContext } from "../observability/clientTelemetry";
import { actionStartedAt } from "./actionTelemetry";
import { fallbackForBusinessMiniAppView, ROOT_BUSINESS_VIEWS } from "./business-mini-app/helpers";
import { useBusinessAccessModel } from "./business-mini-app/useBusinessAccessModel";
import { useBusinessAdsModel } from "./business-mini-app/useBusinessAdsModel";
import { useBusinessChatModel } from "./business-mini-app/useBusinessChatModel";
import { useBusinessCreditsModel } from "./business-mini-app/useBusinessCreditsModel";
import { useBusinessHomeSummaryModel } from "./business-mini-app/useBusinessHomeSummaryModel";
import { useBusinessOrdersModel } from "./business-mini-app/useBusinessOrdersModel";
import { useBusinessTelegramControls } from "./business-mini-app/useBusinessTelegramControls";
import { useSurfaceSupportModel } from "./useSurfaceSupportModel";
import { useSurfaceAttentionModel } from "./useSurfaceAttentionModel";

function businessLegalRequirement(
  requirements: BusinessLegalRequirements | null,
  documentSet: BusinessLegalDocumentSet
): BusinessLegalRequirement | null {
  return requirements?.requirements.find((item) => item.document_set === documentSet) || null;
}

export function useBusinessMiniAppModel({ user, token }: { user: PublicUser; token: string }) {
  const [view, setCurrentView] = useState<BusinessMiniAppView>("business-dashboard");
  const [currentUser, setCurrentUser] = useState(user);
  const [businessLegalRequirements, setBusinessLegalRequirements] = useState<BusinessLegalRequirements | null>(null);
  const viewHistoryRef = useRef<BusinessMiniAppView[]>([]);
  const pendingViewTransitionRef = useRef<{ from: BusinessMiniAppView; to: BusinessMiniAppView; startedAt: number } | null>(null);
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const pendingOrderPinResumeRef = useRef<(() => Promise<boolean>) | null>(null);
  const reconciledOrderAttentionRef = useRef<string | null>(null);

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
        if (error instanceof ApiClientError && error.code === "BUSINESS_TERMS_ACCEPTANCE_REQUIRED") {
          setNotice("Acepta los terminos de NODO Negocio para continuar.");
          setCurrentView("business-terms");
        }
        if (error instanceof ApiClientError && error.code === "BUSINESS_CREDIT_TERMS_ACCEPTANCE_REQUIRED") {
          setNotice("Acepta los terminos de creditos antes de comprar.");
          setCurrentView("business-credit-terms");
        }
        throw error;
      }
    },
    [token]
  );

  const setView = useCallback((nextView: BusinessMiniAppView) => {
    const safeView = isBusinessMiniAppView(nextView) ? nextView : "business-dashboard";
    const startedAt = actionStartedAt();
    setCurrentView((currentView) => {
      if (currentView === safeView) {
        return currentView;
      }
      pendingViewTransitionRef.current = { from: currentView, to: safeView, startedAt };
      viewHistoryRef.current = [...viewHistoryRef.current, currentView].slice(-20);
      return safeView;
    });
  }, []);

  const goBack = useCallback(() => {
    const startedAt = actionStartedAt();
    setCurrentView((currentView) => {
      const previousView = viewHistoryRef.current.pop();
      const fallback = fallbackForBusinessMiniAppView(currentView);
      const nextView = previousView && isBusinessMiniAppView(previousView) ? previousView : fallback;
      if (nextView !== currentView) {
        pendingViewTransitionRef.current = { from: currentView, to: nextView, startedAt };
      }
      return nextView;
    });
  }, []);

  const consumeViewTransition = useCallback((renderedView: BusinessMiniAppView) => {
    const transition = pendingViewTransitionRef.current;
    if (!transition || transition.to !== renderedView) {
      return null;
    }
    pendingViewTransitionRef.current = null;
    return transition;
  }, []);

  const canGoBack = useMemo(() => !ROOT_BUSINESS_VIEWS.has(view), [view]);

  const resumePendingOrderPinAction = useCallback(async () => {
    return pendingOrderPinResumeRef.current
      ? pendingOrderPinResumeRef.current()
      : false;
  }, []);
  const access = useBusinessAccessModel({
    request,
    resumePendingOrderPinAction,
    setBusy,
    setNotice,
    setView
  });

  const currentBusinessLegalRequirements = useMemo(() => {
    return businessLegalRequirements?.business_id === access.business?.id ? businessLegalRequirements : null;
  }, [access.business?.id, businessLegalRequirements]);

  const loadBusinessLegalRequirements = useCallback(async () => {
    if (!access.business?.id) {
      return null;
    }
    const requirements = await getBusinessLegalRequirements(request);
    setBusinessLegalRequirements(requirements);
    return requirements;
  }, [access.business?.id, request]);

  const ensureBusinessCreditTermsAccepted = useCallback(async () => {
    if (!hasAcceptedCurrentClientTerms(currentUser)) {
      setNotice("Acepta los terminos de NODO Negocio para continuar.");
      setView("business-terms");
      return false;
    }
    try {
      const requirements = currentBusinessLegalRequirements || await loadBusinessLegalRequirements();
      if (!requirements) {
        setNotice("No pudimos validar los terminos del negocio.");
        return false;
      }
      if (!businessLegalRequirement(requirements, BUSINESS_TERMS_DOCUMENT_SET)?.accepted) {
        setNotice("Acepta los terminos de NODO Negocio para continuar.");
        setView("business-terms");
        return false;
      }
      if (!businessLegalRequirement(requirements, BUSINESS_CREDIT_TERMS_DOCUMENT_SET)?.accepted) {
        setNotice("Acepta los terminos de creditos antes de comprar.");
        setView("business-credit-terms");
        return false;
      }
      return true;
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "No pudimos validar los terminos de creditos.");
      return false;
    }
  }, [currentBusinessLegalRequirements, currentUser, loadBusinessLegalRequirements, setView]);

  const acceptBusinessTerms = useCallback(async () => {
    setBusy(true);
    try {
      if (!hasAcceptedCurrentClientTerms(currentUser)) {
        const acceptedUser = await acceptUserTerms<PublicUser>(request, CURRENT_CLIENT_TERMS_VERSION);
        setCurrentUser(acceptedUser);
      }
      const requirements = currentBusinessLegalRequirements || await loadBusinessLegalRequirements();
      const requirement = businessLegalRequirement(requirements, BUSINESS_TERMS_DOCUMENT_SET);
      if (!requirement) {
        throw new Error("No pudimos validar los terminos del negocio.");
      }
      await acceptBusinessLegalTerms(request, BUSINESS_TERMS_DOCUMENT_SET, requirement.document_version);
      await loadBusinessLegalRequirements();
      setNotice("Terminos aceptados. Ya puedes preparar tu negocio.");
      setView("business-dashboard");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "No se pudieron aceptar los terminos.");
    } finally {
      setBusy(false);
    }
  }, [currentBusinessLegalRequirements, currentUser, loadBusinessLegalRequirements, request, setView]);

  const credits = useBusinessCreditsModel({
    business: access.business,
    request,
    ensureBusinessCreditTermsAccepted,
    setBusy,
    setNotice,
    setView
  });

  const acceptBusinessCreditTerms = useCallback(async () => {
    setBusy(true);
    try {
      const requirements = currentBusinessLegalRequirements || await loadBusinessLegalRequirements();
      if (!requirements) {
        throw new Error("No pudimos validar los terminos de creditos.");
      }
      if (!businessLegalRequirement(requirements, BUSINESS_TERMS_DOCUMENT_SET)?.accepted) {
        setNotice("Acepta primero los terminos de NODO Negocio.");
        setView("business-terms");
        return;
      }
      const requirement = businessLegalRequirement(requirements, BUSINESS_CREDIT_TERMS_DOCUMENT_SET);
      if (!requirement) {
        throw new Error("No pudimos validar los terminos de creditos.");
      }
      await acceptBusinessLegalTerms(request, BUSINESS_CREDIT_TERMS_DOCUMENT_SET, requirement.document_version);
      await loadBusinessLegalRequirements();
      setNotice("Terminos de creditos aceptados. Ya puedes comprar creditos.");
      await credits.openBuyCredits({ skipLegalCheck: true });
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "No se pudieron aceptar los terminos de creditos.");
    } finally {
      setBusy(false);
    }
  }, [credits.openBuyCredits, currentBusinessLegalRequirements, loadBusinessLegalRequirements, request, setView]);

  const ads = useBusinessAdsModel({
    adForm: access.adForm,
    business: access.business,
    request,
    refreshCreditWallet: credits.refreshCreditWallet,
    setAdForm: access.setAdForm,
    setNotice,
    setView
  });
  const orders = useBusinessOrdersModel({
    business: access.business,
    request,
    setBusy,
    setNotice,
    setView
  });
  pendingOrderPinResumeRef.current = orders.resumePendingBusinessOrderPinAction;
  const chat = useBusinessChatModel({
    business: access.business,
    request,
    syncBusinessOrderFromChat: orders.syncBusinessOrderFromChat,
    setBusy,
    setNotice,
    setView
  });
  const support = useSurfaceSupportModel({ request, setBusy, setNotice, initialScope: "business_general" });
  const awareness = useSurfaceAttentionModel({
    enabled: access.accessState === "ready" && hasAcceptedCurrentClientTerms(currentUser),
    request
  });
  const { acknowledgeAttention, attentionAlert, attentionItems } = awareness;
  useEffect(() => {
    let cancelled = false;
    async function refreshActiveBusinessChatAttention() {
      if (view !== "business-chat" || !chat.chatOrderId) {
        return;
      }
      const item = attentionItems.find(
        (candidate) => candidate.kind === "order" && candidate.resource_id === chat.chatOrderId
      );
      if (!item) {
        return;
      }
      const refreshed = await chat.refreshChat({ silent: true });
      if (!cancelled && refreshed) {
        void acknowledgeAttention("order", item.resource_id);
      }
    }
    void refreshActiveBusinessChatAttention();
    return () => {
      cancelled = true;
    };
  }, [acknowledgeAttention, attentionItems, chat.chatOrderId, chat.refreshChat, view]);
  useEffect(() => {
    let cancelled = false;
    async function refreshVisibleBusinessOrderAttention() {
      if (view === "business-chat") {
        return;
      }
      const isExactDetail = view === "business-order-detail"
        && Boolean(orders.businessOrderDetail?.order.id);
      const isOrderSummaryVisible = view === "business-orders" || view === "business-dashboard";
      if (!isExactDetail && !isOrderSummaryVisible) {
        return;
      }
      const item = isExactDetail
        ? attentionItems.find(
            (candidate) => candidate.kind === "order"
              && candidate.resource_id === orders.businessOrderDetail?.order.id
          )
        : attentionItems.find((candidate) => candidate.kind === "order");
      if (!item) {
        return;
      }
      const refreshScope = isExactDetail
        ? `detail:${item.resource_id}`
        : `${view}:${orders.businessOrderFilter}`;
      const refreshKey = `${refreshScope}:${item.signature}`;
      if (reconciledOrderAttentionRef.current === refreshKey) {
        return;
      }
      // Attention polls every 15s; a stable signature must not add another list/detail poll.
      reconciledOrderAttentionRef.current = refreshKey;
      const refreshed = await orders.refreshBusinessOrderFromAttention(item.resource_id);
      if (!refreshed && reconciledOrderAttentionRef.current === refreshKey) {
        reconciledOrderAttentionRef.current = null;
      }
      if (!cancelled && refreshed && isExactDetail) {
        void acknowledgeAttention("order", item.resource_id);
      }
    }
    void refreshVisibleBusinessOrderAttention();
    return () => {
      cancelled = true;
    };
  }, [
    acknowledgeAttention,
    attentionItems,
    orders.businessOrderFilter,
    orders.businessOrderDetail?.order.id,
    orders.refreshBusinessOrderFromAttention,
    view
  ]);
  const openBusinessOrderWithAttention = useCallback(async (orderId: string) => {
    const opened = await orders.openBusinessOrder(orderId);
    if (opened) {
      void acknowledgeAttention("order", orderId);
    }
  }, [acknowledgeAttention, orders.openBusinessOrder]);
  const openBusinessSupportTicketWithAttention = useCallback(async (ticketId: string) => {
    setView("business-support");
    const opened = await support.openSupportTicket(ticketId);
    if (opened) {
      void acknowledgeAttention("support", ticketId);
    }
  }, [acknowledgeAttention, setView, support.openSupportTicket]);
  const openBusinessSupport = useCallback(() => {
    setView("business-support");
  }, [setView]);
  const openAttentionAlert = useCallback(async () => {
    const item = attentionAlert;
    if (!item) {
      return;
    }
    if (item.kind === "order") {
      await openBusinessOrderWithAttention(item.resource_id);
      return;
    }
    await openBusinessSupportTicketWithAttention(item.resource_id);
  }, [attentionAlert, openBusinessOrderWithAttention, openBusinessSupportTicketWithAttention]);
  const homeSummary = useBusinessHomeSummaryModel({
    accessState: access.accessState,
    refreshBusinessCapacity: access.refreshBusinessCapacity,
    refreshBusinessOrders: orders.refreshBusinessOrders,
    refreshCreditWallet: credits.refreshCreditWallet,
    refreshMyAds: ads.refreshMyAds,
    setView,
    view
  });
  const handledDeepLinkRef = useRef(false);

  useEffect(() => {
    configureTelemetryContext(token, "business_mini_app");
    return () => configureTelemetryContext(null, null);
  }, [token]);

  useEffect(() => {
    void access.loadBusinessProfile();
  }, [access.loadBusinessProfile]);

  useEffect(() => {
    if (handledDeepLinkRef.current || access.accessState !== "ready" || typeof window === "undefined") {
      return;
    }
    const params = new URLSearchParams(window.location.search);
    const deepLinkView = params.get("view");
    const orderId = params.get("order_id");
    const ticketId = params.get("ticket_id");
    if (deepLinkView === "business-order-detail" && orderId) {
      handledDeepLinkRef.current = true;
      void openBusinessOrderWithAttention(orderId);
      return;
    }
    if (deepLinkView === "business-chat" && orderId) {
      handledDeepLinkRef.current = true;
      void chat.openBusinessChat(orderId);
      return;
    }
    if (deepLinkView === "business-support" && ticketId) {
      handledDeepLinkRef.current = true;
      void openBusinessSupportTicketWithAttention(ticketId);
    }
  }, [
    access.accessState,
    chat.openBusinessChat,
    openBusinessOrderWithAttention,
    openBusinessSupportTicketWithAttention
  ]);

  useEffect(() => {
    if (access.accessState === "ready" && !hasAcceptedCurrentClientTerms(currentUser)) {
      setCurrentView("business-terms");
    }
  }, [access.accessState, currentUser]);

  useEffect(() => {
    if (access.accessState !== "ready" || !access.business?.id || !hasAcceptedCurrentClientTerms(currentUser)) {
      return;
    }
    if (currentBusinessLegalRequirements) {
      if (!businessLegalRequirement(currentBusinessLegalRequirements, BUSINESS_TERMS_DOCUMENT_SET)?.accepted) {
        setCurrentView("business-terms");
      }
      return;
    }
    let cancelled = false;
    async function loadLegalState() {
      try {
        const requirements = await loadBusinessLegalRequirements();
        if (
          !cancelled
          && requirements
          && !businessLegalRequirement(requirements, BUSINESS_TERMS_DOCUMENT_SET)?.accepted
        ) {
          setCurrentView("business-terms");
        }
      } catch {
        if (!cancelled) {
          setNotice("No pudimos validar los terminos del negocio.");
        }
      }
    }
    void loadLegalState();
    return () => {
      cancelled = true;
    };
  }, [
    access.accessState,
    access.business?.id,
    currentBusinessLegalRequirements,
    currentUser,
    loadBusinessLegalRequirements
  ]);

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
    acceptBusinessCreditTerms,
    businessLegalRequirements: currentBusinessLegalRequirements,
    view,
    setView,
    consumeViewTransition,
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
    ...support,
    ...awareness,
    openAttentionAlert,
    openBusinessOrder: openBusinessOrderWithAttention,
    openBusinessSupport,
    openSupportTicket: openBusinessSupportTicketWithAttention
  };
}

export type BusinessMiniAppModel = ReturnType<typeof useBusinessMiniAppModel>;
