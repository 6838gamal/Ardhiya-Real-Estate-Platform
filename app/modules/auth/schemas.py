"""Auth module Pydantic schemas."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class GoogleUserInfo(BaseModel):
    """Google OAuth user info from ID token."""
    sub: str  # Google user ID
    email: EmailStr
    email_verified: bool = False
    name: Optional[str] = None
    given_name: Optional[str] = None
    family_name: Optional[str] = None
    picture: Optional[str] = None
    locale: Optional[str] = None


class GoogleLoginURLResponse(BaseModel):
    """Response with Google OAuth URL."""
    auth_url: str


class TokenResponse(BaseModel):
    """Response for token exchange."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    refresh_token: Optional[str] = None
    id_token: Optional[str] = None


class SessionResponse(BaseModel):
    """Session information response."""
    user_id: int
    role: str
    email: str
    name: Optional[str] = None
    expires_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True


class AuthCallbackRequest(BaseModel):
    """Request for OAuth callback."""
    code: str
    state: str


class LogoutRequest(BaseModel):
    """Request for logout."""
    session_token: str


class UserInfoResponse(BaseModel):
    """Current user info response."""
    user_id: int
    email: str
    name: Optional[str] = None
    role: str
    picture: Optional[str] = None
    is_authenticated: bool = True

    class Config:
        from_attributes = True


class GoogleTokenExchange(BaseModel):
    """Google token exchange request."""
    code: str
    client_id: str
    client_secret: str
    redirect_uri: str
    grant_type: str = "authorization_code"


class GoogleJWKSResponse(BaseModel):
    """Google JWKS response."""
    keys: list[dict]


class ErrorResponse(BaseModel):
    """Error response model."""
    error: str
    detail: Optional[str] = None
    status_code: int
