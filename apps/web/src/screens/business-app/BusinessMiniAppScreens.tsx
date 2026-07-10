import type { BusinessMiniAppModel } from "../../hooks/useBusinessMiniAppModel";
import { BusinessAccessPanel } from "./BusinessAccessPanel";
import { ArchivedAdsScreen, CreateAdScreen, MyAdsScreen, PaymentMethodsScreen } from "./BusinessAdsScreens";
import { BusinessChatScreen } from "./BusinessChatScreen";
import { BusinessDashboardScreen } from "./BusinessDashboardScreen";
import { BuyCreditsScreen, CreditPaymentPendingScreen, CreditsDashboardScreen, CreditsLedgerScreen, ReferralProgramScreen } from "./BusinessCreditsScreens";
import { BusinessOrderDetailScreen, IncomingOrdersScreen } from "./BusinessOrdersScreens";
import { BusinessSettingsScreen } from "./BusinessSettingsScreen";

export function BusinessMiniAppScreens({ model }: { model: BusinessMiniAppModel }) {
  if (model.accessState !== "ready") {
    return <BusinessAccessPanel model={model} />;
  }

  switch (model.view) {
    case "create-ad":
      return <CreateAdScreen model={model} />;
    case "my-ads":
      return <MyAdsScreen model={model} />;
    case "archived-ads":
      return <ArchivedAdsScreen model={model} />;
    case "payment-methods":
      return <PaymentMethodsScreen model={model} />;
    case "business-orders":
      return <IncomingOrdersScreen model={model} />;
    case "business-order-detail":
      return <BusinessOrderDetailScreen model={model} />;
    case "business-chat":
      return <BusinessChatScreen model={model} />;
    case "credits-dashboard":
      return <CreditsDashboardScreen model={model} />;
    case "buy-credits":
      return <BuyCreditsScreen model={model} />;
    case "credit-payment-pending":
      return <CreditPaymentPendingScreen model={model} />;
    case "credits-ledger":
      return <CreditsLedgerScreen model={model} />;
    case "referrals":
      return <ReferralProgramScreen model={model} />;
    case "business-settings":
      return <BusinessSettingsScreen model={model} />;
    case "business-dashboard":
    default:
      return <BusinessDashboardScreen model={model} />;
  }
}
