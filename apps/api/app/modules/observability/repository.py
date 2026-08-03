from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from app.shared.db.connection import pooled_connect


FRICTION_EVENT_TYPES = {
    "api_failure",
    "action_failed",
    "slow_sensitive_action",
    "slow_screen_transition",
}


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _as_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _percentile(values: list[float], percentile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round((len(ordered) - 1) * percentile)))
    return round(ordered[index], 2)


def _is_friction_event(event: dict[str, Any]) -> bool:
    status_code = event.get("status_code")
    return (
        event.get("event_type") in FRICTION_EVENT_TYPES
        or event.get("severity") in {"warn", "error"}
        or (isinstance(status_code, int) and status_code >= 400)
    )


def _limited_top(items: dict[str, dict[str, Any]], *, limit: int) -> list[dict[str, Any]]:
    return sorted(items.values(), key=lambda item: (-int(item.get("friction_count", item.get("count", 0))), item.get("name", "")))[:limit]


def summarize_ux_events(events: list[dict[str, Any]], *, ingest_enabled: bool, window_hours: int, limit: int) -> dict[str, Any]:
    surfaces: dict[str, dict[str, Any]] = {}
    screens: dict[str, dict[str, Any]] = {}
    actions: dict[str, dict[str, Any]] = {}
    routes: dict[str, dict[str, Any]] = {}
    sessions = set()
    friction_count = 0
    durations_by_screen: dict[str, list[float]] = {}
    durations_by_action: dict[str, list[float]] = {}
    recent_friction: list[dict[str, Any]] = []

    for event in events:
        surface = str(event.get("surface") or "unknown")
        session_hash = event.get("session_id_hash")
        if session_hash:
            sessions.add(session_hash)

        surface_item = surfaces.setdefault(
            surface,
            {"surface": surface, "event_count": 0, "friction_count": 0, "screen_views": 0, "api_failures": 0, "slow_events": 0},
        )
        surface_item["event_count"] += 1

        event_type = str(event.get("event_type") or "")
        is_friction = _is_friction_event(event)
        if is_friction:
            friction_count += 1
            surface_item["friction_count"] += 1
            recent_friction.append(
                {
                    "event_type": event_type,
                    "surface": surface,
                    "screen": event.get("screen"),
                    "action": event.get("action"),
                    "route_template": event.get("route_template"),
                    "status_code": event.get("status_code"),
                    "error_code": event.get("error_code"),
                    "duration_ms": _as_float(event.get("duration_ms")),
                    "occurred_at": event.get("occurred_at"),
                }
            )
        if event_type == "screen_view":
            surface_item["screen_views"] += 1
        if event_type == "api_failure":
            surface_item["api_failures"] += 1
        if event_type.startswith("slow_"):
            surface_item["slow_events"] += 1

        screen = event.get("screen")
        if screen:
            key = f"{surface}:{screen}"
            screen_item = screens.setdefault(
                key,
                {"surface": surface, "screen": screen, "views": 0, "friction_count": 0, "slow_count": 0, "failure_count": 0, "p95_duration_ms": None},
            )
            if event_type == "screen_view":
                screen_item["views"] += 1
            if is_friction:
                screen_item["friction_count"] += 1
            if event_type.startswith("slow_"):
                screen_item["slow_count"] += 1
            if event_type in {"api_failure", "action_failed"} or event.get("severity") == "error":
                screen_item["failure_count"] += 1
            duration = _as_float(event.get("duration_ms"))
            if duration is not None:
                durations_by_screen.setdefault(key, []).append(duration)

        action = event.get("action")
        if action:
            key = f"{surface}:{action}"
            action_item = actions.setdefault(
                key,
                {
                    "surface": surface,
                    "action": action,
                    "started": 0,
                    "completed": 0,
                    "failed": 0,
                    "slow_count": 0,
                    "friction_count": 0,
                    "p95_duration_ms": None,
                },
            )
            if event_type == "action_started":
                action_item["started"] += 1
            if event_type == "action_completed":
                action_item["completed"] += 1
            if event_type == "action_failed":
                action_item["failed"] += 1
            if event_type.startswith("slow_"):
                action_item["slow_count"] += 1
            if is_friction:
                action_item["friction_count"] += 1
            duration = _as_float(event.get("duration_ms"))
            if duration is not None:
                durations_by_action.setdefault(key, []).append(duration)

        route = event.get("route_template")
        if event_type == "api_failure" and route:
            key = f"{surface}:{route}"
            route_item = routes.setdefault(
                key,
                {"surface": surface, "route_template": route, "count": 0, "friction_count": 0, "status_counts": {}, "error_codes": {}},
            )
            route_item["count"] += 1
            route_item["friction_count"] += 1
            status = str(event.get("status_code") or "0")
            error_code = str(event.get("error_code") or "UNKNOWN_ERROR")
            route_item["status_counts"][status] = route_item["status_counts"].get(status, 0) + 1
            route_item["error_codes"][error_code] = route_item["error_codes"].get(error_code, 0) + 1

    for key, values in durations_by_screen.items():
        screens[key]["p95_duration_ms"] = _percentile(values, 0.95)
    for key, values in durations_by_action.items():
        actions[key]["p95_duration_ms"] = _percentile(values, 0.95)

    recent_friction = sorted(recent_friction, key=lambda item: str(item.get("occurred_at") or ""), reverse=True)[:limit]
    top_screens = _limited_top(screens, limit=limit)
    top_actions = _limited_top(actions, limit=limit)
    top_routes = sorted(routes.values(), key=lambda item: (-int(item["count"]), str(item["route_template"])))[:limit]

    recommendations: list[str] = []
    if not ingest_enabled:
        recommendations.append("Activar OBSERVABILITY_INGEST_ENABLED y NEXT_PUBLIC_OBSERVABILITY_INGEST_ENABLED para recolectar friccion UX.")
    if not events:
        recommendations.append("Aun no hay eventos UX persistidos para este periodo.")
    if top_screens:
        recommendations.append(f"Revisar primero la pantalla {top_screens[0]['screen']} en {top_screens[0]['surface']}.")
    if top_actions:
        recommendations.append(f"Revisar la accion {top_actions[0]['action']} porque concentra friccion.")
    if top_routes:
        recommendations.append(f"Correlacionar errores de API en {top_routes[0]['route_template']}.")

    return {
        "ingest_enabled": ingest_enabled,
        "window_hours": window_hours,
        "total_events": len(events),
        "unique_sessions": len(sessions),
        "friction_events": friction_count,
        "surfaces": sorted(surfaces.values(), key=lambda item: item["surface"]),
        "top_screens": top_screens,
        "top_actions": top_actions,
        "api_failures": top_routes,
        "recent_friction": recent_friction,
        "recommended_actions": recommendations,
        "disclaimer": "Panel UX: usa eventos limitados y agregados; no almacena IP, wallet, Zelle completo, PIN, tokens ni comprobantes.",
    }


class InMemoryFrontendObservabilityRepository:
    def __init__(self) -> None:
        self._events: list[dict[str, Any]] = []

    def record_event(self, **fields: Any) -> None:
        self._events.append(dict(fields))

    def ux_friction_summary(self, *, ingest_enabled: bool, window_hours: int, limit: int) -> dict[str, Any]:
        cutoff = _now_utc() - timedelta(hours=window_hours)
        events = [event for event in self._events if event.get("created_at", _now_utc()) >= cutoff]
        return summarize_ux_events(events, ingest_enabled=ingest_enabled, window_hours=window_hours, limit=limit)


class PostgresFrontendObservabilityRepository:
    def __init__(self, database_url: str) -> None:
        self._database_url = database_url

    def _connect(self):  # type: ignore[no-untyped-def]
        return pooled_connect(self._database_url)

    def record_event(self, **fields: Any) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                insert into frontend_observability_events (
                    event_id, event_type, severity, surface, session_id_hash, actor_user_hash,
                    actor_role, request_id, correlation_id, operation_id, screen,
                    previous_screen, action, method, route_template, status_code,
                    duration_ms, error_code, resource_refs_json, metadata_json,
                    occurred_at, created_at
                )
                values (
                    %(event_id)s, %(event_type)s, %(severity)s, %(surface)s, %(session_id_hash)s,
                    %(actor_user_hash)s, %(actor_role)s, %(request_id)s, %(correlation_id)s,
                    %(operation_id)s, %(screen)s, %(previous_screen)s, %(action)s, %(method)s,
                    %(route_template)s, %(status_code)s, %(duration_ms)s, %(error_code)s,
                    %(resource_refs_json)s::jsonb, %(metadata_json)s::jsonb, %(occurred_at)s, now()
                )
                """,
                fields,
            )

    def ux_friction_summary(self, *, ingest_enabled: bool, window_hours: int, limit: int) -> dict[str, Any]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                select event_id, event_type, severity, surface, session_id_hash, actor_user_hash,
                       actor_role, request_id, correlation_id, operation_id, screen,
                       previous_screen, action, method, route_template, status_code,
                       duration_ms, error_code, resource_refs_json, metadata_json,
                       occurred_at, created_at
                from frontend_observability_events
                where created_at >= now() - (%s::text)::interval
                order by created_at desc
                limit 5000
                """,
                (f"{window_hours} hours",),
            ).fetchall()
        return summarize_ux_events([dict(row) for row in rows], ingest_enabled=ingest_enabled, window_hours=window_hours, limit=limit)
