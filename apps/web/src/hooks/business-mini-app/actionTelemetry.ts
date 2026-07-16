import { elapsedMs, recordActionBreadcrumb, recordSlowSensitiveAction } from "../../observability/clientTelemetry";

export function actionStartedAt() {
  if (typeof performance !== "undefined" && typeof performance.now === "function") {
    return performance.now();
  }
  return Date.now();
}

export function recordBusinessActionStarted(action: string, screen: string) {
  recordActionBreadcrumb(action, { screen, status: "started" });
}

export function recordBusinessActionCompleted(action: string, screen: string, startedAt: number) {
  const durationMs = elapsedMs(startedAt);
  recordActionBreadcrumb(action, { durationMs, screen, status: "completed" });
  recordSlowSensitiveAction(action, { durationMs, screen });
}

export function recordBusinessActionFailed(action: string, screen: string, startedAt: number, errorCode?: string) {
  const durationMs = elapsedMs(startedAt);
  recordActionBreadcrumb(action, { durationMs, errorCode, screen, status: "failed" });
  recordSlowSensitiveAction(action, { durationMs, errorCode, screen });
}
