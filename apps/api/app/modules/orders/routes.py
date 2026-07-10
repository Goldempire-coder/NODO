from __future__ import annotations

from fastapi import APIRouter

from app.modules.orders.business_routes import router as business_router
from app.modules.orders.payment_routes import router as payment_router
from app.modules.orders.remitter_routes import router as remitter_router

router = APIRouter()
router.include_router(remitter_router)
router.include_router(business_router)
router.include_router(payment_router)
