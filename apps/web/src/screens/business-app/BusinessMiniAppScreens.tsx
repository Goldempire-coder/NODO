import type { BusinessMiniAppModel } from "../../hooks/useBusinessMiniAppModel";
import { BusinessAccessPanel } from "./BusinessAccessPanel";
import { ArchivedAdsScreen, CreateAdScreen, MyAdsScreen, PaymentMethodsScreen } from "./BusinessAdsScreens";
import { BusinessChatScreen } from "./BusinessChatScreen";
import { BusinessDashboardScreen } from "./BusinessDashboardScreen";
import { BuyCreditsScreen, CreditPaymentPendingScreen, CreditsDashboardScreen, ReferralProgramScreen } from "./BusinessCreditsScreens";
import { BusinessOrderDetailScreen, IncomingOrdersScreen } from "./BusinessOrdersScreens";
import { BusinessPinScreen } from "./BusinessPinScreen";
import { BusinessCreditTermsScreen, BusinessRulesScreen, BusinessSettingsScreen, BusinessTermsScreen } from "./BusinessSettingsScreen";
import { BusinessSupportScreen } from "./BusinessSupportScreen";

export function BusinessMiniAppScreens({ model }: { model: BusinessMiniAppModel }) {
  if (model.accessState !== "ready") {
    return <BusinessAccessPanel model={model} />;
  }

  switch (model.view) {
    case "business-pin":
      return <BusinessPinScreen model={model} />;
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
    case "referrals":
      return <ReferralProgramScreen model={model} />;
    case "business-settings":
      return <BusinessSettingsScreen model={model} />;
    case "business-terms":
      return <BusinessTermsScreen model={model} />;
    case "business-credit-terms":
      return <BusinessCreditTermsScreen model={model} />;
    case "business-rules":
      return <BusinessRulesScreen />;
    case "business-support":
      return <BusinessSupportScreen model={model} />;
    case "business-dashboard":
    default:
      return <BusinessDashboardScreen model={model} />;
  }
}
