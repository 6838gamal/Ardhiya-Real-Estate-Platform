"""Auth module services."""
import secrets
import time
import base64
import logging
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
from app.modules.auth.models import UserSession
from app.modules.auth.schemas import (
    GoogleUserInfo, TokenResponse, GoogleTokenExchange,
    GoogleJWKSResponse
)
from app.modules.users.schemas import UserCreate, UserUpdate
from app.modules.users.services import UserService

# إعداد التسجيل
logger = logging.getLogger(__name__)


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
            logger.error(f"❌ State mismatch! Received: {state[:10]}..., Stored: {stored_state[:10]}...")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid state parameter"
            )

        logger.info("✅ State validated successfully")

        # Exchange code for tokens
        tokens = await self._exchange_code_for_tokens(code)

        # Verify ID token with access_token
        user_info = await self._verify_id_token(tokens.id_token, tokens.access_token)

        # Create or update user
        user = await self._get_or_create_user(user_info)

        # Create session
        session = self.session_service.create_session(
            user_id=user.id,
            ip_address=ip_address,
            user_agent=user_agent
        )

        logger.info(f"✅ Session created for user: {user.email}")

        return {
            "user": user,
            "session": session,
            "access_token": tokens.access_token
        }

    async def _exchange_code_for_tokens(self, code: str) -> TokenResponse:
        """
        Exchange authorization code for tokens using Basic Authentication.
        
        تستخدم هذه الطريقة Basic Auth لتجنب مشكلة "Could not determine client ID"
        """
        try:
            # ✅ التأكد من أن القيم موجودة
            if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
                logger.error("❌ GOOGLE_CLIENT_ID or GOOGLE_CLIENT_SECRET is not set!")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Google OAuth credentials not configured"
                )

            # ✅ التأكد من أن redirect_uri موجود
            if not settings.GOOGLE_REDIRECT_URI:
                logger.error("❌ GOOGLE_REDIRECT_URI is not set!")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Google OAuth redirect URI not configured"
                )

            # ✅ إنشاء Basic Auth header
            credentials = f"{settings.GOOGLE_CLIENT_ID}:{settings.GOOGLE_CLIENT_SECRET}"
            encoded_credentials = base64.b64encode(credentials.encode()).decode()

            logger.info(f"🔑 Using Basic Auth for token exchange")
            logger.info(f"🔑 GOOGLE_CLIENT_ID: {settings.GOOGLE_CLIENT_ID[:20]}...")
            logger.info(f"🔑 GOOGLE_REDIRECT_URI: {settings.GOOGLE_REDIRECT_URI}")

            # ✅ البيانات بدون client_id و client_secret (موجودة في الـ Auth header)
            token_data = {
                "code": code,
                "redirect_uri": settings.GOOGLE_REDIRECT_URI,
                "grant_type": "authorization_code",
            }

            logger.info(f"📤 Sending token exchange request with Basic Auth")

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "https://oauth2.googleapis.com/token",
                    data=token_data,
                    headers={
                        "Content-Type": "application/x-www-form-urlencoded",
                        "Authorization": f"Basic {encoded_credentials}"
                    }
                )

            logger.info(f"📥 Response status: {response.status_code}")

            if response.status_code != 200:
                logger.error(f"❌ Token exchange failed: {response.text}")
                
                # محاولة تحليل الخطأ
                try:
                    error_data = response.json()
                    error_msg = error_data.get("error_description", error_data.get("error", "Unknown error"))
                except:
                    error_msg = response.text[:200]
                
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Token exchange failed: {error_msg}"
                )

            # ✅ تسجيل نجاح التبادل
            logger.info("✅ Token exchange successful")
            return TokenResponse(**response.json())

        except httpx.TimeoutException:
            logger.error("❌ Token exchange timeout")
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="Token exchange timeout"
            )
        except httpx.RequestError as e:
            logger.error(f"❌ Request error during token exchange: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Token exchange failed: {str(e)}"
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"❌ Unexpected error during token exchange: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Token exchange failed: {str(e)}"
            )

    async def _verify_id_token(self, id_token: str, access_token: str) -> GoogleUserInfo:
        """Verify Google ID token using JWKS with access_token for at_hash verification."""
        try:
            # Get Google's JWKS
            jwks = await self._get_google_jwks()

            # Decode and verify token
            unverified = jwt.get_unverified_header(id_token)
            key = self._find_matching_key(jwks, unverified["kid"])

            # Verify token with access_token for at_hash
            claims = jwt.decode(
                id_token,
                key,
                algorithms=["RS256"],
                audience=settings.GOOGLE_CLIENT_ID,
                issuer="https://accounts.google.com",
                access_token=access_token
            )

            logger.info(f"✅ ID token verified for user: {claims.get('email', 'unknown')}")
            return GoogleUserInfo(**claims)

        except JWTError as e:
            logger.error(f"❌ JWT verification failed: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid ID token: {str(e)}"
            )
        except Exception as e:
            logger.error(f"❌ Unexpected error verifying ID token: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to verify ID token: {str(e)}"
            )

    async def _get_google_jwks(self) -> GoogleJWKSResponse:
        """Fetch Google's JWKS."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    "https://www.googleapis.com/oauth2/v3/certs"
                )

            if response.status_code != 200:
                logger.error(f"❌ Failed to fetch JWKS: {response.status_code}")
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Unable to fetch Google JWKS"
                )

            return GoogleJWKSResponse(**response.json())
        except httpx.TimeoutException:
            logger.error("❌ JWKS fetch timeout")
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="JWKS fetch timeout"
            )
        except Exception as e:
            logger.error(f"❌ Failed to fetch JWKS: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Unable to fetch Google JWKS: {str(e)}"
            )

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
        try:
            # ✅ البحث عن المستخدم بواسطة oauth_id
            user = self.user_service.get_user_by_oauth_id(
                oauth_id=user_info.sub,
                oauth_provider="google"
            )
            
            # ✅ إذا لم يتم العثور، حاول البحث بالبريد الإلكتروني
            if not user:
                user = self.user_service.get_user_by_email(user_info.email)
                if user:
                    # ✅ تحديث oauth_id للمستخدم الموجود
                    user.oauth_id = user_info.sub
                    user.oauth_provider = "google"
                    self.db.commit()
                    self.db.refresh(user)
                    logger.info(f"✅ Updated existing user with OAuth ID: {user_info.email}")
            
            if not user:
                # ✅ إنشاء مستخدم جديد
                user_data = UserCreate(
                    email=user_info.email,
                    name=user_info.name or user_info.given_name or user_info.email,
                    oauth_provider="google",
                    oauth_id=user_info.sub,
                    is_active=True,
                    is_verified=True
                )
                user = self.user_service.create_user(user_data)
                logger.info(f"✅ Created new user: {user_info.email}")
            else:
                # ✅ تحديث معلومات المستخدم إذا كانت مختلفة
                updated = False
                if user.name != user_info.name and user_info.name:
                    user.name = user_info.name
                    updated = True
                if user.oauth_id != user_info.sub:
                    user.oauth_id = user_info.sub
                    user.oauth_provider = "google"
                    updated = True
                if updated:
                    self.db.commit()
                    self.db.refresh(user)
                    logger.info(f"✅ Updated user info: {user_info.email}")
            
            return user

        except Exception as e:
            logger.error(f"❌ Failed to get or create user: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to process user: {str(e)}"
            )


class SessionService:
    """Session CRUD, expiry checks, revocation."""

    def __init__(self, db: Session):
        self.db = db
        self.signer = URLSafeTimedSerializer(
            settings.SECRET_KEY,
            salt="session-token"
        )

    def create_session(
        self, 
        user_id: int, 
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> UserSession:
        """Create a new session."""
        try:
            # Generate session token
            raw_token = secrets.token_urlsafe(32)
            signed_token = self.signer.dumps(raw_token)

            # Calculate expiry
            expires_at = datetime.utcnow() + timedelta(
                minutes=settings.SESSION_EXPIRE_MINUTES
            )

            session = UserSession(
                user_id=user_id,
                token=signed_token,
                expires_at=expires_at,
                ip_address=ip_address,
                user_agent=user_agent,
                is_revoked=False
            )

            self.db.add(session)
            self.db.commit()
            self.db.refresh(session)

            logger.info(f"✅ Session created for user_id: {user_id}")
            return session

        except Exception as e:
            logger.error(f"❌ Failed to create session: {str(e)}")
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create session: {str(e)}"
            )

    def get_session(self, token: str) -> Optional[UserSession]:
        """Get session by token."""
        try:
            # Verify signature and extract raw token
            raw_token = self.signer.loads(token)
        except BadSignature:
            logger.warning(f"⚠️ Invalid session token signature")
            return None

        session = self.db.query(UserSession).filter(
            UserSession.token == token,
            UserSession.is_revoked == False
        ).first()

        if not session:
            logger.warning(f"⚠️ Session not found or revoked")
            return None

        if session.is_expired():
            logger.warning(f"⚠️ Session expired")
            return None

        return session

    def revoke_session(self, session_id: int) -> bool:
        """Revoke a session."""
        try:
            session = self.db.query(UserSession).filter(
                UserSession.id == session_id
            ).first()

            if not session:
                logger.warning(f"⚠️ Session not found: {session_id}")
                return False

            session.is_revoked = True
            self.db.commit()
            logger.info(f"✅ Session revoked: {session_id}")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to revoke session: {str(e)}")
            self.db.rollback()
            return False

    def revoke_all_user_sessions(self, user_id: int) -> int:
        """Revoke all sessions for a user."""
        try:
            sessions = self.db.query(UserSession).filter(
                UserSession.user_id == user_id,
                UserSession.is_revoked == False
            ).all()

            for session in sessions:
                session.is_revoked = True

            self.db.commit()
            logger.info(f"✅ Revoked {len(sessions)} sessions for user_id: {user_id}")
            return len(sessions)

        except Exception as e:
            logger.error(f"❌ Failed to revoke sessions: {str(e)}")
            self.db.rollback()
            return 0

    def cleanup_expired_sessions(self) -> int:
        """Delete expired sessions."""
        try:
            expired = self.db.query(UserSession).filter(
                UserSession.expires_at < datetime.utcnow()
            ).delete()

            self.db.commit()
            logger.info(f"🧹 Cleaned up {expired} expired sessions")
            return expired

        except Exception as e:
            logger.error(f"❌ Failed to cleanup sessions: {str(e)}")
            self.db.rollback()
            return 0

    def extend_session(self, session_id: int) -> bool:
        """Extend session expiry."""
        try:
            session = self.db.query(UserSession).filter(
                UserSession.id == session_id
            ).first()

            if not session or session.is_revoked:
                logger.warning(f"⚠️ Cannot extend session: not found or revoked")
                return False

            session.expires_at = datetime.utcnow() + timedelta(
                minutes=settings.SESSION_EXPIRE_MINUTES
            )
            self.db.commit()
            logger.info(f"✅ Session extended: {session_id}")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to extend session: {str(e)}")
            self.db.rollback()
            return False


class TokenService:
    """JWT creation/verification for API access (future)."""

    def create_api_token(self, user_id: int, role: str) -> str:
        """Create JWT for API access."""
        try:
            payload = {
                "sub": str(user_id),
                "role": role,
                "iat": datetime.utcnow(),
                "exp": datetime.utcnow() + timedelta(
                    minutes=settings.JWT_EXPIRE_MINUTES
                )
            }
            token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
            logger.info(f"✅ API token created for user_id: {user_id}")
            return token

        except Exception as e:
            logger.error(f"❌ Failed to create API token: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create token: {str(e)}"
            )

    def verify_api_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify JWT token."""
        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM]
            )
            return payload
        except JWTError as e:
            logger.warning(f"⚠️ Invalid API token: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"❌ Failed to verify API token: {str(e)}")
            return None
