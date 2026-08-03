"use client";

import { useRef, useState } from "react";
import type { AdSummary } from "../../types/ads";
import type { PublicUser } from "../../types/auth";
import type { ChatAttachment, ChatCapabilities, ChatMessage } from "../../types/chat";
import type { ClientProfileFormState, SearchFormState } from "../../types/client";
import type { OrderFormState, OrderSummary } from "../../types/orders";
import type { PaymentEvidence, PaymentInstructions, PaymentReportFormState } from "../../types/payments";
import { useClientActionState } from "./useClientActionState";
import { useClientNavigationState } from "./useClientNavigationState";

export function emptyPaymentReportForm(paymentAmount = ""): PaymentReportFormState {
  return {
    payment_reference: "",
    payment_sender_name: "",
    payment_sender_account_masked: "",
    payment_amount: paymentAmount,
    tx_hash: ""
  };
}

export function useClientWorkspaceState(user: PublicUser) {
  const navigation = useClientNavigationState(user);
  const actions = useClientActionState();
  const [clientProfileForm, setClientProfileForm] = useState<ClientProfileFormState>({
    first_name: user.first_name || "",
    phone: user.phone || ""
  });
  const [notice, setNotice] = useState("");
  const [searchForm, setSearchForm] = useState<SearchFormState>({
    amount_usd: "50.00",
    payment_method: "zelle",
    delivery_method: "pago_movil_ve",
    sort: "rate"
  });
  const [searchResults, setSearchResults] = useState<AdSummary[]>([]);
  const [selectedAd, setSelectedAd] = useState<AdSummary | null>(null);
  const [selectedOrder, setSelectedOrder] = useState<OrderSummary | null>(null);
  const [selectedRatingStars, setSelectedRatingStars] = useState(0);
  const [myOrders, setMyOrders] = useState<OrderSummary[]>([]);
  const [chatOrderId, setChatOrderId] = useState<string | null>(null);
  const paymentOrderContextRef = useRef<string | null>(null);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [chatCapabilities, setChatCapabilities] = useState<ChatCapabilities>({
    can_send_message: false,
    can_open_dispute: false,
    can_share_zelle: false,
    payment_details_shared: false,
    can_report_payment: false,
    receiver_details_shared: false,
    can_share_receiver_details: false,
    can_reveal_receiver_details: false,
    receiver_details_required: false,
    can_confirm_received: false,
    can_confirm_payment: false,
    can_mark_delivered: false
  });
  const [chatBody, setChatBody] = useState("");
  const [chatAttachments, setChatAttachments] = useState<ChatAttachment[]>([]);
  const [orderForm, setOrderForm] = useState<OrderFormState>({
    amount_usd: "50.00"
  });
  const [paymentInstructions, setPaymentInstructions] = useState<PaymentInstructions | null>(null);
  const [paymentEvidence, setPaymentEvidence] = useState<PaymentEvidence | null>(null);
  const [pendingPaymentReportId, setPendingPaymentReportId] = useState<string | null>(null);
  const [paymentReportForm, setPaymentReportForm] = useState<PaymentReportFormState>(emptyPaymentReportForm("50.00"));

  return {
    view: navigation.view,
    setView: navigation.setView,
    goBack: navigation.goBack,
    canGoBack: navigation.canGoBack,
    clientProfileForm,
    setClientProfileForm,
    notice,
    setNotice,
    busy: actions.busy,
    setBusy: actions.setBusy,
    searchingMarketplace: actions.searchingMarketplace,
    setSearchingMarketplace: actions.setSearchingMarketplace,
    loadingMarketplace: actions.loadingMarketplace,
    setLoadingMarketplace: actions.setLoadingMarketplace,
    openingMarketplaceAdId: actions.openingMarketplaceAdId,
    setOpeningMarketplaceAdId: actions.setOpeningMarketplaceAdId,
    creatingOrder: actions.creatingOrder,
    setCreatingOrder: actions.setCreatingOrder,
    loadingOrders: actions.loadingOrders,
    setLoadingOrders: actions.setLoadingOrders,
    openingOrderId: actions.openingOrderId,
    setOpeningOrderId: actions.setOpeningOrderId,
    extendingOrderId: actions.extendingOrderId,
    setExtendingOrderId: actions.setExtendingOrderId,
    cancellingOrderId: actions.cancellingOrderId,
    setCancellingOrderId: actions.setCancellingOrderId,
    loadingPaymentInstructions: actions.loadingPaymentInstructions,
    setLoadingPaymentInstructions: actions.setLoadingPaymentInstructions,
    uploadingPaymentEvidence: actions.uploadingPaymentEvidence,
    setUploadingPaymentEvidence: actions.setUploadingPaymentEvidence,
    submittingPaymentReport: actions.submittingPaymentReport,
    setSubmittingPaymentReport: actions.setSubmittingPaymentReport,
    openingChatOrderId: actions.openingChatOrderId,
    setOpeningChatOrderId: actions.setOpeningChatOrderId,
    refreshingChat: actions.refreshingChat,
    setRefreshingChat: actions.setRefreshingChat,
    uploadingChatAttachment: actions.uploadingChatAttachment,
    setUploadingChatAttachment: actions.setUploadingChatAttachment,
    sendingChatMessage: actions.sendingChatMessage,
    setSendingChatMessage: actions.setSendingChatMessage,
    submittingRatingOrderId: actions.submittingRatingOrderId,
    setSubmittingRatingOrderId: actions.setSubmittingRatingOrderId,
    searchForm,
    setSearchForm,
    searchResults,
    setSearchResults,
    selectedAd,
    setSelectedAd,
    selectedOrder,
    setSelectedOrder,
    selectedRatingStars,
    setSelectedRatingStars,
    myOrders,
    setMyOrders,
    chatOrderId,
    setChatOrderId,
    paymentOrderContextRef,
    chatMessages,
    setChatMessages,
    chatCapabilities,
    setChatCapabilities,
    chatBody,
    setChatBody,
    chatAttachments,
    setChatAttachments,
    orderForm,
    setOrderForm,
    paymentInstructions,
    setPaymentInstructions,
    paymentEvidence,
    setPaymentEvidence,
    pendingPaymentReportId,
    setPendingPaymentReportId,
    paymentReportForm,
    setPaymentReportForm
  };
}

export type ClientWorkspaceState = ReturnType<typeof useClientWorkspaceState>;
