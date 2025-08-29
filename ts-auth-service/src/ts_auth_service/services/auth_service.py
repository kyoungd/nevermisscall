"""Authentication service with business logic."""

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, Tuple
from uuid import UUID
import bcrypt

from ..config.settings import security_config
from ..models.user import User, UserRegistration, UserLogin, UserSession, TokenPair
from ..models.response import ErrorCode
from .database import DatabaseService
from .token_service import TokenService, token_service

logger = logging.getLogger(__name__)


class AuthService:
    """Handles authentication business logic."""
    
    def __init__(self, database: DatabaseService, token_service: TokenService):
        self.database = database
        self.token_service = token_service
        self.bcrypt_rounds = security_config.bcrypt_rounds
        self.password_min_length = security_config.password_min_length
    
    async def register_user(self, registration: UserRegistration, device_info: Optional[str] = None, ip_address: Optional[str] = None) -> Tuple[bool, Dict[str, Any]]:
        """
        Register a new user account.
        
        Returns:
            Tuple[bool, Dict]: (success, result_data_or_error)
        """
        try:
            # Check if email already exists
            if await self.database.email_exists(registration.email):
                return False, {
                    "error_code": ErrorCode.EMAIL_ALREADY_EXISTS,
                    "message": "An account with this email address already exists"
                }
            
            # Hash password
            password_hash = self._hash_password(registration.password)
            
            # Create user data
            user_data = {
                "email": registration.email,
                "password_hash": password_hash,
                "first_name": registration.first_name,
                "last_name": registration.last_name,
                "role": "owner",
                "email_verified": False,
                "is_active": True
            }
            
            # Create user in database
            user = await self.database.create_user(user_data)
            if not user:
                return False, {
                    "error_code": ErrorCode.INTERNAL_SERVER_ERROR,
                    "message": "Failed to create user account"
                }
            
            # Generate tokens
            tokens = self.token_service.generate_token_pair(user)
            
            # Create session
            session_data = {
                "user_id": user.id,
                "refresh_token": tokens.refresh_token,
                "device_info": device_info,
                "ip_address": ip_address,
                "expires_at": self.token_service.get_refresh_token_expiry()
            }
            
            session = await self.database.create_session(session_data)
            if not session:
                logger.warning(f"Failed to create session for user {user.id}")
            
            # Update last login
            await self.database.update_last_login(user.id)
            
            logger.info(f"User registered successfully: {user.email}")
            
            return True, {
                "user": user,
                "tokens": tokens
            }
            
        except Exception as e:
            logger.error(f"Error during user registration: {e}")
            return False, {
                "error_code": ErrorCode.INTERNAL_SERVER_ERROR,
                "message": "Registration failed due to server error"
            }
    
    async def login_user(self, login: UserLogin, device_info: Optional[str] = None, ip_address: Optional[str] = None) -> Tuple[bool, Dict[str, Any]]:
        """
        Authenticate user login.
        
        Returns:
            Tuple[bool, Dict]: (success, result_data_or_error)
        """
        try:
            # Find user by email
            user = await self.database.get_user_by_email(login.email)
            if not user:
                return False, {
                    "error_code": ErrorCode.INVALID_CREDENTIALS,
                    "message": "Invalid email or password"
                }
            
            # Check if account is active
            if not user.is_active:
                return False, {
                    "error_code": ErrorCode.ACCOUNT_DISABLED,
                    "message": "Account has been disabled"
                }
            
            # Verify password
            if not self._verify_password(login.password, user.password_hash):
                return False, {
                    "error_code": ErrorCode.INVALID_CREDENTIALS,
                    "message": "Invalid email or password"
                }
            
            # Generate tokens
            tokens = self.token_service.generate_token_pair(user)
            
            # Invalidate existing sessions (optional - depends on requirements)
            # await self.database.invalidate_user_sessions(user.id)
            
            # Create new session
            session_data = {
                "user_id": user.id,
                "refresh_token": tokens.refresh_token,
                "device_info": device_info,
                "ip_address": ip_address,
                "expires_at": self.token_service.get_refresh_token_expiry()
            }
            
            session = await self.database.create_session(session_data)
            if not session:
                logger.warning(f"Failed to create session for user {user.id}")
            
            # Update last login
            await self.database.update_last_login(user.id)
            
            logger.info(f"User logged in successfully: {user.email}")
            
            return True, {
                "user": user,
                "tokens": tokens
            }
            
        except Exception as e:
            logger.error(f"Error during user login: {e}")
            return False, {
                "error_code": ErrorCode.INTERNAL_SERVER_ERROR,
                "message": "Login failed due to server error"
            }
    
    async def refresh_token(self, refresh_token: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Refresh access token using refresh token.
        
        Returns:
            Tuple[bool, Dict]: (success, result_data_or_error)
        """
        try:
            # Get session by refresh token
            session = await self.database.get_session_by_token(refresh_token)
            if not session:
                return False, {
                    "error_code": ErrorCode.REFRESH_TOKEN_INVALID,
                    "message": "Invalid or expired refresh token"
                }
            
            # Check if session is active and not expired
            now = datetime.now(timezone.utc)
            if not session.is_active or session.expires_at <= now:
                # Clean up expired session
                await self.database.invalidate_session(refresh_token)
                return False, {
                    "error_code": ErrorCode.SESSION_EXPIRED,
                    "message": "Session has expired, please login again"
                }
            
            # Get user
            user = await self.database.get_user_by_id(session.user_id)
            if not user or not user.is_active:
                await self.database.invalidate_session(refresh_token)
                return False, {
                    "error_code": ErrorCode.USER_NOT_FOUND,
                    "message": "User account not found or disabled"
                }
            
            # Generate new access token
            new_access_token = self.token_service.refresh_access_token(user)
            
            # Create new token pair (keeping same refresh token)
            tokens = TokenPair(
                access_token=new_access_token,
                refresh_token=refresh_token,
                expires_in=self.token_service.access_token_expire,
                token_type="bearer"
            )
            
            logger.debug(f"Token refreshed for user {user.id}")
            
            return True, {
                "tokens": tokens
            }
            
        except Exception as e:
            logger.error(f"Error during token refresh: {e}")
            return False, {
                "error_code": ErrorCode.INTERNAL_SERVER_ERROR,
                "message": "Token refresh failed due to server error"
            }
    
    async def logout_user(self, refresh_token: str) -> bool:
        """
        Logout user by invalidating session.
        
        Returns:
            bool: Success status
        """
        try:
            # Invalidate session
            result = await self.database.invalidate_session(refresh_token)
            
            if result:
                logger.debug("User logged out successfully")
            else:
                logger.warning("Failed to invalidate session during logout")
            
            return result
            
        except Exception as e:
            logger.error(f"Error during logout: {e}")
            return False
    
    async def validate_token(self, token: str) -> Tuple[bool, Optional[User], Optional[str]]:
        """
        Validate JWT token and return user information.
        
        Returns:
            Tuple[bool, Optional[User], Optional[str]]: (valid, user, error_message)
        """
        try:
            # Validate token format
            if not self.token_service.validate_token_format(token):
                return False, None, "Invalid token format"
            
            # Validate and decode token
            payload = self.token_service.validate_access_token(token)
            if not payload:
                return False, None, "Invalid or expired token"
            
            # Get user from database
            user_id = UUID(payload.sub)
            user = await self.database.get_user_by_id(user_id)
            
            if not user:
                return False, None, "User not found"
            
            if not user.is_active:
                return False, None, "Account disabled"
            
            return True, user, None
            
        except Exception as e:
            logger.error(f"Error validating token: {e}")
            return False, None, "Token validation failed"
    
    async def get_user_profile(self, user_id: UUID) -> Optional[User]:
        """Get user profile information."""
        try:
            return await self.database.get_user_by_id(user_id)
            
        except Exception as e:
            logger.error(f"Error getting user profile: {e}")
            return None
    
    async def update_user_profile(self, user_id: UUID, update_data: Dict[str, Any]) -> Optional[User]:
        """Update user profile information."""
        try:
            # Filter allowed update fields
            allowed_fields = ['first_name', 'last_name', 'email']
            filtered_data = {k: v for k, v in update_data.items() if k in allowed_fields}
            
            if not filtered_data:
                return await self.database.get_user_by_id(user_id)
            
            # Check if new email already exists (if email is being updated)
            if 'email' in filtered_data:
                existing_user = await self.database.get_user_by_email(filtered_data['email'])
                if existing_user and existing_user.id != user_id:
                    return None  # Email already in use
            
            return await self.database.update_user(user_id, filtered_data)
            
        except Exception as e:
            logger.error(f"Error updating user profile: {e}")
            return None
    
    async def change_password(self, user_id: UUID, current_password: str, new_password: str) -> bool:
        """Change user password."""
        try:
            # Get current user
            user = await self.database.get_user_by_id(user_id)
            if not user:
                return False
            
            # Verify current password
            if not self._verify_password(current_password, user.password_hash):
                return False
            
            # Hash new password
            new_password_hash = self._hash_password(new_password)
            
            # Update password
            result = await self.database.update_user(user_id, {"password_hash": new_password_hash})
            
            if result:
                # Invalidate all sessions to force re-login
                await self.database.invalidate_user_sessions(user_id)
                logger.info(f"Password changed for user {user_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error changing password: {e}")
            return False
    
    # Private helper methods
    
    def _hash_password(self, password: str) -> str:
        """Hash password using bcrypt."""
        try:
            salt = bcrypt.gensalt(rounds=self.bcrypt_rounds)
            return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
            
        except Exception as e:
            logger.error(f"Error hashing password: {e}")
            raise
    
    def _verify_password(self, password: str, password_hash: str) -> bool:
        """Verify password against hash."""
        try:
            return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
            
        except Exception as e:
            logger.error(f"Error verifying password: {e}")
            return False
    
    def validate_password_strength(self, password: str) -> Tuple[bool, str]:
        """Validate password strength."""
        if len(password) < self.password_min_length:
            return False, f"Password must be at least {self.password_min_length} characters long"
        
        if not any(c.isalpha() for c in password):
            return False, "Password must contain at least one letter"
        
        if not any(c.isdigit() for c in password):
            return False, "Password must contain at least one number"
        
        return True, "Password is valid"
    
    async def get_service_stats(self) -> Dict[str, Any]:
        """Get service statistics."""
        try:
            user_count = await self.database.get_user_count()
            session_count = await self.database.get_active_session_count()
            
            return {
                "total_users": user_count,
                "active_sessions": session_count,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting service stats: {e}")
            return {
                "total_users": 0,
                "active_sessions": 0,
                "timestamp": datetime.utcnow().isoformat()
            }