declare global {
  interface Window {
    Telegram?: {
      WebApp?: {
        initData?: string;
        themeParams?: Record<string, string>;
        colorScheme?: "light" | "dark";
        ready?: () => void;
        expand?: () => void;
        enableVerticalSwipes?: () => void;
        enableClosingConfirmation?: () => void;
        disableClosingConfirmation?: () => void;
        openLink?: (url: string, options?: { try_instant_view?: boolean }) => void;
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
  try {
    webApp.ready?.();
  } catch {
    // Telegram native helpers must never block authentication.
  }
  try {
    webApp.expand?.();
  } catch {
    // Telegram native helpers must never block authentication.
  }
  try {
    webApp.enableVerticalSwipes?.();
  } catch {
    // Telegram native helpers must never block authentication.
  }
}

export function notifyTelegram(type: "error" | "success" | "warning") {
  try {
    getTelegramWebApp()?.HapticFeedback?.notificationOccurred?.(type);
  } catch {
    // Haptics are optional and can be unsupported in some Telegram WebViews.
  }
}

function normalizeTelegramInitData(value: string | null | undefined): string | null {
  const trimmed = value?.trim();
  if (!trimmed) {
    return null;
  }
  if (trimmed.includes("hash=")) {
    return trimmed;
  }
  try {
    const decoded = decodeURIComponent(trimmed);
    return decoded.includes("hash=") ? decoded : null;
  } catch {
    return null;
  }
}

function readTelegramInitDataFromUrl(): string | null {
  if (typeof window === "undefined") {
    return null;
  }

  const fromSearch = normalizeTelegramInitData(new URLSearchParams(window.location.search).get("tgWebAppData"));
  if (fromSearch) {
    return fromSearch;
  }

  const hash = window.location.hash.replace(/^#/, "").replace(/^\?/, "");
  const fromHashParam = normalizeTelegramInitData(new URLSearchParams(hash).get("tgWebAppData"));
  if (fromHashParam) {
    return fromHashParam;
  }

  return normalizeTelegramInitData(hash);
}

async function waitForTelegramInitData(): Promise<string | null> {
  for (let attempt = 0; attempt < 8; attempt += 1) {
    const direct = normalizeTelegramInitData(window.Telegram?.WebApp?.initData);
    if (direct) {
      return direct;
    }
    const fromUrl = readTelegramInitDataFromUrl();
    if (fromUrl) {
      return fromUrl;
    }
    await new Promise((resolve) => window.setTimeout(resolve, 75));
  }
  return null;
}

export async function readTelegramInitData(): Promise<string | null> {
  if (typeof window === "undefined") {
    return null;
  }

  const initial = await waitForTelegramInitData();
  if (initial) {
    return initial;
  }

  try {
    const sdk = await import("@telegram-apps/sdk");
    try {
      sdk.mountThemeParams();
      sdk.bindThemeParamsCssVars();
    } catch {
      applyFallbackThemeParams();
    }
    return normalizeTelegramInitData(sdk.retrieveRawInitData()) || normalizeTelegramInitData(window.Telegram?.WebApp?.initData);
  } catch {
    applyFallbackThemeParams();
    return normalizeTelegramInitData(window.Telegram?.WebApp?.initData) || readTelegramInitDataFromUrl();
  }
}
