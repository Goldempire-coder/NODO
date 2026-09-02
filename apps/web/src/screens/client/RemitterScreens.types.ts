import type { Dispatch, SetStateAction } from "react";
import type { ClientView } from "../../constants/clientViews";
import type { AdSummary } from "../../types/ads";
import type { PublicUser } from "../../types/auth";
import type { ClientProfileFormState, SearchFormState } from "../../types/client";
import type {
  OrderCancelReason,
  OrderFormState,
  OrderSummary
} from "../../types/orders";
import type { PaymentEvidence, PaymentInstructions, PaymentReportFormState } from "../../types/payments";
import type { OperationReportCreateInput } from "../../types/support";
import type {
  SurfaceAttentionCounts,
  SurfaceAttentionItem,
  SurfaceAttentionTruncated
} from "../../types/notifications";

export type RemitterScreensModel = {
  user: PublicUser;
  loggingOut: boolean;
  logout: () => void | Promise<void>;
  view: ClientView;
  setView: (view: ClientView) => void;
  acceptTerms: () => void | Promise<void>;
  submitClientProfile: () => void | Promise<void>;
  clientProfileForm: ClientProfileFormState;
  setClientProfileForm: Dispatch<SetStateAction<ClientProfileFormState>>;
  busy: boolean;
  attentionAlert: SurfaceAttentionItem | null;
  attentionCounts: SurfaceAttentionCounts;
  attentionStale: boolean;
  attentionTruncated: SurfaceAttentionTruncated;
  notice: string;
  searchingMarketplace: boolean;
  loadingMarketplace: boolean;
  loadingMoreMarketplace: boolean;
  openingMarketplaceAdId: string | null;
  searchForm: SearchFormState;
  setSearchForm: Dispatch<SetStateAction<SearchFormState>>;
  searchResults: AdSummary[];
  searchResultsNextCursor: string | null;
  selectedAd: AdSummary | null;
  setSelectedAd: Dispatch<SetStateAction<AdSummary | null>>;
  selectedOrder: OrderSummary | null;
  setSelectedOrder: Dispatch<SetStateAction<OrderSummary | null>>;
  myOrders: OrderSummary[];
  myOrdersNextCursor: string | null;
  creatingOrder: boolean;
  loadingOrders: boolean;
  loadingMoreMyOrders: boolean;
  openingOrderId: string | null;
  extendingOrderId: string | null;
  cancellingOrderId: string | null;
  selectedRatingStars: number;
  setSelectedRatingStars: Dispatch<SetStateAction<number>>;
  submittingRatingOrderId: string | null;
  creatingOperationReportOrderId: string | null;
  operationReportError: { orderId: string; message: string } | null;
  operationReportSuccessOrderId: string | null;
  orderForm: OrderFormState;
  setOrderForm: Dispatch<SetStateAction<OrderFormState>>;
  paymentInstructions: PaymentInstructions | null;
  paymentEvidence: PaymentEvidence | null;
  loadingPaymentInstructions: boolean;
  uploadingPaymentEvidence: boolean;
  submittingPaymentReport: boolean;
  openingChatOrderId: string | null;
  paymentReportForm: PaymentReportFormState;
  setPaymentReportForm: Dispatch<SetStateAction<PaymentReportFormState>>;
  selectMarketplacePaymentMethod: (paymentMethod: SearchFormState["payment_method"]) => void;
  searchAds: () => void | Promise<void>;
  loadActiveMarketplace: (sort?: SearchFormState["sort"]) => void | Promise<void>;
  loadMoreActiveMarketplace: () => void | Promise<void>;
  openAdDetail: (adId: string) => void | Promise<void>;
  createOrder: () => void | Promise<void>;
  loadMyOrders: (targetView?: "my-orders" | "messages") => void | Promise<void>;
  loadMoreMyOrders: () => void | Promise<void>;
  openOrderDetail: (orderId: string) => void | Promise<void>;
  openClientSupport: () => void;
  openPaymentReport: (orderId: string) => void | Promise<boolean>;
  uploadPaymentEvidence: (file: File | null) => void | Promise<void>;
  submitPaymentReport: () => void | Promise<void>;
  extendOrder: (orderId: string) => void | Promise<void>;
  cancelOrder: (
    orderId: string,
    reason: OrderCancelReason,
    paymentNotSentConfirmed: boolean
  ) => Promise<boolean>;
  submitOrderRating: (orderId: string) => void | Promise<void>;
  submitOperationReport: (orderId: string, input: OperationReportCreateInput) => Promise<boolean>;
  openOrderChat: (orderId: string) => void | Promise<boolean>;
};

export function displayBusinessName(ad: AdSummary | null): string {
  const name = ad?.business?.business_name?.trim();
  if (!name) {
    return "Negocio registrado";
  }
  if (name.length > 34 || name.includes("_smoke_") || name.includes("concurrency")) {
    return "Negocio registrado";
  }
  return name;
}
