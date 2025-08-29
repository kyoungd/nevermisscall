"""Authentication utilities for as-call-service."""

from typing import Optional
from uuid import UUID

from fastapi import Header, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError

from ..config import settings
from .shared_integration import logger, AuthenticationError


security = HTTPBearer(auto_error=False)


async def verify_internal_service_key(
    x_service_key: str = Header(None, alias="x-service-key")
) -> str:
    """Verify internal service API key."""
    if not x_service_key:
        logger.warning("Missing internal service key")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing service authentication key"
        )
    
    if x_service_key != settings.internal_service_key:
        logger.warning("Invalid internal service key", provided_key=x_service_key[:10] + "...")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid service authentication key"
        )
    
    return x_service_key


async def verify_jwt_token(
    authorization: Optional[HTTPAuthorizationCredentials] = security
) -> dict:
    """Verify JWT token for user authentication."""
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization token"
        )
    
    token = authorization.credentials
    
    if not settings.jwt_secret:
        logger.error("JWT secret not configured")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication not properly configured"
        )
    
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=["HS256"]
        )
        
        # Validate required claims
        user_id = payload.get("user_id")
        tenant_id = payload.get("tenant_id")
        
        if not user_id or not tenant_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token claims"
            )
        
        return {
            "user_id": UUID(user_id),
            "tenant_id": UUID(tenant_id),
            "email": payload.get("email"),
            "role": payload.get("role", "user"),
        }
        
    except JWTError as e:
        logger.warning("Invalid JWT token", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization token"
        )
    except ValueError as e:
        logger.warning("Invalid UUID in token", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token format"
        )


def verify_tenant_access(user_data: dict, tenant_id: UUID) -> None:
    """Verify user has access to the specified tenant."""
    if user_data["tenant_id"] != tenant_id:
        logger.warning(
            "Tenant access denied",
            user_id=user_data["user_id"],
            requested_tenant=tenant_id,
            user_tenant=user_data["tenant_id"]
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to tenant resources"
        )