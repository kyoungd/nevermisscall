"""Authentication utilities."""

from typing import Dict, Any, Optional
from fastapi import HTTPException, Header

from ..services.auth_service import AuthService
from ..config import settings


def validate_service_key(service_key: str) -> bool:
    """Validate internal service key."""
    return service_key == settings.internal_service_key


async def get_current_user(auth_service: AuthService, authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    """Get current authenticated user from JWT token."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")
    
    token = authorization.replace("Bearer ", "")
    user_data = await auth_service.authenticate_socket_connection(token)
    
    if not user_data:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    return user_data