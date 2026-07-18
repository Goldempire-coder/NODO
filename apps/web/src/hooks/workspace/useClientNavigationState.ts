"use client";

import { useCallback, useRef, useState } from "react";
import { coerceClientView, type ClientView } from "../../constants/clientViews";
import { hasAcceptedCurrentClientTerms } from "../../constants/legal";
import type { PublicUser } from "../../types/auth";

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

export function useClientNavigationState(user: PublicUser) {
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

  return {
    canGoBack: !CLIENT_ROOT_VIEWS.has(view),
    goBack,
    setView,
    view
  };
}
