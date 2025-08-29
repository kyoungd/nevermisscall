"""Authentication middleware and utilities."""

import logging
from typing import Optional
from fastapi import HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from ..models.user import User
from ..models.response import ErrorCode, error_response
from ..services.auth_service import AuthService

logger = logging.getLogger(__name__)

# Security scheme for Bearer token
security = HTTPBearer()


class AuthMiddleware:
    """Authentication middleware for protecting endpoints."""
    
    def __init__(self, auth_service: AuthService):
        self.auth_service = auth_service
    
    async def get_current_user(
        self, 
        credentials: HTTPAuthorizationCredentials = Depends(security)
    ) -> User:
        """Get current authenticated user from JWT token."""
        try:
            token = credentials.credentials
            
            # Validate token and get user
            valid, user, error_message = await self.auth_service.validate_token(token)
            
            if not valid or not user:
                raise HTTPException(
                    status_code=401,
                    detail=error_response(
                        ErrorCode.INVALID_TOKEN,
                        error_message or "Invalid or expired token"
                    ),
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            return user
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error in get_current_user: {e}")
            raise HTTPException(
                status_code=401,
                detail=error_response(
                    ErrorCode.INTERNAL_SERVER_ERROR,
                    "Authentication failed"
                ),
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    async def get_optional_user(
        self, 
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))
    ) -> Optional[User]:
        """Get current user if authenticated, None otherwise."""
        try:
            if not credentials:
                return None
            
            token = credentials.credentials
            valid, user, _ = await self.auth_service.validate_token(token)
            
            return user if valid else None
            
        except Exception as e:
            logger.error(f"Error in get_optional_user: {e}")
            return None


def get_client_ip(request: Request) -> Optional[str]:
    """Extract client IP address from request."""
    try:
        # Check for forwarded IP first (in case of proxy/load balancer)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Get the first IP if multiple IPs are present
            return forwarded_for.split(",")[0].strip()
        
        # Check other common headers
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fall back to client host
        if hasattr(request, "client") and request.client:
            return request.client.host
        
        return None
        
    except Exception as e:
        logger.error(f"Error extracting client IP: {e}")
        return None


def get_user_agent(request: Request) -> Optional[str]:
    """Extract user agent from request."""
    try:
        return request.headers.get("User-Agent")
    except Exception as e:
        logger.error(f"Error extracting user agent: {e}")
        return None


def get_device_info(request: Request) -> Optional[str]:
    """Extract basic device information from request headers."""
    try:
        user_agent = get_user_agent(request)
        client_ip = get_client_ip(request)
        
        if user_agent or client_ip:
            info_parts = []
            if user_agent:
                # Truncate user agent to reasonable length
                truncated_ua = user_agent[:200] if len(user_agent) > 200 else user_agent
                info_parts.append(f"UA:{truncated_ua}")
            
            if client_ip:
                info_parts.append(f"IP:{client_ip}")
            
            return " | ".join(info_parts)
        
        return None
        
    except Exception as e:
        logger.error(f"Error extracting device info: {e}")
        return None