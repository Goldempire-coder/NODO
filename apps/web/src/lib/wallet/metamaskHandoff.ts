import { getTelegramWebApp } from "../../theme/telegramTheme";

const WALLET_PROBE_PATH = "/business/wallet-probe";
const CREDIT_PAYMENT_PATH = "/business/credit-payment";
const METAMASK_DAPP_DEEPLINK_BASE = "https://link.metamask.io/dapp/";
const NODO_PROBE_HTTPS_ORIGINS = new Set(["https://nodo-staging.pages.dev"]);

function isAllowedProbeOrigin(url: URL): boolean {
  if (url.protocol === "https:" && NODO_PROBE_HTTPS_ORIGINS.has(url.origin)) {
    return true;
  }
  return url.protocol === "http:"
    && (url.hostname === "localhost" || url.hostname === "127.0.0.1" || url.hostname === "[::1]");
}

export function buildMetaMaskWalletProbeDeeplink(origin: string): string {
  const source = new URL(origin);
  if (
    !isAllowedProbeOrigin(source)
    || source.username
    || source.password
    || source.pathname !== "/"
    || source.search
    || source.hash
  ) {
    throw new Error("WALLET_PROBE_ORIGIN_INVALID");
  }
  const probe = new URL(WALLET_PROBE_PATH, source.origin);
  return `${METAMASK_DAPP_DEEPLINK_BASE}${probe.host}${probe.pathname}`;
}

export function openMetaMaskWalletProbe(): void {
  if (typeof window === "undefined") {
    return;
  }
  const deeplink = buildMetaMaskWalletProbeDeeplink(window.location.origin);
  const telegramWebApp = getTelegramWebApp();
  if (telegramWebApp?.openLink) {
    try {
      telegramWebApp.openLink(deeplink);
      return;
    } catch {
      // Fall through to normal navigation when the Telegram helper is unavailable.
    }
  }
  window.location.assign(deeplink);
}

export function buildMetaMaskCreditHandoffDeeplink(origin: string, handoffToken: string): string {
  if (!/^[A-Za-z0-9_-]{43}$/.test(handoffToken)) {
    throw new Error("CREDIT_HANDOFF_TOKEN_INVALID");
  }
  const source = new URL(origin);
  if (
    !isAllowedProbeOrigin(source)
    || source.username
    || source.password
    || source.pathname !== "/"
    || source.search
    || source.hash
  ) {
    throw new Error("CREDIT_HANDOFF_ORIGIN_INVALID");
  }
  const target = new URL(CREDIT_PAYMENT_PATH, source.origin);
  target.hash = `handoff=${handoffToken}`;
  const dappUrl = `${target.host}${target.pathname}${target.hash}`;
  return `${METAMASK_DAPP_DEEPLINK_BASE}${encodeURIComponent(dappUrl)}`;
}

export function openMetaMaskCreditHandoff(handoffToken: string): void {
  if (typeof window === "undefined") {
    return;
  }
  const deeplink = buildMetaMaskCreditHandoffDeeplink(window.location.origin, handoffToken);
  const telegramWebApp = getTelegramWebApp();
  if (telegramWebApp?.openLink) {
    try {
      telegramWebApp.openLink(deeplink);
      return;
    } catch {
      // Fall through to normal navigation when Telegram cannot open the link.
    }
  }
  window.location.assign(deeplink);
}
