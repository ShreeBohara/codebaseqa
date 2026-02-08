"""Platform/runtime configuration endpoints for frontend feature flags."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.core.demo_mode import get_platform_config_payload
from src.dependencies import get_db
from src.models.schemas import PlatformConfigResponse

router = APIRouter(tags=["platform"])


@router.get("/config", response_model=PlatformConfigResponse)
async def get_platform_config(db: Session = Depends(get_db)):
    """Expose runtime mode flags so frontend can adapt behavior safely."""
    return get_platform_config_payload(db)
