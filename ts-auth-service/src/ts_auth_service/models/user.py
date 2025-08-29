"""User data models."""

from datetime import datetime
from typing import Optional, Literal
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field, validator
import re


class UserBase(BaseModel):
    """Base user model with common fields."""
    
    email: EmailStr = Field(..., description="User email address")
    first_name: str = Field(..., min_length=1, max_length=100, description="User first name")
    last_name: str = Field(..., min_length=1, max_length=100, description="User last name")


class UserRegistration(UserBase):
    """User registration request model."""
    
    password: str = Field(..., min_length=8, description="User password")
    business_name: str = Field(..., min_length=1, max_length=255, description="Business name")
    
    @validator("password")
    def validate_password(cls, v):
        """Validate password strength."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        
        if not re.search(r"[A-Za-z]", v):
            raise ValueError("Password must contain at least one letter")
        
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one number")
        
        return v


class UserLogin(BaseModel):
    """User login request model."""
    
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., description="User password")


class User(UserBase):
    """Complete user entity model."""
    
    id: UUID = Field(..., description="User ID")
    password_hash: str = Field(..., description="Hashed password")
    tenant_id: Optional[UUID] = Field(None, description="Associated tenant ID")
    role: Literal['owner', 'operator', 'viewer'] = Field(default='owner', description="User role")
    email_verified: bool = Field(default=False, description="Email verification status")
    is_active: bool = Field(default=True, description="User active status")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    last_login_at: Optional[datetime] = Field(None, description="Last login timestamp")
    
    class Config:
        from_attributes = True


class UserResponse(UserBase):
    """User response model (no sensitive data)."""
    
    id: UUID
    tenant_id: Optional[UUID] = None
    role: str = "owner"
    email_verified: bool = False
    is_active: bool = True
    last_login_at: Optional[datetime] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class UserSession(BaseModel):
    """User session model."""
    
    id: UUID = Field(..., description="Session ID")
    user_id: UUID = Field(..., description="User ID")
    refresh_token: str = Field(..., description="Refresh token")
    device_info: Optional[str] = Field(None, max_length=500, description="Device information")
    ip_address: Optional[str] = Field(None, description="IP address")
    expires_at: datetime = Field(..., description="Session expiry time")
    is_active: bool = Field(default=True, description="Session active status")
    created_at: datetime = Field(..., description="Creation timestamp")
    
    class Config:
        from_attributes = True


class JWTPayload(BaseModel):
    """JWT token payload model."""
    
    sub: str = Field(..., description="Subject (user ID)")
    email: str = Field(..., description="User email")
    tenant_id: Optional[str] = Field(None, description="Tenant ID")
    role: str = Field(..., description="User role")
    iat: int = Field(..., description="Issued at timestamp")
    exp: int = Field(..., description="Expiration timestamp")


class TokenPair(BaseModel):
    """Token pair response model."""
    
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="Refresh token")
    expires_in: int = Field(..., description="Access token expiry in seconds")
    token_type: str = Field(default="bearer", description="Token type")


class RefreshTokenRequest(BaseModel):
    """Refresh token request model."""
    
    refresh_token: str = Field(..., description="Refresh token")


class TokenValidationRequest(BaseModel):
    """Token validation request model."""
    
    token: str = Field(..., description="JWT token to validate")


class UserUpdate(BaseModel):
    """User update model."""
    
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[EmailStr] = None
    
    @validator("*", pre=True)
    def empty_str_to_none(cls, v):
        """Convert empty strings to None."""
        if v == "":
            return None
        return v


class PasswordChangeRequest(BaseModel):
    """Password change request model."""
    
    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=8, description="New password")
    
    @validator("new_password")
    def validate_new_password(cls, v):
        """Validate new password strength."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        
        if not re.search(r"[A-Za-z]", v):
            raise ValueError("Password must contain at least one letter")
        
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one number")
        
        return v