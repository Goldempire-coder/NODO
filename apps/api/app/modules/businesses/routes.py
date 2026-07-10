from __future__ import annotations

from fastapi import APIRouter

from app.modules.businesses.access_routes import router as access_router
from app.modules.businesses.admin_routes import router as admin_router
from app.modules.businesses.legacy_routes import router as legacy_router
from app.modules.businesses.public_routes import router as public_router

router = APIRouter()
router.include_router(legacy_router)
router.include_router(public_router)
router.include_router(admin_router)
router.include_router(access_router)
