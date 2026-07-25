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

    const updateViewportHeight = () => {
      const currentHeight = visualViewport?.height || window.innerHeight;
      root.style.setProperty("--nodo-viewport-height", `${Math.round(currentHeight)}px`);
      if (!isEditableElement(document.activeElement)) {
        fullViewportHeight = Math.max(fullViewportHeight, currentHeight);
      }
      setKeyboardActive(fullViewportHeight - currentHeight > 120 || isEditableElement(document.activeElement));
    };

    const updateAfterFocusSettles = () => {
      window.setTimeout(updateViewportHeight, 120);
      window.setTimeout(updateViewportHeight, 300);
    };

    updateViewportHeight();
    window.addEventListener("resize", updateViewportHeight);
    document.addEventListener("focusin", updateAfterFocusSettles);
    document.addEventListener("focusout", updateAfterFocusSettles);
    visualViewport?.addEventListener("resize", updateViewportHeight);
    visualViewport?.addEventListener("scroll", updateViewportHeight);
    return () => {
      window.removeEventListener("resize", updateViewportHeight);
      document.removeEventListener("focusin", updateAfterFocusSettles);
      document.removeEventListener("focusout", updateAfterFocusSettles);
      visualViewport?.removeEventListener("resize", updateViewportHeight);
      visualViewport?.removeEventListener("scroll", updateViewportHeight);
    };
  }, []);

  return keyboardActive;
}
