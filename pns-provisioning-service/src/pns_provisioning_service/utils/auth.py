"""Authentication utilities."""

import logging
from typing import Optional
from fastapi import HTTPException, Header, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt

from ..config.settings import settings

logger = logging.getLogger(__name__)

# Security schemes
security = HTTPBearer()


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


async def verify_jwt_token(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """Verify JWT token and return payload."""
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm]
        )
        
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=401,
                detail="Could not validate credentials"
            )
        
        return payload
        
    except JWTError as e:
        logger.warning(f"JWT validation failed: {e}")
        raise HTTPException(
            status_code=401,
            detail="Could not validate credentials"
        )


def get_service_auth_headers() -> dict:
    """Get headers for internal service-to-service requests."""
    return {
        "X-Service-Key": settings.internal_service_key,
        "Content-Type": "application/json"
    }


def extract_tenant_id_from_token(payload: dict) -> Optional[str]:
    """Extract tenant ID from JWT token payload."""
    return payload.get("tenant_id")