"""
Authentication models for NeverMissCall shared library.

Provides User, Tenant, and JWT models following the database schema
defined in database-migration-order.md and authentication standards.
"""

from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, EmailStr


class User(BaseModel):
    """
    User model following the database schema from database-migration-order.md.
    
    Maps to the 'users' table in the PostgreSQL database.
    """
    id: str
    email: EmailStr
    password_hash: Optional[str] = None  # Not included in API responses
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    
    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class UserProfile(BaseModel):
    """
    User profile model following the database schema.
    
    Maps to the 'user_profiles' table with extended user information.
    """
    id: str
    user_id: str
    tenant_id: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: EmailStr
    phone_number: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class UserPreferences(BaseModel):
    """
    User preferences model following the database schema.
    
    Maps to the 'user_preferences' table.
    """
    id: str
    user_id: str
    notification_email: bool = True
    notification_sms: bool = True
    notification_push: bool = True
    ai_takeover_delay: int = 60  # seconds
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class UserStatus(BaseModel):
    """
    User status model following the database schema.
    
    Maps to the 'user_status' table for tracking user availability.
    """
    id: str
    user_id: str
    is_active: bool = True
    is_online: bool = False
    status: str = 'available'  # available, busy, away, etc.
    last_seen_at: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class Tenant(BaseModel):
    """
    Tenant model following the database schema from database-migration-order.md.
    
    Maps to the 'tenants' table for business/organization information.
    """
    id: str
    business_name: str
    business_address: Optional[str] = None
    business_latitude: Optional[float] = None
    business_longitude: Optional[float] = None
    trade_type: Optional[str] = None
    service_area_radius: int = 25  # miles
    onboarding_completed: bool = False
    onboarding_step: int = 1
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class BusinessSettings(BaseModel):
    """
    Business settings model following the database schema.
    
    Maps to the 'business_settings' table with operational configuration.
    """
    id: str
    tenant_id: str
    business_hours: Dict[str, Any] = Field(default_factory=lambda: {
        "monday": {"open": "09:00", "close": "17:00", "enabled": True},
        "tuesday": {"open": "09:00", "close": "17:00", "enabled": True},
        "wednesday": {"open": "09:00", "close": "17:00", "enabled": True},
        "thursday": {"open": "09:00", "close": "17:00", "enabled": True},
        "friday": {"open": "09:00", "close": "17:00", "enabled": True},
        "saturday": {"open": "09:00", "close": "17:00", "enabled": False},
        "sunday": {"open": "09:00", "close": "17:00", "enabled": False}
    })
    timezone: str = 'America/New_York'
    auto_response_enabled: bool = True
    auto_response_message: str = 'Hi! Sorry we missed your call. How can we help?'
    ai_greeting_template: str = 'Hello! I\'m here to help with your [TRADE] needs. What can I assist you with today?'
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class JwtPayload(BaseModel):
    """
    JWT token payload model for authentication.
    
    Follows the JWT patterns defined in authentication-standards.md
    for user-facing authentication.
    """
    user_id: str
    tenant_id: str
    role: str
    email: str
    iat: Optional[int] = None  # issued at
    exp: Optional[int] = None  # expires at
    
    # Additional claims
    session_id: Optional[str] = None
    permissions: Optional[list] = None


class UserSession(BaseModel):
    """
    User session model following the database schema.
    
    Maps to the 'user_sessions' table for session management.
    """
    id: str
    user_id: str
    session_token: str
    expires_at: str
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    
    # Additional session data
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    last_activity: Optional[str] = None


class AuthRequest(BaseModel):
    """
    Authentication request model for login endpoints.
    """
    email: EmailStr
    password: str
    remember_me: bool = False


class AuthResponse(BaseModel):
    """
    Authentication response model for login endpoints.
    """
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: int  # seconds
    user: User
    tenant: Tenant


class RefreshTokenRequest(BaseModel):
    """
    Refresh token request model.
    """
    refresh_token: str


class PasswordResetRequest(BaseModel):
    """
    Password reset request model.
    """
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """
    Password reset confirmation model.
    """
    token: str
    new_password: str
    confirm_password: str