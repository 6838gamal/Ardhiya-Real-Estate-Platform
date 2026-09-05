"""Auth module services."""
import secrets
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from urllib.parse import urlencode
import json

import httpx
from itsdangerous import URLSafeTimedSerializer, BadSignature
from jose import jwt, jwk
from jose.exceptions import JWTError
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.config.settings import settings
from app.modules.auth.models import UserSession  # ✅ استيراد من auth.models
from app.modules.auth.schemas import (
    GoogleUserInfo, TokenResponse, GoogleTokenExchange,
    GoogleJWKSResponse
)
from app.modules.users.schemas import UserCreate, UserUpdate
from app.modules.users.services import UserService


class AuthService:
    """Orchestrates OAuth flow, token exchange, session creation."""

    def __init__(self, db: Session):
        self.db = db
        self.user_service = UserService(db)
        self.session_service = SessionService(db)
        self.token_service = TokenService()

    def generate_oauth_url(self, state: str) -> str:
        """Generate Google OAuth URL with PKCE."""
        params = {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "redirect_uri": settings.GOOGLE_REDIRECT_URI,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "access_type": "online",
            "prompt": "select_account"
        }
        return f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"

    async def handle_callback(self, code: str, state: str, stored_state: str,
                              ip_address: Optional[str] = None,
                              user_agent: Optional[str] = None) -> Dict[str, Any]:
        """Handle OAuth callback and create session."""
        # Verify state for CSRF protection
        if state != stored_state:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid state parameter"
            )

        # Exchange code for tokens
        tokens = await self._exchange_code_for_tokens(code)

        # Verify ID token
        user_info = await self._verify_id_token(tokens.id_token)

        # Create or update user
        user = await self._get_or_create_user(user_info)

        # Create session
        session = self.session_service.create_session(
            user_id=user.id,
            provider_user_id=user_info.sub,
            ip_address=ip_address,
            user_agent=user_agent
        )

        return {
            "user": user,
            "session": session,
            "access_token": tokens.access_token
        }

    async def _exchange_code_for_tokens(self, code: str) -> TokenResponse:
        """Exchange authorization code for tokens."""
        token_data = GoogleTokenExchange(
            code=code,
            client_id=settings.GOOGLE_CLIENT_ID,
            client_secret=settings.GOOGLE_CLIENT_SECRET,
            redirect_uri=settings.GOOGLE_REDIRECT_URI
        )

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://oauth2.googleapis.com/token",
                data=token_data.model_dump()
            )

        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Token exchange failed: {response.text}"
            )

        return TokenResponse(**response.json())

    async def _verify_id_token(self, id_token: str) -> GoogleUserInfo:
        """Verify Google ID token using JWKS."""
        try:
            # Get Google's JWKS
            jwks = await self._get_google_jwks()

            # Decode and verify token
            unverified = jwt.get_unverified_header(id_token)
            key = self._find_matching_key(jwks, unverified["kid"])

            # Verify token
            claims = jwt.decode(
                id_token,
                key,
                algorithms=["RS256"],
                audience=settings.GOOGLE_CLIENT_ID,
                issuer="https://accounts.google.com"
            )

            return GoogleUserInfo(**claims)

        except JWTError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid ID token: {str(e)}"
            )

    async def _get_google_jwks(self) -> GoogleJWKSResponse:
        """Fetch Google's JWKS."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://www.googleapis.com/oauth2/v3/certs"
            )

        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Unable to fetch Google JWKS"
            )

        return GoogleJWKSResponse(**response.json())

    def _find_matching_key(self, jwks: GoogleJWKSResponse, kid: str) -> Dict[str, Any]:
        """Find matching key from JWKS by kid."""
        for key in jwks.keys:
            if key.get("kid") == kid:
                return key
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No matching JWK found"
        )

    async def _get_or_create_user(self, user_info: GoogleUserInfo) -> Any:
        """Get or create user from Google user info."""
        user = self.user_service.get_user_by_provider_id(
            provider="google",
            provider_user_id=user_info.sub
        )

        if not user:
            user_data = UserCreate(
                email=user_info.email,
                name=user_info.name or user_info.given_name or user_info.email,
                provider="google",
                provider_user_id=user_info.sub,
                is_active=True,
                is_verified=True
            )
            user = self.user_service.create_user(user_data)

        # Update user info if needed
        if user.name != user_info.name and user_info.name:
            user.name = user_info.name
            self.db.commit()
            self.db.refresh(user)

        return user


class SessionService:
    """Session CRUD, expiry checks, revocation."""

    def __init__(self, db: Session):
        self.db = db
        self.signer = URLSafeTimedSerializer(
            settings.SECRET_KEY,
            salt="session-token"
        )

    def create_session(self, user_id: int, provider_user_id: str,
                       ip_address: Optional[str] = None,
                       user_agent: Optional[str] = None) -> UserSession:
        """Create a new session."""
        # Generate session token
        raw_token = secrets.token_urlsafe(32)
        signed_token = self.signer.dumps(raw_token)

        # Calculate expiry
        expires_at = datetime.utcnow() + timedelta(
            minutes=settings.JWT_EXPIRE_MINUTES
        )

        session = UserSession(
            user_id=user_id,
            token=signed_token,  # ✅ استخدام 'token' بدلاً من 'session_token'
            provider="google",
            provider_user_id=provider_user_id,
            expires_at=expires_at,
            ip_address=ip_address,
            user_agent=user_agent,
            is_revoked=False
        )

        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)

        return session

    def get_session(self, token: str) -> Optional[UserSession]:
        """Get session by token."""
        try:
            # Verify signature and extract raw token
            raw_token = self.signer.loads(token)
        except BadSignature:
            return None

        session = self.db.query(UserSession).filter(
            UserSession.token == token,  # ✅ استخدام 'token' بدلاً من 'session_token'
            UserSession.is_revoked == False  # ✅ Boolean بدلاً من 0
        ).first()

        if not session or session.is_expired():
            return None

        return session

    def revoke_session(self, session_id: int) -> bool:
        """Revoke a session."""
        session = self.db.query(UserSession).filter(
            UserSession.id == session_id
        ).first()

        if not session:
            return False

        session.is_revoked = True  # ✅ Boolean بدلاً من 1
        self.db.commit()
        return True

    def revoke_all_user_sessions(self, user_id: int) -> int:
        """Revoke all sessions for a user."""
        sessions = self.db.query(UserSession).filter(
            UserSession.user_id == user_id,
            UserSession.is_revoked == False  # ✅ Boolean بدلاً من 0
        ).all()

        for session in sessions:
            session.is_revoked = True  # ✅ Boolean بدلاً من 1

        self.db.commit()
        return len(sessions)

    def cleanup_expired_sessions(self) -> int:
        """Delete expired sessions."""
        expired = self.db.query(UserSession).filter(
            UserSession.expires_at < datetime.utcnow()
        ).delete()

        self.db.commit()
        return expired

    def extend_session(self, session_id: int) -> bool:
        """Extend session expiry."""
        session = self.db.query(UserSession).filter(
            UserSession.id == session_id
        ).first()

        if not session or session.is_revoked:
            return False

        session.expires_at = datetime.utcnow() + timedelta(
            minutes=settings.JWT_EXPIRE_MINUTES
        )
        self.db.commit()
        return True


class TokenService:
    """JWT creation/verification for API access (future)."""

    def create_api_token(self, user_id: int, role: str) -> str:
        """Create JWT for API access."""
        payload = {
            "sub": str(user_id),
            "role": role,
            "iat": datetime.utcnow(),
            "exp": datetime.utcnow() + timedelta(
                minutes=settings.JWT_EXPIRE_MINUTES
            )
        }
        return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")

    def verify_api_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify JWT token."""
        try:
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=["HS256"]
            )
            return payload
        except JWTError:
            return None
