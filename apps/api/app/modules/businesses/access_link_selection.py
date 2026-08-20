from __future__ import annotations

from app.modules.businesses.models import BusinessAccessLinkRecord


ACCESS_LINK_STATUS_PRIORITY = {
    "active": 4,
    "suspended": 3,
    "blocked": 2,
    "revoked": 1,
}


def preferred_access_link(links: list[BusinessAccessLinkRecord]) -> BusinessAccessLinkRecord | None:
    if not links:
        return None
    return sorted(
        links,
        key=lambda link: (
            ACCESS_LINK_STATUS_PRIORITY.get(link.status, 0),
            link.updated_at,
            link.id,
        ),
        reverse=True,
    )[0]
