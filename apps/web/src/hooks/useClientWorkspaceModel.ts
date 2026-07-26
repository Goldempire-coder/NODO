"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { ApiClientError, apiRequest } from "../api/client";
import { acceptTerms as acceptUserTerms, saveClientProfile } from "../api/users";
import type { ClientView } from "../constants/clientViews";
import { CURRENT_CLIENT_TERMS_VERSION } from "../constants/legal";
import { configureTelemetryContext } from "../observability/clientTelemetry";
import type { PublicUser } from "../types/auth";
import { useClientChatDisputesModel } from "./workspace/useClientChatDisputesModel";
import { useClientMarketplaceModel } from "./workspace/useClientMarketplaceModel";
import { useClientTelegramMainButton } from "./workspace/useClientTelegramMainButton";
import { usePaymentReportModel } from "./workspace/usePaymentReportModel";
import { useRemitterOrdersModel } from "./workspace/useRemitterOrdersModel";
import { useClientTelegramNativeShell } from "./workspace/useClientTelegramNativeShell";
import { useClientWorkspaceState } from "./workspace/useClientWorkspaceState";
import { useSurfaceSupportModel } from "./useSurfaceSupportModel";

export function useClientWorkspaceModel({
  user,
  token
}: {
  user: PublicUser;
  token: string;
}) {
  const [currentUser, setCurrentUser] = useState(user);
  const state = useClientWorkspaceState(user);
  const view = state.view;
  const setNotice = state.setNotice;
  const setClientView = state.setView;
  const setView = useCallback((nextView: ClientView) => setClientView(nextView), [setClientView]);
  const request = useCallback(
    async (path: string, options: RequestInit = {}) => {
      const headers = new Headers(options.headers || {});
      headers.set("X-NODO-Surface", "client_mini_app");
      try {
        return await apiRequest<any>(path, token, { ...options, headers });
      } catch (error) {
        if (error instanceof ApiClientError && error.code === "TERMS_ACCEPTANCE_REQUIRED") {
          setNotice("Acepta los terminos vigentes para continuar.");
          setClientView("terms");
        }
        throw error;
      }
    },
    [setClientView, setNotice, token]
  );

  const acceptTerms = useCallback(async () => {
    state.setBusy(true);
    try {
      const updatedUser = await acceptUserTerms<PublicUser>(request, CURRENT_CLIENT_TERMS_VERSION);
      setCurrentUser(updatedUser);
      state.setNotice("");
      state.setView(state.clientProfileForm.phone ? "marketplace-search" : "client-profile-setup");
    } catch (error) {
      state.setNotice(error instanceof Error ? error.message : "No pudimos registrar los terminos.");
    } finally {
      state.setBusy(false);
    }
  }, [request, state]);

  const submitClientProfile = useCallback(async () => {
    state.setBusy(true);
    try {
      const updatedUser = await saveClientProfile<PublicUser>(request, state.clientProfileForm);
      setCurrentUser(updatedUser);
      state.setNotice("");
      state.setView("marketplace-search");
    } catch (error) {
      state.setNotice(error instanceof Error ? error.message : "No pudimos guardar tus datos.");
    } finally {
      state.setBusy(false);
    }
  }, [request, state]);

  const context = { ...state, request, user: currentUser };
  const marketplace = useClientMarketplaceModel(context);
  const remitterOrders = useRemitterOrdersModel(context);
  const paymentReport = usePaymentReportModel({ ...context, loadMyOrders: remitterOrders.loadMyOrders });
  const chatDisputes = useClientChatDisputesModel(context);
  const support = useSurfaceSupportModel({ request, setBusy: state.setBusy, setNotice: state.setNotice, initialScope: "client_general" });
  const didWarmClientDataRef = useRef(false);
  const handledOrderDeepLinkRef = useRef(false);
  const prefetchActiveMarketplaceRef = useRef<() => Promise<void>>(async () => undefined);
  const prefetchMyOrdersRef = useRef<() => Promise<void>>(async () => undefined);
  const openOrderDetailRef = useRef<(orderId: string) => Promise<void>>(async () => undefined);
  const mainActionBusy = state.busy || state.creatingOrder || state.submittingPaymentReport;

  prefetchActiveMarketplaceRef.current = marketplace.prefetchActiveMarketplace;
  prefetchMyOrdersRef.current = remitterOrders.prefetchMyOrders;
  openOrderDetailRef.current = remitterOrders.openOrderDetail;

  useEffect(() => {
    configureTelemetryContext(token, "client_mini_app");
    return () => configureTelemetryContext(null, null);
  }, [token]);

  useEffect(() => {
    if (didWarmClientDataRef.current || view === "welcome" || view === "terms" || view === "client-profile-setup") {
      return;
    }
    const timer = window.setTimeout(() => {
      didWarmClientDataRef.current = true;
      void prefetchActiveMarketplaceRef.current();
      void prefetchMyOrdersRef.current();
    }, 250);
    return () => window.clearTimeout(timer);
  }, [view]);

  useEffect(() => {
    if (
      handledOrderDeepLinkRef.current
      || view === "welcome"
      || view === "terms"
      || view === "client-profile-setup"
      || typeof window === "undefined"
    ) {
      return;
    }
    const params = new URLSearchParams(window.location.search);
    const orderId = params.get("order_id");
    if (params.get("view") !== "order-summary" || !orderId) {
      return;
    }
    handledOrderDeepLinkRef.current = true;
    void openOrderDetailRef.current(orderId);
  }, [view]);

  useClientTelegramNativeShell({
    busy: mainActionBusy,
    canGoBack: state.canGoBack,
    goBack: state.goBack,
    view
  });

  useClientTelegramMainButton({
    view,
    createOrder: remitterOrders.createOrder,
    submitPaymentReport: paymentReport.submitPaymentReport,
    busy: mainActionBusy,
    dependencies: [
      state.selectedAd,
      state.orderForm,
      state.paymentReportForm,
      state.paymentEvidence,
      state.pendingPaymentReportId,
      state.selectedOrder
    ]
  });

  return {
    user: currentUser,
    view,
    setView,
    goBack: state.goBack,
    canGoBack: state.canGoBack,
    clientProfileForm: state.clientProfileForm,
    setClientProfileForm: state.setClientProfileForm,
    notice: state.notice,
    setNotice: state.setNotice,
    busy: state.busy,
    searchingMarketplace: state.searchingMarketplace,
    loadingMarketplace: state.loadingMarketplace,
    openingMarketplaceAdId: state.openingMarketplaceAdId,
    searchForm: state.searchForm,
    setSearchForm: state.setSearchForm,
    searchResults: state.searchResults,
    selectedAd: state.selectedAd,
    setSelectedAd: state.setSelectedAd,
    selectedOrder: state.selectedOrder,
    setSelectedOrder: state.setSelectedOrder,
    myOrders: state.myOrders,
    creatingOrder: state.creatingOrder,
    loadingOrders: state.loadingOrders,
    openingOrderId: state.openingOrderId,
    extendingOrderId: state.extendingOrderId,
    cancellingOrderId: state.cancellingOrderId,
    selectedRatingStars: state.selectedRatingStars,
    setSelectedRatingStars: state.setSelectedRatingStars,
    submittingRatingOrderId: state.submittingRatingOrderId,
    chatOrderId: state.chatOrderId,
    chatMessages: state.chatMessages,
    chatCapabilities: state.chatCapabilities,
    chatBody: state.chatBody,
    setChatBody: state.setChatBody,
    chatAttachments: state.chatAttachments,
    openingChatOrderId: state.openingChatOrderId,
    refreshingChat: state.refreshingChat,
    uploadingChatAttachment: state.uploadingChatAttachment,
    sendingChatMessage: state.sendingChatMessage,
    openingOrderDispute: state.openingOrderDispute,
    disputeReason: state.disputeReason,
    setDisputeReason: state.setDisputeReason,
    orderForm: state.orderForm,
    setOrderForm: state.setOrderForm,
    paymentInstructions: state.paymentInstructions,
    paymentEvidence: state.paymentEvidence,
    loadingPaymentInstructions: state.loadingPaymentInstructions,
    uploadingPaymentEvidence: state.uploadingPaymentEvidence,
    submittingPaymentReport: state.submittingPaymentReport,
    paymentReportForm: state.paymentReportForm,
    setPaymentReportForm: state.setPaymentReportForm,
    acceptTerms,
    submitClientProfile,
    searchAds: marketplace.searchAds,
    loadActiveMarketplace: marketplace.loadActiveMarketplace,
    openAdDetail: marketplace.openAdDetail,
    createOrder: remitterOrders.createOrder,
    loadMyOrders: remitterOrders.loadMyOrders,
    openOrderDetail: remitterOrders.openOrderDetail,
    openPaymentInstructions: paymentReport.openPaymentInstructions,
    uploadPaymentEvidence: paymentReport.uploadPaymentEvidence,
    submitPaymentReport: paymentReport.submitPaymentReport,
    extendOrder: remitterOrders.extendOrder,
    cancelOrder: remitterOrders.cancelOrder,
    submitOrderRating: remitterOrders.submitRating,
    openOrderChat: chatDisputes.openOrderChat,
    refreshChat: chatDisputes.refreshChat,
    uploadChatAttachment: chatDisputes.uploadChatAttachment,
    sendChatMessage: chatDisputes.sendChatMessage,
    openOrderDispute: chatDisputes.openOrderDispute,
    supportTickets: support.supportTickets,
    supportFilter: support.supportFilter,
    creatingSupportTicket: support.creatingSupportTicket,
    loadingSupportTickets: support.loadingSupportTickets,
    openingSupportTicketId: support.openingSupportTicketId,
    selectedSupportTicket: support.selectedSupportTicket,
    setSelectedSupportTicket: support.setSelectedSupportTicket,
    supportForm: support.supportForm,
    setSupportForm: support.setSupportForm,
    supportReply: support.supportReply,
    setSupportReply: support.setSupportReply,
    sendingSupportReply: support.sendingSupportReply,
    closingSupportTicketId: support.closingSupportTicketId,
    uploadingSupportAttachment: support.uploadingSupportAttachment,
    loadSupportTickets: support.loadSupportTickets,
    refreshSupportWorkspace: support.refreshSupportWorkspace,
    openSupportTicket: support.openSupportTicket,
    submitSupportTicket: support.submitSupportTicket,
    submitSupportReply: support.submitSupportReply,
    closeOwnSupportTicket: support.closeOwnSupportTicket,
    uploadTicketAttachment: support.uploadTicketAttachment
  };
}

export type ClientWorkspaceModel = ReturnType<typeof useClientWorkspaceModel>;
