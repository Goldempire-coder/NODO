"use client";

import { useCallback, useEffect } from "react";
import type { ClientView } from "../../constants/clientViews";
import { getTelegramWebApp } from "../../theme/telegramTheme";

export function useClientTelegramMainButton({
  view,
  createOrder,
  submitPaymentReport,
  busy,
  dependencies
}: {
  view: ClientView;
  createOrder: () => void | Promise<void>;
  submitPaymentReport: () => void | Promise<void>;
  busy: boolean;
  dependencies: unknown[];
}) {
  const handlePrimaryAction = useCallback(() => {
    getTelegramWebApp()?.HapticFeedback?.impactOccurred?.("light");
    if (view === "create-order") {
      void createOrder();
    }
    if (view === "report-payment") {
      void submitPaymentReport();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [view, ...dependencies]);

  useEffect(() => {
    const mainButton = getTelegramWebApp()?.MainButton;
    if (!mainButton) {
      return;
    }
    if (view !== "create-order" && view !== "report-payment") {
      mainButton.hide?.();
      return;
    }
    const text = view === "create-order" ? "Crear orden" : "Confirmar y enviar";
    mainButton.setText?.(text);
    mainButton.setParams?.({ text, is_active: !busy, is_visible: true });
    if (busy) {
      mainButton.disable?.();
      mainButton.showProgress?.(false);
    } else {
      mainButton.hideProgress?.();
      mainButton.enable?.();
    }
    mainButton.onClick?.(handlePrimaryAction);
    mainButton.show?.();
    return () => {
      mainButton.offClick?.(handlePrimaryAction);
      mainButton.hideProgress?.();
      mainButton.hide?.();
    };
  }, [busy, view, handlePrimaryAction]);
}

