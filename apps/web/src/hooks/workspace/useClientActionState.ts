"use client";

import { useState } from "react";

export function useClientActionState() {
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
  const [submittingRatingOrderId, setSubmittingRatingOrderId] = useState<string | null>(null);

  return {
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
    submittingRatingOrderId,
    setSubmittingRatingOrderId
  };
}
