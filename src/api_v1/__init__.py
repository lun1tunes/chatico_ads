from fastapi import APIRouter

from .ai.views import router as ai_router
from .auth.views import router as auth_router
from .dashboard.views import router as dashboard_router
from .google_ads.views import router as google_ads_router
from .meta.views import router as meta_router
from .tiktok_ads.views import router as tiktok_ads_router

router = APIRouter()
router.include_router(auth_router, prefix="/auth", tags=["auth"])
router.include_router(meta_router, prefix="/meta", tags=["meta"])
router.include_router(google_ads_router, prefix="/google-ads", tags=["google-ads"])
router.include_router(tiktok_ads_router, prefix="/tiktok-ads", tags=["tiktok-ads"])
router.include_router(dashboard_router, prefix="/dashboard", tags=["dashboard"])
router.include_router(ai_router, prefix="/ai", tags=["ai"])
