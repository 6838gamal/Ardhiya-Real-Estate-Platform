# Auth Module — Architecture Contract

> **Status:** Not Implemented. This document defines the future architecture.

## Purpose

Handle user authentication and authorization via **Google OAuth 2.0 / OpenID Connect**. No username/password or email/password authentication — Google Login is the sole identity provider.

## Responsibilities

- Google OAuth 2.0 login flow (Authorization Code + PKCE)
- OpenID Connect ID token verification
- Session management (server-side sessions via signed cookies)
- JWT issuance for API access (future)
- Role-based authorization (Owner, Buyer, Admin)
- Session persistence and expiry

## Future Models

```python
class UserSession:
    id: int
    user_id: int          # FK → users.id
    session_token: str    # signed, opaque token
    provider: str         # "google"
    provider_user_id: str # Google sub claim
    expires_at: datetime
    created_at: datetime
    ip_address: str | None
    user_agent: str | None
```

## Future Schemas

```python
class GoogleLoginURLResponse(BaseModel):
    auth_url: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int

class SessionResponse(BaseModel):
    user_id: int
    role: str
    expires_at: datetime
```

## Future Services

- `AuthService` — orchestrates OAuth flow, token exchange, session creation
- `TokenService` — JWT creation/verification (future API access)
- `SessionService` — session CRUD, expiry checks, revocation

## Future Routes / API

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/auth/login` | Redirect to Google consent screen | Public |
| GET | `/auth/callback` | OAuth callback, code exchange | Public |
| POST | `/auth/logout` | Destroy session, clear cookie | Required |
| GET | `/auth/me` | Current user info from session | Required |

## Google OAuth Flow

```
1. User clicks "Login with Google"
2. App redirects to Google consent URL:
   GET https://accounts.google.com/o/oauth2/v2/auth?
       client_id={CLIENT_ID}
       &redirect_uri={REDIRECT_URI}
       &response_type=code
       &scope=openid email profile
       &state={CSRF_STATE}

3. Google redirects back to /auth/callback?code=...&state=...
4. App exchanges code for tokens:
   POST https://oauth2.googleapis.com/token
   Body: code, client_id, client_secret, redirect_uri, grant_type=authorization_code

5. App verifies ID token (JWT) from Google:
   - Verify signature using Google's JWKS
   - Validate iss, aud, exp, iat claims
   - Extract sub (Google user ID), email, name, picture

6. App creates or updates user in users module
7. App creates server-side session (signed cookie)
8. Redirect to dashboard or original page
```

## Dependencies

- **users** module — user creation/lookup after OAuth
- `httpx` — outbound HTTP calls to Google
- `itsdangerous` — signed session cookies
- PyJWT or `python-jose` — JWT handling (future)

## Permissions

| Role | Access |
|------|--------|
| Anonymous | Can initiate login, view callback |
| Authenticated | Can logout, view own session |
| Admin | Can revoke any session (future) |

## Business Rules

- Only Google is supported as identity provider
- Email from Google is always verified (no email confirmation needed)
- First-time login creates a user with role `buyer` by default
- Sessions expire after 24 hours (configurable via `JWT_EXPIRE_MINUTES`)
- `state` parameter must match between request and callback (CSRF protection)

## Future Extensions

- Additional OAuth providers (Apple, Microsoft)
- Multi-factor authentication
- Session management dashboard (view active sessions, revoke)
- API key issuance for programmatic access
- Rate limiting on auth endpoints
