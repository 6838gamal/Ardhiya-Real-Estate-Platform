"""User Pydantic schemas for validation and serialization."""

from datetime import datetime
from typing import Optional, Literal, List
from pydantic import BaseModel, EmailStr, Field, ConfigDict


# ============ Request Schemas ============

class UserCreate(BaseModel):
    """Schema for creating a new user (via Google OAuth)."""
    email: EmailStr = Field(..., description="User email (from Google)")
    name: str = Field(..., min_length=1, max_length=255, description="User full name")
    avatar_url: Optional[str] = Field(None, max_length=500, description="Profile picture URL")
    role: Literal["owner", "buyer", "admin"] = Field("buyer", description="User role")
    
    model_config = ConfigDict(from_attributes=True)


class UserUpdate(BaseModel):
    """Schema for updating user profile."""
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="User full name")
    phone: Optional[str] = Field(None, max_length=20, description="Phone number")
    bio: Optional[str] = Field(None, max_length=500, description="Short bio")
    avatar_url: Optional[str] = Field(None, max_length=500, description="Profile picture URL")
    
    model_config = ConfigDict(from_attributes=True)


class UserProfileUpdate(BaseModel):
    """Schema for updating user preferences."""
    preferred_language: Optional[Literal["ar", "en"]] = Field(None, description="Preferred language")
    preferred_currency: Optional[Literal["SAR", "USD", "AED"]] = Field(None, description="Preferred currency")
    notifications_enabled: Optional[bool] = Field(None, description="Enable notifications")
    marketing_emails: Optional[bool] = Field(None, description="Receive marketing emails")
    
    model_config = ConfigDict(from_attributes=True)


class RoleUpdate(BaseModel):
    """Schema for updating user role (admin only)."""
    role: Literal["owner", "buyer", "admin"] = Field(..., description="New user role")
    
    model_config = ConfigDict(from_attributes=True)


# ============ Response Schemas ============

class UserProfileResponse(BaseModel):
    """User profile settings response."""
    preferred_language: str
    preferred_currency: str
    notifications_enabled: bool
    marketing_emails: bool
    created_at: datetime
    updated_at: Optional[datetime]
    
    model_config = ConfigDict(from_attributes=True)


class UserResponse(BaseModel):
    """User information response (public fields)."""
    id: int
    email: str
    name: str
    avatar_url: Optional[str]
    phone: Optional[str]
    role: str
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]
    profile: Optional[UserProfileResponse] = None
    
    model_config = ConfigDict(from_attributes=True)


class UserListResponse(BaseModel):
    """Paginated list of users response."""
    items: List[UserResponse]
    total: int
    page: int
    per_page: int
    total_pages: int
    
    model_config = ConfigDict(from_attributes=True)


class UserMeResponse(UserResponse):
    """Current user response (includes full profile)."""
    pass


# ============ Error Schemas ============

class UserNotFoundError(BaseModel):
    """Error when user is not found."""
    detail: str = "User not found"
    user_id: Optional[int] = None


class UserAlreadyExistsError(BaseModel):
    """Error when user already exists."""
    detail: str = "User already exists"
    email: Optional[str] = None
