"use client";

import { useCallback, useRef, useState } from "react";
import { coerceClientView, type ClientView } from "../../constants/clientViews";
import { hasAcceptedCurrentClientTerms } from "../../constants/legal";
import type { AdSummary } from "../../types/ads";
import type { PublicUser } from "../../types/auth";
import type { ChatAttachment, ChatCapabilities, ChatMessage } from "../../types/chat";
import type { ClientProfileFormState, SearchFormState } from "../../types/client";
import type { OrderFormState, OrderSummary } from "../../types/orders";
import type { PaymentEvidence, PaymentInstructions, PaymentReportFormState } from "../../types/payments";

const CLIENT_ROOT_VIEWS = new Set<ClientView>([
  "welcome",
  "client-profile-setup",
  "profile",
  "marketplace-search",
  "marketplace-list",
  "my-orders",
  "messages"
]);

function fallbackClientViewFor(view: ClientView): ClientView {
  if (view === "terms") {
    return "welcome";
  }
  if (view === "client-profile-setup") {
    return "terms";
  }
  if (view === "marketplace-detail" || view === "create-order" || view === "order-summary") {
    return "marketplace-search";
  }
  if (view === "payment-instructions" || view === "report-payment") {
    return "my-orders";
  }
  if (view === "order-chat") {
    return "messages";
  }
  return "marketplace-search";
}

export function useClientWorkspaceState(user: PublicUser) {
  const initialView: ClientView = hasAcceptedCurrentClientTerms(user) ? (user.phone ? "marketplace-search" : "client-profile-setup") : "welcome";
  const [view, setCurrentView] = useState<ClientView>(initialView);
  const viewHistoryRef = useRef<ClientView[]>([]);

  const setView = useCallback((nextView: ClientView) => {
    const nextClientView = coerceClientView(nextView);
    setCurrentView((currentView) => {
      if (currentView === nextClientView) {
        return currentView;
      }
      viewHistoryRef.current = [...viewHistoryRef.current, currentView].slice(-20);
      return nextClientView;
    });
  }, []);

  const goBack = useCallback(() => {
    setCurrentView((currentView) => {
      const previousView = viewHistoryRef.current.pop();
      const fallbackView = fallbackClientViewFor(currentView);
      const nextView = previousView && previousView !== currentView ? previousView : fallbackView;
      return nextView === currentView ? currentView : nextView;
    });
  }, []);

  const [clientProfileForm, setClientProfileForm] = useState<ClientProfileFormState>({
    first_name: user.first_name || "",
    phone: user.phone || ""
  });
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const [searchingMarketplace, setSearchingMarketplace] = useState(false);
  const [loadingMarketplace, setLoadingMarketplace] = useState(false);
  const [openingMarketplaceAdId, setOpeningMarketplaceAdId] = useState<string | null>(null);
  const [creatingOrder, setCreatingOrder] = useState(false);
  const [loadingOrders, setLoadingOrders] = useState(false);
  const [openingOrderId, setOpeningOrderId] = useState<string | null>(null);
  const [extendingOrderId, setExtendingOrderId] = useState<string | null>(null);
  const [cancellingOrderId, setCancellingOrderId] = useState<string | null>(null);
  const [loadingPaymentInstructions, setLoadingPaymentInstructions] = useState(false);
  const [uploadingPaymentEvidence, setUploadingPaymentEvidence] = useState(false);
  const [submittingPaymentReport, setSubmittingPaymentReport] = useState(false);
  const [openingChatOrderId, setOpeningChatOrderId] = useState<string | null>(null);
  const [refreshingChat, setRefreshingChat] = useState(false);
  const [uploadingChatAttachment, setUploadingChatAttachment] = useState(false);
  const [sendingChatMessage, setSendingChatMessage] = useState(false);
  const [openingOrderDispute, setOpeningOrderDispute] = useState(false);
  const [searchForm, setSearchForm] = useState<SearchFormState>({
    amount_usd: "50.00",
    payment_method: "zelle",
    delivery_method: "pago_movil_ve",
    sort: "trust"
  });
  const [searchResults, setSearchResults] = useState<AdSummary[]>([]);
  const [selectedAd, setSelectedAd] = useState<AdSummary | null>(null);
  const [selectedOrder, setSelectedOrder] = useState<OrderSummary | null>(null);
  const [myOrders, setMyOrders] = useState<OrderSummary[]>([]);
  const [chatOrderId, setChatOrderId] = useState<string | null>(null);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [chatCapabilities, setChatCapabilities] = useState<ChatCapabilities>({ can_send_message: false, can_open_dispute: false });
  const [chatBody, setChatBody] = useState("");
  const [chatAttachments, setChatAttachments] = useState<ChatAttachment[]>([]);
  const [disputeReason, setDisputeReason] = useState("business_no_payment_confirmation");
  const [orderForm, setOrderForm] = useState<OrderFormState>({
    amount_usd: "50.00",
    bank: "",
    phone: "",
    document: "",
    holder: ""
  });
  const [paymentInstructions, setPaymentInstructions] = useState<PaymentInstructions | null>(null);
  const [paymentEvidence, setPaymentEvidence] = useState<PaymentEvidence | null>(null);
  const [pendingPaymentReportId, setPendingPaymentReportId] = useState<string | null>(null);
  const [paymentReportForm, setPaymentReportForm] = useState<PaymentReportFormState>({
    payment_reference: "",
    payment_sender_name: "",
    payment_sender_account_masked: "",
    payment_amount: "50.00",
    tx_hash: ""
  });

  return {
    view,
    setView,
    goBack,
    canGoBack: !CLIENT_ROOT_VIEWS.has(view),
    clientProfileForm,
    setClientProfileForm,
    notice,
    setNotice,
    busy,
    setBusy,
    searchingMarketplace,
    setSearchingMarketplace,
    loadingMarketplace,
    setLoadingMarketplace,
    openingMarketplaceAdId,
    setOpeningMarketplaceAdId,
    creatingOrder,
    setCreatingOrder,
    loadingOrders,
    setLoadingOrders,
    openingOrderId,
    setOpeningOrderId,
    extendingOrderId,
    setExtendingOrderId,
    cancellingOrderId,
    setCancellingOrderId,
    loadingPaymentInstructions,
    setLoadingPaymentInstructions,
    uploadingPaymentEvidence,
    setUploadingPaymentEvidence,
    submittingPaymentReport,
    setSubmittingPaymentReport,
    openingChatOrderId,
    setOpeningChatOrderId,
    refreshingChat,
    setRefreshingChat,
    uploadingChatAttachment,
    setUploadingChatAttachment,
    sendingChatMessage,
    setSendingChatMessage,
    openingOrderDispute,
    setOpeningOrderDispute,
    searchForm,
    setSearchForm,
    searchResults,
    setSearchResults,
    selectedAd,
    setSelectedAd,
    selectedOrder,
    setSelectedOrder,
    myOrders,
    setMyOrders,
    chatOrderId,
    setChatOrderId,
    chatMessages,
    setChatMessages,
    chatCapabilities,
    setChatCapabilities,
    chatBody,
    setChatBody,
    chatAttachments,
    setChatAttachments,
    disputeReason,
    setDisputeReason,
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
