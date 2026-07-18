import { getPublicEnv, resolveApiUrl } from "../lib/env";

const CORRELATION_STORAGE_KEY = "nodo_observability_correlation_id";
const SESSION_STORAGE_KEY = "nodo_observability_session_id";
const MAX_BREADCRUMBS = 50;
const OBSERVABILITY_ENDPOINT = "/api/v1/observability/events";
const SLOW_SENSITIVE_ACTION_THRESHOLD_MS = 1500;
const SLOW_SCREEN_TRANSITION_THRESHOLD_MS = 1000;

const sensitiveKeyFragments = [
  "authorization",
  "cookie",
  "password",
  "secret",
  "token",
  "pin",
  "otp",
  "wallet",
  "zelle",
  "email",
  "phone",
  "account",
  "storage",
  "private",
  "seed",
  "mnemonic",
  "tx",
  "hash",
  "url"
];

type Breadcrumb = {
  timestamp: string;
  event_type: string;
  screen?: string;
  previous_screen?: string;
  action?: string;
  route_template?: string;
  status_code?: number;
  error_code?: string;
  duration_ms?: number;
};

type TelemetrySurface = "client_mini_app" | "business_mini_app" | "admin_web";

export type ObservedRequestContext = {
  headers: Headers;
  method: string;
  routeTemplate: string;
  requestId: string;
  correlationId: string;
  operationId: string;
  surface: string | null;
  startedAt: number;
};

let breadcrumbs: Breadcrumb[] = [];
let telemetryAuthToken: string | null = null;
let telemetrySurface: TelemetrySurface | null = null;

export function configureTelemetryContext(token: string | null, surface: TelemetrySurface | null) {
  telemetryAuthToken = token;
  telemetrySurface = surface;
}

function randomIdPart() {
  const cryptoApi = typeof globalThis !== "undefined" ? globalThis.crypto : undefined;
  if (cryptoApi && "randomUUID" in cryptoApi) {
    return cryptoApi.randomUUID().replace(/-/g, "").slice(0, 16);
  }
  return Math.random().toString(36).slice(2, 14);
}

function generatedId(prefix: string) {
  return `${prefix}_${Date.now()}_${randomIdPart()}`;
}

function canUseSessionStorage() {
  try {
    return typeof window !== "undefined" && Boolean(window.sessionStorage);
  } catch {
    return false;
  }
}

function storedId(storageKey: string, prefix: string) {
  if (!canUseSessionStorage()) {
    return generatedId(prefix);
  }
  try {
    const existing = window.sessionStorage.getItem(storageKey);
    if (existing) {
      return existing;
    }
    const next = generatedId(prefix);
    window.sessionStorage.setItem(storageKey, next);
    return next;
  } catch {
    return generatedId(prefix);
  }
}

export function telemetrySessionId() {
  return storedId(SESSION_STORAGE_KEY, "sess_web");
}

export function correlationId() {
  return storedId(CORRELATION_STORAGE_KEY, "corr_web");
}

function operationId(path: string, method: string) {
  const route = routeTemplate(path)
    .replace(/^\/+/, "")
    .replace(/[^A-Za-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "")
    .slice(0, 72);
  return `op_${method.toLowerCase()}_${route || "request"}_${randomIdPart()}`;
}

function requestSurface(path: string, headers: Headers) {
  const explicitSurface = headers.get("X-NODO-Surface");
  if (explicitSurface) {
    return explicitSurface;
  }
  if (path.startsWith("/api/v1/admin/")) {
    return "admin_web";
  }
  if (path.startsWith("/api/v1/business/")) {
    return "business_mini_app";
  }
  return null;
}

export function routeTemplate(path: string) {
  return path.split("?")[0] || path;
}

function nowMs() {
  if (typeof performance !== "undefined" && typeof performance.now === "function") {
    return performance.now();
  }
  return Date.now();
}

export function elapsedMs(startedAt: number) {
  return Math.max(0, Math.round((nowMs() - startedAt) * 100) / 100);
}

export function buildObservedRequest(path: string, token: string, options: RequestInit): ObservedRequestContext {
  const headers = new Headers(options.headers || {});
  const method = String(options.method || "GET").toUpperCase();
  headers.set("Authorization", `Bearer ${token}`);
  if (!headers.has("X-Request-Id")) {
    headers.set("X-Request-Id", generatedId("web_req"));
  }
  if (!headers.has("X-Correlation-Id")) {
    headers.set("X-Correlation-Id", correlationId());
  }
  if (!headers.has("X-NODO-Operation-Id")) {
    headers.set("X-NODO-Operation-Id", operationId(path, method));
  }
  const surface = requestSurface(path, headers);
  if (surface && !headers.has("X-NODO-Surface")) {
    headers.set("X-NODO-Surface", surface);
  }
  return {
    headers,
    method,
    routeTemplate: routeTemplate(path),
    requestId: headers.get("X-Request-Id") || generatedId("web_req"),
    correlationId: headers.get("X-Correlation-Id") || correlationId(),
    operationId: headers.get("X-NODO-Operation-Id") || operationId(path, method),
    surface,
    startedAt: nowMs()
  };
}

function observabilityIngestEnabled() {
  return getPublicEnv().NEXT_PUBLIC_OBSERVABILITY_INGEST_ENABLED === "1";
}

function isSensitiveKey(key: string) {
  const normalized = key.toLowerCase().replace(/-/g, "_");
  return sensitiveKeyFragments.some((fragment) => normalized.includes(fragment));
}

function safeMetadataValue(key: string, value: unknown): unknown {
  if (isSensitiveKey(key)) {
    return "[REDACTED]";
  }
  if (typeof value === "string") {
    return value.slice(0, 160);
  }
  if (typeof value === "boolean" || typeof value === "number" || value === null || value === undefined) {
    return value ?? null;
  }
  if (Array.isArray(value)) {
    return value.slice(0, 20).map((item) => safeMetadataValue(key, item));
  }
  if (typeof value === "object") {
    return Object.fromEntries(
      Object.entries(value as Record<string, unknown>)
        .slice(0, 20)
        .map(([itemKey, itemValue]) => [itemKey.slice(0, 80), safeMetadataValue(itemKey, itemValue)])
    );
  }
  return String(value).slice(0, 160);
}

function safeMetadata(values: Record<string, unknown>) {
  return Object.fromEntries(
    Object.entries(values)
      .slice(0, 40)
      .map(([key, value]) => [key.slice(0, 80), safeMetadataValue(key, value)])
  );
}

function pushBreadcrumb(breadcrumb: Breadcrumb) {
  breadcrumbs = [...breadcrumbs.slice(-(MAX_BREADCRUMBS - 1)), breadcrumb];
}

function emitFrontendTelemetryEvent(event: {
  eventType: string;
  severity?: "trace" | "debug" | "info" | "warn" | "error";
  screen?: string;
  previousScreen?: string;
  action?: string;
  durationMs?: number;
  errorCode?: string;
  metadata?: Record<string, unknown>;
}) {
  if (!observabilityIngestEnabled() || !telemetryAuthToken || !telemetrySurface) {
    return;
  }
  const headers = new Headers({
    Authorization: `Bearer ${telemetryAuthToken}`,
    "Content-Type": "application/json",
    "X-Request-Id": generatedId("web_obs"),
    "X-Correlation-Id": correlationId(),
    "X-NODO-Operation-Id": generatedId("op_frontend_ux"),
    "X-NODO-Surface": telemetrySurface
  });
  const payload = {
    session_id: telemetrySessionId(),
    app_version: getPublicEnv().NEXT_PUBLIC_APP_ENV || undefined,
    build_id: undefined,
    events: [
      {
        event_id: generatedId("evt_ux"),
        event_type: event.eventType,
        severity: event.severity || "info",
        timestamp: new Date().toISOString(),
        correlation_id: correlationId(),
        operation_id: generatedId("op_frontend_ux"),
        screen: event.screen,
        previous_screen: event.previousScreen,
        action: event.action,
        duration_ms: event.durationMs,
        error_code: event.errorCode,
        metadata: safeMetadata(event.metadata || {})
      }
    ]
  };
  void fetch(resolveApiUrl(OBSERVABILITY_ENDPOINT), {
    method: "POST",
    headers,
    body: JSON.stringify(payload),
    keepalive: true
  }).catch(() => undefined);
}

export function recordScreenView(screen: string, previousScreen?: string | null) {
  pushBreadcrumb({
    timestamp: new Date().toISOString(),
    event_type: "screen_view",
    screen,
    previous_screen: previousScreen || undefined
  });
  emitFrontendTelemetryEvent({
    eventType: "screen_view",
    screen,
    previousScreen: previousScreen || undefined
  });
}

export function recordActionBreadcrumb(
  action: string,
  details: { durationMs?: number; screen?: string; status?: "started" | "completed" | "failed"; errorCode?: string } = {}
) {
  pushBreadcrumb({
    timestamp: new Date().toISOString(),
    event_type: details.status ? `action_${details.status}` : "action",
    screen: details.screen,
    action,
    error_code: details.errorCode,
    duration_ms: typeof details.durationMs === "number" ? Math.max(0, Math.round(details.durationMs * 100) / 100) : undefined
  });
  emitFrontendTelemetryEvent({
    eventType: details.status ? `action_${details.status}` : "action",
    severity: details.status === "failed" ? "error" : "info",
    screen: details.screen,
    action,
    errorCode: details.errorCode,
    durationMs: typeof details.durationMs === "number" ? Math.max(0, Math.round(details.durationMs * 100) / 100) : undefined
  });
}

export function recordSlowSensitiveAction(
  action: string,
  details: { durationMs: number; screen?: string; errorCode?: string }
) {
  if (details.durationMs < SLOW_SENSITIVE_ACTION_THRESHOLD_MS) {
    return;
  }
  pushBreadcrumb({
    timestamp: new Date().toISOString(),
    event_type: "slow_sensitive_action",
    screen: details.screen,
    action,
    error_code: details.errorCode,
    duration_ms: Math.max(0, Math.round(details.durationMs * 100) / 100)
  });
  emitFrontendTelemetryEvent({
    eventType: "slow_sensitive_action",
    severity: "warn",
    screen: details.screen,
    action,
    errorCode: details.errorCode,
    durationMs: Math.max(0, Math.round(details.durationMs * 100) / 100)
  });
}

export function recordSlowScreenTransition(screen: string, previousScreen: string | null | undefined, durationMs: number) {
  if (durationMs < SLOW_SCREEN_TRANSITION_THRESHOLD_MS) {
    return;
  }
  pushBreadcrumb({
    timestamp: new Date().toISOString(),
    event_type: "slow_screen_transition",
    screen,
    previous_screen: previousScreen || undefined,
    duration_ms: Math.max(0, Math.round(durationMs * 100) / 100)
  });
  emitFrontendTelemetryEvent({
    eventType: "slow_screen_transition",
    severity: "warn",
    screen,
    previousScreen: previousScreen || undefined,
    durationMs: Math.max(0, Math.round(durationMs * 100) / 100)
  });
}

export function recentBreadcrumbs() {
  return breadcrumbs.slice();
}

export function recordApiFailure(context: ObservedRequestContext, details: { statusCode?: number; errorCode?: string; durationMs: number }) {
  pushBreadcrumb({
    timestamp: new Date().toISOString(),
    event_type: "api_failure",
    action: context.method,
    route_template: context.routeTemplate,
    status_code: details.statusCode,
    error_code: details.errorCode,
    duration_ms: details.durationMs
  });
}

export function emitApiFailure(
  token: string,
  context: ObservedRequestContext,
  details: { statusCode?: number; errorCode?: string; durationMs: number; responseStarted: boolean }
) {
  recordApiFailure(context, details);
  if (!observabilityIngestEnabled() || !token || context.routeTemplate === OBSERVABILITY_ENDPOINT) {
    return;
  }
  const headers = new Headers({
    Authorization: `Bearer ${token}`,
    "Content-Type": "application/json",
    "X-Request-Id": generatedId("web_obs"),
    "X-Correlation-Id": context.correlationId,
    "X-NODO-Operation-Id": context.operationId
  });
  const surface = context.surface || telemetrySurface;
  if (surface) {
    headers.set("X-NODO-Surface", surface);
  }
  const payload = {
    session_id: telemetrySessionId(),
    app_version: getPublicEnv().NEXT_PUBLIC_APP_ENV || undefined,
    build_id: undefined,
    events: [
      {
        event_id: generatedId("evt_api"),
        event_type: "api_failure",
        severity: "error",
        timestamp: new Date().toISOString(),
        request_id: context.requestId,
        correlation_id: context.correlationId,
        operation_id: context.operationId,
        action: context.method,
        route_template: context.routeTemplate,
        status_code: details.statusCode ?? 0,
        duration_ms: details.durationMs,
        error_code: details.errorCode || "API_REQUEST_FAILED",
        metadata: safeMetadata({
          response_started: details.responseStarted,
          online: typeof navigator === "undefined" ? null : navigator.onLine,
          breadcrumb_count: breadcrumbs.length
        })
      }
    ]
  };

  void fetch(resolveApiUrl(OBSERVABILITY_ENDPOINT), {
    method: "POST",
    headers,
    body: JSON.stringify(payload),
    keepalive: true
  }).catch(() => undefined);
}
