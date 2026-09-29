import { getTelegramWebApp } from "../../theme/telegramTheme";
import { getPublicEnv } from "../env";

const WALLET_PROBE_PATH = "/business/wallet-probe/";
const CREDIT_PAYMENT_HANDOFF_PATH_PREFIX = "/business/credit-payment/handoff/";
const METAMASK_DAPP_DEEPLINK_BASE = "https://link.metamask.io/dapp/";
const STAGING_ORIGIN = "https://nodo-staging.pages.dev";
const NON_PRODUCTION_ENVIRONMENTS = new Set(["local", "dev", "development", "staging", "test"]);

function parseOrigin(value: string): URL | null {
  try {
    const source = new URL(value);
    if (
      !/^https?:\/\/[^/?#\\\s]+\/?$/i.test(value)
      || source.username
      || source.password
      || source.pathname !== "/"
      || source.search
      || source.hash
      || source.hostname.includes("*")
    ) {
      return null;
    }
    return source;
  } catch {
    return null;
  }
}

function isAllowedProbeOrigin(url: URL): boolean {
  const env = getPublicEnv();
  const environment = env.NEXT_PUBLIC_APP_ENV.trim().toLowerCase();
  const nonProduction = NON_PRODUCTION_ENVIRONMENTS.has(environment)
    || (!environment && process.env.NODE_ENV === "development");
  const configured = env.NEXT_PUBLIC_WALLET_ALLOWLIST.trim();
  const entries = configured ? configured.split(",").map((entry) => entry.trim()) : [];
  const origins = entries.map(parseOrigin);
  // A malformed entry invalidates the whole list, never just that entry.
  if (origins.some((origin) => !origin || origin.protocol !== "https:")) {
    return false;
  }
  if (environment === "production" && origins.some((origin) =>
    origin?.hostname === "nodo-staging.pages.dev" || origin?.hostname.endsWith(".nodo-staging.pages.dev")
  )) {
    return false;
  }
  const allowed = origins.map((origin) => origin!.origin);
  if (!configured && nonProduction) {
    allowed.push(STAGING_ORIGIN);
  }
  if (url.protocol === "https:" && allowed.includes(url.origin)) {
    return true;
  }
  return nonProduction && url.protocol === "http:"
    && (url.hostname === "localhost" || url.hostname === "127.0.0.1" || url.hostname === "[::1]");
}

function rejectOrigin(code: "WALLET_PROBE_ORIGIN_INVALID" | "CREDIT_HANDOFF_ORIGIN_INVALID"): never {
  console.warn(code);
  throw Object.assign(new Error("No se puede abrir MetaMask desde este sitio. Contacta a Soporte NODO."), { code });
}

export function buildMetaMaskWalletProbeDeeplink(origin: string): string {
  const source = parseOrigin(origin);
  if (
    !source
    || !isAllowedProbeOrigin(source)
    || source.username
    || source.password
    || source.pathname !== "/"
    || source.search
    || source.hash
  ) {
    rejectOrigin("WALLET_PROBE_ORIGIN_INVALID");
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
  const source = parseOrigin(origin);
  if (
    !source
    || !isAllowedProbeOrigin(source)
    || source.username
    || source.password
    || source.pathname !== "/"
    || source.search
    || source.hash
  ) {
    rejectOrigin("CREDIT_HANDOFF_ORIGIN_INVALID");
  }
  const target = new URL(`${CREDIT_PAYMENT_HANDOFF_PATH_PREFIX}${handoffToken}/`, source.origin);
  const dappUrl = `${target.host}${target.pathname}`;
  return `${METAMASK_DAPP_DEEPLINK_BASE}${dappUrl}`;
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
