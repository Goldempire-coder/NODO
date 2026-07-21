from __future__ import annotations

from typing import Any, Callable

from app.core.errors import ApiError
from app.modules.businesses.reputation import public_reputation_payload
from app.modules.orders.helpers import require_uuid
from app.modules.orders.models import RatingRecord
from app.modules.orders.policy import require_remitter
from app.modules.orders.schemas import OrderRatingRequest
from app.modules.users.models import UserRecord


def rating_payload(rating: RatingRecord) -> dict[str, Any]:
    return {
        "id": rating.id,
        "order_id": rating.order_id,
        "business_id": rating.business_id,
        "stars": rating.stars,
        "created_at": rating.created_at.isoformat(),
    }


class OrderRatingOps:
    def __init__(
        self,
        *,
        repository,
        rating_repository,
        audit_writer,
        idempotency_store,
        rate_limit: Callable[[str, UserRecord], None],
    ) -> None:  # type: ignore[no-untyped-def]
        self._orders = repository
        self._ratings = rating_repository
        self._audit = audit_writer
        self._idempotency = idempotency_store
        self._rate_limit = rate_limit

    def state(self, *, order_id: str, user_id: str) -> dict[str, Any]:
        return self._ratings.rating_state(order_id=order_id, rater_user_id=user_id)

    def create(
        self,
        *,
        user: UserRecord,
        order_id: str,
        payload: OrderRatingRequest,
        request_id: str,
        idempotency_key: str | None,
    ) -> dict[str, Any]:
        require_remitter(user)
        self._rate_limit("rating", user)
        if not idempotency_key:
            raise ApiError("IDEMPOTENCY_KEY_REQUIRED", status_code=400)
        order_id = require_uuid(order_id, "ORDER_NOT_FOUND") or order_id

        def compute() -> dict[str, Any]:
            rating, business = self._ratings.create_for_completed_order(
                order_id=order_id,
                rater_user_id=user.id,
                stars=payload.stars,
            )
            self._audit.write(
                event_type="rating_created",
                actor_user_id=user.id,
                actor_role=user.role,
                resource_type="rating",
                resource_id=rating.id,
                request_id=request_id,
                metadata_json={"order_id": order_id, "business_id": business.id},
            )
            return {
                "rating": rating_payload(rating),
                "business_reputation": public_reputation_payload(business),
            }

        return self._idempotency.replay_or_store(
            f"orders:rating:{user.id}:{order_id}:{idempotency_key}",
            payload={"order_id": order_id, "stars": payload.stars},
            compute=compute,
        )
