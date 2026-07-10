"use client";

import { useEffect, useMemo, useRef } from "react";
import type { ClientView } from "../../constants/clientViews";
import { getTelegramWebApp, setupTelegramViewport } from "../../theme/telegramTheme";

const CLIENT_DIRTY_VIEWS = new Set<ClientView>(["create-order", "report-payment"]);

export function useClientTelegramNativeShell({
  busy,
  canGoBack,
  goBack,
  view
}: {
  busy: boolean;
  canGoBack: boolean;
  goBack: () => void;
  view: ClientView;
}) {
  const currentViewRef = useRef(view);
  const shouldShowBack = useMemo(() => canGoBack, [canGoBack]);

  useEffect(() => {
    setupTelegramViewport();
  }, []);

  useEffect(() => {
    const webApp = getTelegramWebApp();
    if (!webApp) {
      currentViewRef.current = view;
      return;
    }
    if (currentViewRef.current !== view) {
      currentViewRef.current = view;
      webApp.HapticFeedback?.selectionChanged?.();
    }
  }, [view]);

  useEffect(() => {
    const backButton = getTelegramWebApp()?.BackButton;
    if (!backButton) {
      return;
    }
    const handleBack = () => goBack();
    if (!shouldShowBack) {
      backButton.hide?.();
      return;
    }
    backButton.onClick?.(handleBack);
    backButton.show?.();
    return () => {
      backButton.offClick?.(handleBack);
      backButton.hide?.();
    };
  }, [goBack, shouldShowBack, view]);

  useEffect(() => {
    const webApp = getTelegramWebApp();
    if (!webApp) {
      return;
    }
    if (CLIENT_DIRTY_VIEWS.has(view) && !busy) {
      webApp.enableClosingConfirmation?.();
    } else {
      webApp.disableClosingConfirmation?.();
    }
    return () => {
      webApp.disableClosingConfirmation?.();
    };
  }, [busy, view]);
}
