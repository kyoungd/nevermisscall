"""JWT token management service."""

import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from uuid import UUID
import jwt

from ..config.settings import jwt_config
from ..models.user import User, JWTPayload, TokenPair
from ..models.response import ErrorCode

logger = logging.getLogger(__name__)


class TokenService:
    """Handles JWT token generation and validation."""
    
    def __init__(self):
        self.secret = jwt_config.secret
        self.algorithm = jwt_config.algorithm
        self.access_token_expire = jwt_config.access_token_expire
        self.refresh_token_expire = jwt_config.refresh_token_expire
    
    def generate_access_token(self, user: User) -> str:
        """Generate JWT access token for user."""
        try:
            now = datetime.now(timezone.utc)
            expires_at = now + timedelta(seconds=self.access_token_expire)
            
            payload = JWTPayload(
                sub=str(user.id),
                email=user.email,
                tenant_id=str(user.tenant_id) if user.tenant_id else None,
                role=user.role,
                iat=int(now.timestamp()),
                exp=int(expires_at.timestamp())
            )
            
            token = jwt.encode(
                payload.dict(),
                self.secret,
                algorithm=self.algorithm
            )
            
            logger.debug(f"Generated access token for user {user.id}")
            return token
            
        except Exception as e:
            logger.error(f"Error generating access token: {e}")
            raise
    
    def generate_refresh_token(self) -> str:
        """Generate secure refresh token."""
        try:
            # Generate cryptographically secure random token
            return secrets.token_urlsafe(32)
            
        except Exception as e:
            logger.error(f"Error generating refresh token: {e}")
            raise
    
    def generate_token_pair(self, user: User) -> TokenPair:
        """Generate both access and refresh tokens."""
        try:
            access_token = self.generate_access_token(user)
            refresh_token = self.generate_refresh_token()
            
            return TokenPair(
                access_token=access_token,
                refresh_token=refresh_token,
                expires_in=self.access_token_expire,
                token_type="bearer"
            )
            
        except Exception as e:
            logger.error(f"Error generating token pair: {e}")
            raise
    
    def validate_access_token(self, token: str) -> Optional[JWTPayload]:
        """Validate and decode JWT access token."""
        try:
            payload = jwt.decode(
                token,
                self.secret,
                algorithms=[self.algorithm]
            )
            
            # Validate payload structure
            required_fields = ['sub', 'email', 'role', 'iat', 'exp']
            for field in required_fields:
                if field not in payload:
                    logger.warning(f"Missing required field '{field}' in token payload")
                    return None
            
            return JWTPayload(**payload)
            
        except jwt.ExpiredSignatureError:
            logger.debug("Token has expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            return None
        except Exception as e:
            logger.error(f"Error validating token: {e}")
            return None
    
    def extract_user_id_from_token(self, token: str) -> Optional[UUID]:
        """Extract user ID from token without full validation."""
        try:
            # Decode without verification for user ID extraction
            payload = jwt.decode(
                token,
                options={"verify_signature": False}
            )
            
            user_id_str = payload.get('sub')
            if user_id_str:
                return UUID(user_id_str)
            
            return None
            
        except Exception as e:
            logger.error(f"Error extracting user ID from token: {e}")
            return None
    
    def get_token_expiry(self, token: str) -> Optional[datetime]:
        """Get token expiry datetime."""
        try:
            payload = jwt.decode(
                token,
                options={"verify_signature": False}
            )
            
            exp_timestamp = payload.get('exp')
            if exp_timestamp:
                return datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting token expiry: {e}")
            return None
    
    def is_token_expired(self, token: str) -> bool:
        """Check if token is expired."""
        try:
            expiry = self.get_token_expiry(token)
            if expiry:
                return datetime.now(timezone.utc) >= expiry
            
            return True  # Assume expired if we can't determine expiry
            
        except Exception as e:
            logger.error(f"Error checking token expiry: {e}")
            return True
    
    def refresh_access_token(self, user: User) -> str:
        """Generate a new access token during refresh."""
        try:
            return self.generate_access_token(user)
            
        except Exception as e:
            logger.error(f"Error refreshing access token: {e}")
            raise
    
    def validate_token_format(self, token: str) -> bool:
        """Validate basic token format without verification."""
        try:
            if not token or not isinstance(token, str):
                return False
            
            # Basic JWT format check (3 parts separated by dots)
            parts = token.split('.')
            if len(parts) != 3:
                return False
            
            # Check if parts are base64 encoded
            for part in parts:
                if not part or not all(c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_=' for c in part):
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating token format: {e}")
            return False
    
    def get_refresh_token_expiry(self) -> datetime:
        """Get refresh token expiry datetime."""
        return datetime.now(timezone.utc) + timedelta(seconds=self.refresh_token_expire)
    
    def create_token_response(self, tokens: TokenPair) -> Dict[str, Any]:
        """Create standardized token response."""
        return {
            "accessToken": tokens.access_token,
            "refreshToken": tokens.refresh_token,
            "expiresIn": tokens.expires_in,
            "tokenType": tokens.token_type
        }


class TokenBlacklistService:
    """Handles token blacklisting for logout functionality."""
    
    def __init__(self):
        # In a production environment, this would be backed by Redis or database
        self._blacklisted_tokens = set()
    
    def blacklist_token(self, token: str) -> bool:
        """Add token to blacklist."""
        try:
            self._blacklisted_tokens.add(token)
            logger.debug(f"Token blacklisted")
            return True
            
        except Exception as e:
            logger.error(f"Error blacklisting token: {e}")
            return False
    
    def is_token_blacklisted(self, token: str) -> bool:
        """Check if token is blacklisted."""
        try:
            return token in self._blacklisted_tokens
            
        except Exception as e:
            logger.error(f"Error checking token blacklist: {e}")
            return False
    
    def cleanup_expired_tokens(self):
        """Clean up expired tokens from blacklist."""
        # This would be implemented with proper token expiry checking
        # For now, we'll keep it simple
        pass


# Global instances
token_service = TokenService()
token_blacklist = TokenBlacklistService()