"""Authentication endpoints controller."""

import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, Request, status
from fastapi.responses import JSONResponse

from ..models.user import (
    UserRegistration, UserLogin, UserResponse, TokenPair,
    RefreshTokenRequest, TokenValidationRequest, User
)
from ..models.response import (
    ErrorCode, success_response, error_response, auth_success_response,
    validation_error_response, TokenValidationResponse
)
from ..services.auth_service import AuthService
from ..utils.middleware import AuthMiddleware, get_client_ip, get_device_info

logger = logging.getLogger(__name__)


def create_auth_router(auth_service: AuthService) -> APIRouter:
    """Create authentication router with endpoints."""
    
    router = APIRouter(prefix="/auth", tags=["Authentication"])
    auth_middleware = AuthMiddleware(auth_service)
    
    @router.post("/register", status_code=status.HTTP_201_CREATED)
    async def register_user(
        registration: UserRegistration,
        request: Request
    ):
        """Register a new business owner account."""
        try:
            # Extract device info and IP
            device_info = get_device_info(request)
            ip_address = get_client_ip(request)
            
            # Register user
            success, result = await auth_service.register_user(
                registration, device_info, ip_address
            )
            
            if not success:
                error_code = result.get("error_code", ErrorCode.INTERNAL_SERVER_ERROR)
                message = result.get("message", "Registration failed")
                
                status_code = status.HTTP_400_BAD_REQUEST
                if error_code == ErrorCode.EMAIL_ALREADY_EXISTS:
                    status_code = status.HTTP_409_CONFLICT
                elif error_code == ErrorCode.INTERNAL_SERVER_ERROR:
                    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
                
                return JSONResponse(
                    status_code=status_code,
                    content=error_response(error_code, message)
                )
            
            # Convert user to response model
            user_response = UserResponse(
                id=result["user"].id,
                email=result["user"].email,
                first_name=result["user"].first_name,
                last_name=result["user"].last_name,
                tenant_id=result["user"].tenant_id,
                role=result["user"].role,
                email_verified=result["user"].email_verified,
                is_active=result["user"].is_active,
                last_login_at=result["user"].last_login_at,
                created_at=result["user"].created_at
            )
            
            return auth_success_response(
                user_response,
                result["tokens"],
                "Account created successfully"
            )
            
        except ValueError as e:
            logger.warning(f"Validation error in registration: {e}")
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content=error_response(ErrorCode.VALIDATION_ERROR, str(e))
            )
        except Exception as e:
            logger.error(f"Unexpected error in registration: {e}")
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content=error_response(
                    ErrorCode.INTERNAL_SERVER_ERROR,
                    "Registration failed due to server error"
                )
            )
    
    @router.post("/login")
    async def login_user(
        login: UserLogin,
        request: Request
    ):
        """Authenticate existing user."""
        try:
            # Extract device info and IP
            device_info = get_device_info(request)
            ip_address = get_client_ip(request)
            
            # Authenticate user
            success, result = await auth_service.login_user(
                login, device_info, ip_address
            )
            
            if not success:
                error_code = result.get("error_code", ErrorCode.INTERNAL_SERVER_ERROR)
                message = result.get("message", "Login failed")
                
                status_code = status.HTTP_401_UNAUTHORIZED
                if error_code == ErrorCode.ACCOUNT_DISABLED:
                    status_code = status.HTTP_403_FORBIDDEN
                elif error_code == ErrorCode.INTERNAL_SERVER_ERROR:
                    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
                
                return JSONResponse(
                    status_code=status_code,
                    content=error_response(error_code, message)
                )
            
            # Convert user to response model
            user_response = UserResponse(
                id=result["user"].id,
                email=result["user"].email,
                first_name=result["user"].first_name,
                last_name=result["user"].last_name,
                tenant_id=result["user"].tenant_id,
                role=result["user"].role,
                email_verified=result["user"].email_verified,
                is_active=result["user"].is_active,
                last_login_at=result["user"].last_login_at,
                created_at=result["user"].created_at
            )
            
            return auth_success_response(
                user_response,
                result["tokens"],
                "Login successful"
            )
            
        except ValueError as e:
            logger.warning(f"Validation error in login: {e}")
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content=error_response(ErrorCode.VALIDATION_ERROR, str(e))
            )
        except Exception as e:
            logger.error(f"Unexpected error in login: {e}")
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content=error_response(
                    ErrorCode.INTERNAL_SERVER_ERROR,
                    "Login failed due to server error"
                )
            )
    
    @router.post("/refresh")
    async def refresh_token(refresh_request: RefreshTokenRequest):
        """Refresh expired access token."""
        try:
            success, result = await auth_service.refresh_token(refresh_request.refresh_token)
            
            if not success:
                error_code = result.get("error_code", ErrorCode.INTERNAL_SERVER_ERROR)
                message = result.get("message", "Token refresh failed")
                
                status_code = status.HTTP_401_UNAUTHORIZED
                if error_code == ErrorCode.SESSION_EXPIRED:
                    status_code = status.HTTP_401_UNAUTHORIZED
                elif error_code == ErrorCode.INTERNAL_SERVER_ERROR:
                    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
                
                return JSONResponse(
                    status_code=status_code,
                    content=error_response(error_code, message)
                )
            
            return success_response(
                {"tokens": result["tokens"].dict()},
                "Token refreshed successfully"
            )
            
        except Exception as e:
            logger.error(f"Unexpected error in token refresh: {e}")
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content=error_response(
                    ErrorCode.INTERNAL_SERVER_ERROR,
                    "Token refresh failed due to server error"
                )
            )
    
    @router.post("/logout")
    async def logout_user(
        refresh_request: RefreshTokenRequest,
        current_user: User = Depends(auth_middleware.get_current_user)
    ):
        """Invalidate user session."""
        try:
            success = await auth_service.logout_user(refresh_request.refresh_token)
            
            if success:
                return success_response(
                    None,
                    "Logged out successfully"
                )
            else:
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content=error_response(
                        ErrorCode.INTERNAL_SERVER_ERROR,
                        "Logout failed"
                    )
                )
            
        except Exception as e:
            logger.error(f"Unexpected error in logout: {e}")
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content=error_response(
                    ErrorCode.INTERNAL_SERVER_ERROR,
                    "Logout failed due to server error"
                )
            )
    
    @router.post("/validate")
    async def validate_token(validation_request: TokenValidationRequest):
        """Validate JWT token (for other services)."""
        try:
            valid, user, error_message = await auth_service.validate_token(validation_request.token)
            
            if valid and user:
                user_response = UserResponse(
                    id=user.id,
                    email=user.email,
                    first_name=user.first_name,
                    last_name=user.last_name,
                    tenant_id=user.tenant_id,
                    role=user.role,
                    email_verified=user.email_verified,
                    is_active=user.is_active,
                    last_login_at=user.last_login_at,
                    created_at=user.created_at
                )
                
                return TokenValidationResponse(
                    valid=True,
                    user=user_response
                )
            else:
                return TokenValidationResponse(
                    valid=False,
                    error=error_message or "Invalid token"
                )
            
        except Exception as e:
            logger.error(f"Unexpected error in token validation: {e}")
            return TokenValidationResponse(
                valid=False,
                error="Token validation failed due to server error"
            )
    
    @router.get("/me")
    async def get_current_user_profile(
        current_user: User = Depends(auth_middleware.get_current_user)
    ):
        """Get current user information."""
        try:
            user_response = UserResponse(
                id=current_user.id,
                email=current_user.email,
                first_name=current_user.first_name,
                last_name=current_user.last_name,
                tenant_id=current_user.tenant_id,
                role=current_user.role,
                email_verified=current_user.email_verified,
                is_active=current_user.is_active,
                last_login_at=current_user.last_login_at,
                created_at=current_user.created_at
            )
            
            return success_response(
                {"user": user_response.dict()},
                "User profile retrieved successfully"
            )
            
        except Exception as e:
            logger.error(f"Unexpected error in get user profile: {e}")
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content=error_response(
                    ErrorCode.INTERNAL_SERVER_ERROR,
                    "Failed to retrieve user profile"
                )
            )
    
    return router