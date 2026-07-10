from __future__ import annotations

from datetime import datetime


def run_expire_and_escalate_orders(app, *, current_time: datetime | None = None, batch_size: int = 100) -> dict:  # type: ignore[no-untyped-def]
    return app.state.expire_and_escalate_orders_worker.run(
        current_time=current_time,
        batch_size=batch_size,
        dry_run=False,
        request_id="scheduler_expire_and_escalate_orders",
    )
