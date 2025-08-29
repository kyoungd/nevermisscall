"""Authentication service for JWT token validation."""

import httpx
import logging
from typing import Optional, Dict, Any
from jose import jwt, JWTError

from ..config import settings

logger = logging.getLogger(__name__)


class AuthService:
    """JWT authentication service for WebSocket connections."""
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=10.0)
        self.auth_service_url = settings.ts_auth_service_url
    
    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()
    
    async def validate_jwt_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Validate JWT token with ts-auth-service."""
        try:
            # Call ts-auth-service to validate token
            response = await self.client.post(
                f"{self.auth_service_url}/internal/auth/validate",
                json={"token": token},
                headers={
                    "x-service-key": settings.internal_service_key,
                    "Content-Type": "application/json"
                }
            )
            
            if response.status_code == 200:
                validation_result = response.json()
                if validation_result.get("valid"):
                    return validation_result.get("user")
            
            logger.warning(f"Token validation failed: {response.status_code}")
            return None
            
        except Exception as e:
            logger.error(f"Error validating JWT token: {e}")
            return None
    
    async def decode_token_locally(self, token: str, secret_key: str) -> Optional[Dict[str, Any]]:
        """Decode JWT token locally (fallback method)."""
        try:
            payload = jwt.decode(token, secret_key, algorithms=["HS256"])
            return payload
            
        except JWTError as e:
            logger.warning(f"JWT decode error: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error decoding JWT: {e}")
            return None
    
    async def authenticate_socket_connection(self, token: str) -> Optional[Dict[str, Any]]:
        """Authenticate WebSocket connection using JWT token."""
        user_data = await self.validate_jwt_token(token)
        
        if user_data:
            # Extract required fields for connection
            return {
                "user_id": user_data.get("user_id"),
                "tenant_id": user_data.get("tenant_id"),
                "email": user_data.get("email"),
                "permissions": user_data.get("permissions", [])
            }
        
        return None
    
    def validate_service_key(self, service_key: str) -> bool:
        """Validate internal service key for HTTP endpoints."""
        return service_key == settings.internal_service_key
    
    async def check_user_tenant_access(self, user_id: str, tenant_id: str) -> bool:
        """Check if user has access to tenant."""
        try:
            response = await self.client.post(
                f"{settings.ts_tenant_service_url}/internal/tenants/check-access",
                json={"user_id": user_id, "tenant_id": tenant_id},
                headers={
                    "x-service-key": settings.internal_service_key,
                    "Content-Type": "application/json"
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get("has_access", False)
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking user tenant access: {e}")
            return False