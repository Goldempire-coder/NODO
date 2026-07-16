"use client";

import { useCallback, useEffect, useRef } from "react";
import { apiRequest } from "../api/client";
import { acceptTerms as acceptUserTerms, saveClientProfile } from "../api/users";
import type { ClientView } from "../constants/clientViews";
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
  const state = useClientWorkspaceState(user);
  const view = state.view;
  const setView = useCallback((nextView: ClientView) => state.setView(nextView), [state]);
  const request = useCallback(
    async (path: string, options: RequestInit = {}) => apiRequest<any>(path, token, options),
    [token]
  );

  const acceptTerms = useCallback(async () => {
    state.setBusy(true);
    try {
      await acceptUserTerms(request, "2026-07-06");
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
      await saveClientProfile(request, state.clientProfileForm);
      state.setNotice("");
      state.setView("marketplace-search");
    } catch (error) {
      state.setNotice(error instanceof Error ? error.message : "No pudimos guardar tus datos.");
    } finally {
      state.setBusy(false);
    }
  }, [request, state]);

  const context = { ...state, request, user };
  const marketplace = useClientMarketplaceModel(context);
  const remitterOrders = useRemitterOrdersModel(context);
  const paymentReport = usePaymentReportModel({ ...context, loadMyOrders: remitterOrders.loadMyOrders });
  const chatDisputes = useClientChatDisputesModel(context);
  const support = useSurfaceSupportModel({ request, setBusy: state.setBusy, setNotice: state.setNotice });
  const didWarmClientDataRef = useRef(false);

  useEffect(() => {
    if (didWarmClientDataRef.current || view === "welcome" || view === "terms" || view === "client-profile-setup") {
      return;
    }
    didWarmClientDataRef.current = true;
    const timer = window.setTimeout(() => {
      void marketplace.prefetchActiveMarketplace();
      void remitterOrders.prefetchMyOrders();
    }, 250);
    return () => window.clearTimeout(timer);
  }, [marketplace, remitterOrders, view]);

  useClientTelegramNativeShell({
    busy: state.busy,
    canGoBack: state.canGoBack,
    goBack: state.goBack,
    view
  });

  useClientTelegramMainButton({
    view,
    createOrder: remitterOrders.createOrder,
    submitPaymentReport: paymentReport.submitPaymentReport,
    busy: state.busy,
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
    user,
    view,
    setView,
    goBack: state.goBack,
    canGoBack: state.canGoBack,
    clientProfileForm: state.clientProfileForm,
    setClientProfileForm: state.setClientProfileForm,
    notice: state.notice,
    setNotice: state.setNotice,
    busy: state.busy,
    searchForm: state.searchForm,
    setSearchForm: state.setSearchForm,
    searchResults: state.searchResults,
    selectedAd: state.selectedAd,
    setSelectedAd: state.setSelectedAd,
    selectedOrder: state.selectedOrder,
    setSelectedOrder: state.setSelectedOrder,
    myOrders: state.myOrders,
    chatOrderId: state.chatOrderId,
    chatMessages: state.chatMessages,
    chatCapabilities: state.chatCapabilities,
    chatBody: state.chatBody,
    setChatBody: state.setChatBody,
    chatAttachments: state.chatAttachments,
    disputeReason: state.disputeReason,
    setDisputeReason: state.setDisputeReason,
    orderForm: state.orderForm,
    setOrderForm: state.setOrderForm,
    paymentInstructions: state.paymentInstructions,
    paymentEvidence: state.paymentEvidence,
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
    openOrderChat: chatDisputes.openOrderChat,
    refreshChat: chatDisputes.refreshChat,
    uploadChatAttachment: chatDisputes.uploadChatAttachment,
    sendChatMessage: chatDisputes.sendChatMessage,
    openOrderDispute: chatDisputes.openOrderDispute,
    supportTickets: support.supportTickets,
    selectedSupportTicket: support.selectedSupportTicket,
    setSelectedSupportTicket: support.setSelectedSupportTicket,
    supportForm: support.supportForm,
    setSupportForm: support.setSupportForm,
    supportReply: support.supportReply,
    setSupportReply: support.setSupportReply,
    loadSupportTickets: support.loadSupportTickets,
    openSupportTicket: support.openSupportTicket,
    submitSupportTicket: support.submitSupportTicket,
    submitSupportReply: support.submitSupportReply,
    uploadTicketAttachment: support.uploadTicketAttachment
  };
}

export type ClientWorkspaceModel = ReturnType<typeof useClientWorkspaceModel>;
