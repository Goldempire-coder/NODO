"use client";

import { useEffect, useState } from "react";

function isEditableElement(element: Element | null) {
  if (!(element instanceof HTMLElement)) {
    return false;
  }
  return element.matches("input, textarea, select, [contenteditable='true']");
}

export function useMobileKeyboardViewport() {
  const [keyboardActive, setKeyboardActive] = useState(false);

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }
    const root = document.documentElement;
    const visualViewport = window.visualViewport;
    let fullViewportHeight = visualViewport?.height || window.innerHeight;
    let animationFrame: number | null = null;

    const updateViewportHeight = () => {
      const currentHeight = visualViewport?.height || window.innerHeight;
      root.style.setProperty("--nodo-viewport-height", `${Math.round(currentHeight)}px`);
      if (!isEditableElement(document.activeElement)) {
        fullViewportHeight = currentHeight;
      }
      setKeyboardActive(
        isEditableElement(document.activeElement) &&
        fullViewportHeight - currentHeight > 120
      );
    };

    const scheduleViewportUpdate = () => {
      if (animationFrame !== null) {
        return;
      }
      animationFrame = window.requestAnimationFrame(() => {
        animationFrame = null;
        updateViewportHeight();
      });
    };

    const resetViewportBaseline = () => {
      fullViewportHeight = visualViewport?.height || window.innerHeight;
      scheduleViewportUpdate();
    };

    updateViewportHeight();
    window.addEventListener("resize", scheduleViewportUpdate);
    window.addEventListener("orientationchange", resetViewportBaseline);
    document.addEventListener("focusin", scheduleViewportUpdate);
    document.addEventListener("focusout", scheduleViewportUpdate);
    visualViewport?.addEventListener("resize", scheduleViewportUpdate);
    return () => {
      if (animationFrame !== null) {
        window.cancelAnimationFrame(animationFrame);
      }
      window.removeEventListener("resize", scheduleViewportUpdate);
      window.removeEventListener("orientationchange", resetViewportBaseline);
      document.removeEventListener("focusin", scheduleViewportUpdate);
      document.removeEventListener("focusout", scheduleViewportUpdate);
      visualViewport?.removeEventListener("resize", scheduleViewportUpdate);
    };
  }, []);

  return keyboardActive;
}
