"""Authentication utilities."""

import logging
from typing import Optional
from fastapi import HTTPException, Header

from ..config.settings import settings

logger = logging.getLogger(__name__)


async def verify_internal_service_key(
    x_service_key: Optional[str] = Header(None)
) -> bool:
    """Verify internal service authentication key."""
    if not x_service_key:
        logger.warning("Missing internal service key")
        raise HTTPException(
            status_code=401,
            detail="Internal service authentication required"
        )
    
    if x_service_key != settings.internal_service_key:
        logger.warning(f"Invalid internal service key: {x_service_key}")
        raise HTTPException(
            status_code=401,
            detail="Invalid internal service key"
        )
    
    return True


def get_service_auth_headers() -> dict:
    """Get headers for internal service-to-service requests."""
    return {
        "x-service-key": settings.internal_service_key,
        "Content-Type": "application/json"
    }