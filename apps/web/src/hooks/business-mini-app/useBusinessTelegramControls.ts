import { useEffect } from "react";
import type { BusinessMiniAppView } from "../../constants/businessViews";
import type { AdFormState } from "../../types/ads";
import { getTelegramWebApp, setupTelegramViewport } from "../../theme/telegramTheme";

export function useBusinessTelegramControls({
  adForm,
  busy,
  canGoBack,
  createAd,
  goBack,
  view
}: {
  adForm: AdFormState;
  busy: boolean;
  canGoBack: boolean;
  createAd: () => Promise<void>;
  goBack: () => void;
  view: BusinessMiniAppView;
}) {
  useEffect(() => {
    setupTelegramViewport();
  }, []);

  useEffect(() => {
    const backButton = getTelegramWebApp()?.BackButton;
    if (!backButton) {
      return;
    }
    const handleBack = () => goBack();
    if (!canGoBack) {
      backButton.hide?.();
      return;
    }
    backButton.onClick?.(handleBack);
    backButton.show?.();
    return () => {
      backButton.offClick?.(handleBack);
      backButton.hide?.();
    };
  }, [canGoBack, goBack, view]);

  useEffect(() => {
    const mainButton = getTelegramWebApp()?.MainButton;
    if (!mainButton) {
      return;
    }
    if (view !== "create-ad") {
      mainButton.hide?.();
      return;
    }
    const text = "Publicar anuncio";
    mainButton.setText?.(text);
    mainButton.setParams?.({ text, is_active: !busy && Boolean(adForm.payment_method_id), is_visible: true });
    if (busy || !adForm.payment_method_id) {
      mainButton.disable?.();
    } else {
      mainButton.enable?.();
    }
    mainButton.onClick?.(createAd);
    mainButton.show?.();
    return () => {
      mainButton.offClick?.(createAd);
      mainButton.hideProgress?.();
      mainButton.hide?.();
    };
  }, [adForm.payment_method_id, busy, createAd, view]);
}
