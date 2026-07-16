import { resolveApiUrl } from "../lib/env";
import { buildObservedRequest, elapsedMs, emitApiFailure, type ObservedRequestContext } from "../observability/clientTelemetry";
import { clearAuthSession, currentAccessToken, inferAuthSurface, refreshAuthSession } from "./session";

export class ApiClientError extends Error {
  code: string;

  constructor(message: string, code: string) {
    super(message);
    this.name = "ApiClientError";
    this.code = code;
  }
}

async function performRequest(path: string, token: string, options: RequestInit = {}) {
  const context = buildObservedRequest(path, token, options);
  let response: Response;
  try {
    response = await fetch(resolveApiUrl(path), {
      ...options,
      headers: context.headers
    });
  } catch (error) {
    emitApiFailure(token, context, {
      statusCode: 0,
      errorCode: error instanceof Error ? error.name : "FETCH_ERROR",
      durationMs: elapsedMs(context.startedAt),
      responseStarted: false
    });
    throw error;
  }
  const payload = await response.json().catch(() => ({}));
  return { context, payload, response };
}

function reportFailedResponse(token: string, context: ObservedRequestContext, response: Response, payload: Record<string, any>) {
  emitApiFailure(token, context, {
    statusCode: response.status,
    errorCode: payload.error?.code || "UNKNOWN_ERROR",
    durationMs: elapsedMs(context.startedAt),
    responseStarted: true
  });
}

export async function apiRequest<T = unknown>(path: string, token: string, options: RequestInit = {}): Promise<T> {
  const surface = inferAuthSurface(path, options);
  const requestToken = currentAccessToken(surface, token);
  let telemetryToken = requestToken;
  let context: ObservedRequestContext;
  let payload: Record<string, any>;
  let response: Response;
  ({ context, payload, response } = await performRequest(path, requestToken, options));
  if (response.status === 401 && path !== "/api/v1/auth/refresh") {
    const refreshed = await refreshAuthSession(surface);
    if (refreshed?.accessToken) {
      telemetryToken = refreshed.accessToken;
      ({ context, payload, response } = await performRequest(path, refreshed.accessToken, options));
    } else {
      clearAuthSession(surface);
    }
  }
  if (!response.ok) {
    reportFailedResponse(telemetryToken, context, response, payload);
    throw new ApiClientError(payload.error?.message || "No logramos completar la accion. Intenta de nuevo.", payload.error?.code || "UNKNOWN_ERROR");
  }
  return payload.data;
}

export type AuthenticatedRequest = <T = unknown>(path: string, options?: RequestInit) => Promise<T>;
