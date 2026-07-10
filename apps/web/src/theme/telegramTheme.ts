declare global {
  interface Window {
    Telegram?: {
      WebApp?: {
        initData?: string;
        themeParams?: Record<string, string>;
        colorScheme?: "light" | "dark";
        ready?: () => void;
        expand?: () => void;
        disableVerticalSwipes?: () => void;
        enableClosingConfirmation?: () => void;
        disableClosingConfirmation?: () => void;
        onEvent?: (eventType: string, callback: () => void) => void;
        offEvent?: (eventType: string, callback: () => void) => void;
        HapticFeedback?: {
          impactOccurred?: (style: "light" | "medium" | "heavy" | "rigid" | "soft") => void;
          notificationOccurred?: (type: "error" | "success" | "warning") => void;
          selectionChanged?: () => void;
        };
        BackButton?: {
          show?: () => void;
          hide?: () => void;
          onClick?: (callback: () => void) => void;
          offClick?: (callback: () => void) => void;
        };
        MainButton?: {
          setText?: (text: string) => void;
          setParams?: (params: { text?: string; is_active?: boolean; is_visible?: boolean }) => void;
          show?: () => void;
          hide?: () => void;
          enable?: () => void;
          disable?: () => void;
          showProgress?: (leaveActive?: boolean) => void;
          hideProgress?: () => void;
          onClick?: (callback: () => void) => void;
          offClick?: (callback: () => void) => void;
        };
      };
    };
  }
}

export function applyFallbackThemeParams() {
  const themeParams = window.Telegram?.WebApp?.themeParams;
  if (!themeParams) {
    return;
  }

  const root = document.documentElement;
  const mapping: Record<string, string> = {
    bg_color: "--tg-theme-bg-color",
    text_color: "--tg-theme-text-color",
    hint_color: "--tg-theme-hint-color",
    button_color: "--tg-theme-button-color",
    button_text_color: "--tg-theme-button-text-color",
    secondary_bg_color: "--tg-theme-secondary-bg-color"
  };

  Object.entries(mapping).forEach(([telegramKey, cssVar]) => {
    const value = themeParams[telegramKey];
    if (value) {
      root.style.setProperty(cssVar, value);
    }
  });
}

export function getTelegramWebApp() {
  if (typeof window === "undefined") {
    return undefined;
  }
  return window.Telegram?.WebApp;
}

export function setupTelegramViewport() {
  const webApp = getTelegramWebApp();
  if (!webApp) {
    return;
  }
  webApp.ready?.();
  webApp.expand?.();
  webApp.disableVerticalSwipes?.();
}

export async function readTelegramInitData(): Promise<string | null> {
  const localDevInitData =
    typeof window !== "undefined" && ["localhost", "127.0.0.1"].includes(window.location.hostname)
      ? new URLSearchParams(window.location.search).get("tgWebAppData")
      : null;
  if (localDevInitData) {
    return localDevInitData;
  }

  try {
    const sdk = await import("@telegram-apps/sdk");
    try {
      sdk.mountThemeParams();
      sdk.bindThemeParamsCssVars();
    } catch {
      applyFallbackThemeParams();
    }
    const raw = sdk.retrieveRawInitData();
    return raw || window.Telegram?.WebApp?.initData || null;
  } catch {
    applyFallbackThemeParams();
    return window.Telegram?.WebApp?.initData || null;
  }
}
