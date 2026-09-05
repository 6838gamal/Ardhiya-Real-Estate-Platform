"""Auth module Pydantic schemas."""
from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, field_validator


# ============ OAuth Schemas ============

class AuthInitResponse(BaseModel):
    """Response for initiating OAuth login."""
    oauth_url: str
    state: str


class AuthCallbackRequest(BaseModel):
    """Request for OAuth callback."""
    code: str
    state: str


class AuthCallbackResponse(BaseModel):
    """Response for OAuth callback."""
    success: bool
    user: Optional["AuthUserResponse"] = None
    access_token: Optional[str] = None
    message: Optional[str] = None


class AuthUserResponse(BaseModel):
    """User data in auth responses."""
    id: int
    email: EmailStr
    name: str
    role: str
    picture: Optional[str] = None
    
    model_config = {"from_attributes": True}


class LogoutResponse(BaseModel):
    """Response for logout."""
    success: bool
    message: Optional[str] = None


class SessionResponse(BaseModel):
    """Session information response."""
    user_id: int
    expires_at: datetime
    created_at: datetime


# ============ Google OAuth Schemas ============

class GoogleUserInfo(BaseModel):
    """Google user info from ID token."""
    sub: str
    email: EmailStr
    email_verified: bool = False
    name: Optional[str] = None
    given_name: Optional[str] = None
    family_name: Optional[str] = None
    picture: Optional[str] = None
    locale: Optional[str] = None


class TokenResponse(BaseModel):
    """Response from Google OAuth token exchange."""
    access_token: str
    expires_in: int
    id_token: str
    scope: str
    token_type: str
    refresh_token: Optional[str] = None


class GoogleTokenExchange(BaseModel):
    """Request data for Google OAuth token exchange (Backend only)."""
    code: str
    redirect_uri: str
    grant_type: str = "authorization_code"
    # ملاحظة: client_id و client_secret تؤخذ من متغيرات البيئة في الـ backend
    # ولا ترسل من frontend لأسباب أمنية


class GoogleJWK(BaseModel):
    """Google JWK key."""
    kty: str
    kid: str
    use: str
    alg: str
    n: str
    e: str


class GoogleJWKSResponse(BaseModel):
    """Google JWKS response."""
    keys: list[GoogleJWK]


# ============ Session Schemas ============

class SessionCreate(BaseModel):
    """Create session request."""
    user_id: int
    #ip_address: Optional[str] = None
   # user_agent: Optional[str] = None


class SessionUpdate(BaseModel):
    """Update session request."""
    expires_at: Optional[datetime] = None
    is_revoked: Optional[bool] = None


# ============ Token Schemas ============

class TokenPayload(BaseModel):
    """JWT token payload."""
    sub: str
    role: str
    exp: datetime = Field(..., description="Expiration time (UTC)")
    iat: datetime = Field(..., description="Issued at time (UTC)")

    @field_validator("exp", "iat", mode="before")
    @classmethod
    def ensure_utc(cls, v):
        """Ensure datetime has UTC timezone."""
        if isinstance(v, datetime) and v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v


class TokenData(BaseModel):
    """Token data for requests."""
    user_id: int
    role: str


# ============ Auth Error Schemas ============

class AuthErrorResponse(BaseModel):
    """Auth error response."""
    success: bool = False
    detail: str
    error_code: Optional[str] = None
    status_code: Optional[int] = None


# ============ Update forward references ============

# تحديث الـ forward references
AuthCallbackResponse.model_rebuild()
