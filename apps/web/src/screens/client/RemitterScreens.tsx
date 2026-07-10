import { ClientMarketplaceScreens } from "./ClientMarketplaceScreens";
import { ClientOnboardingScreens } from "./ClientOnboardingScreens";
import { ClientOrderScreens } from "./ClientOrderScreens";
import { ClientPaymentScreens } from "./ClientPaymentScreens";
import type { RemitterScreensModel } from "./RemitterScreens.types";

export function RemitterScreens({ model }: { model: RemitterScreensModel }) {
  return (
    <>
      <ClientOnboardingScreens model={model} />
      <ClientMarketplaceScreens model={model} />
      <ClientOrderScreens model={model} />
      <ClientPaymentScreens model={model} />
    </>
  );
}
