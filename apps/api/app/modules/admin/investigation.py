from __future__ import annotations

import hashlib
from typing import Any


ADMIN_INVESTIGATION_GROUPS = ("users", "businesses", "business_intakes", "orders", "support_tickets")


def compact_digits(value: object | None) -> str:
    if value is None:
        return ""
    return "".join(ch for ch in str(value) if ch.isdigit())


def query_fingerprint(query: str) -> str:
    return hashlib.sha256(query.strip().lower().encode("utf-8")).hexdigest()[:16]


def empty_investigation_groups() -> dict[str, list[dict[str, Any]]]:
    return {group: [] for group in ADMIN_INVESTIGATION_GROUPS}


def investigation_result_counts(groups: dict[str, list[dict[str, Any]]]) -> dict[str, int]:
    return {group: len(groups.get(group, [])) for group in ADMIN_INVESTIGATION_GROUPS}


def investigation_item(
    *,
    item_type: str,
    item_id: str,
    title: str,
    subtitle: str,
    matched_on: list[str],
    action_route: str,
    status: str | None = None,
    reference: str | None = None,
    created_at: str | None = None,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "type": item_type,
        "id": item_id,
        "title": title,
        "subtitle": subtitle,
        "matched_on": sorted(set(matched_on)),
        "action_route": action_route,
        "status": status,
        "reference": reference,
        "created_at": created_at,
        "context": context or {},
    }


def contains_text(value: object | None, needle: str) -> bool:
    if value is None or not needle:
        return False
    return needle in str(value).lower()


def contains_digits(value: object | None, digits: str) -> bool:
    if value is None or not digits:
        return False
    return digits in compact_digits(value)


def append_group_item(groups: dict[str, list[dict[str, Any]]], group: str, item: dict[str, Any], *, limit: int) -> None:
    if len(groups[group]) >= limit:
        return
    if any(existing["id"] == item["id"] for existing in groups[group]):
        return
    groups[group].append(item)
