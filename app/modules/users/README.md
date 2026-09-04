# Users Module — Architecture Contract

> **Status:** Not Implemented. This document defines the future architecture.

## Purpose

Manage user accounts, profiles, and roles. Users are created automatically upon Google OAuth login. Three roles exist: **Owner** (lists properties), **Buyer** (searches and inquires), and **Admin** (manages platform).

## Responsibilities

- User creation and profile management
- Role assignment and transitions
- Profile data (name, phone, avatar, bio)
- User lookup and search (admin)
- Account deactivation

## Future Models

```python
class User:
    id: int
    email: str               # unique, from Google
    name: str
    avatar_url: str | None
    phone: str | None
    bio: str | None
    role: str                # "owner" | "buyer" | "admin"
    is_active: bool
    last_login: datetime | None
    created_at: datetime
    updated_at: datetime

class UserProfile:
    user_id: int             # FK → users.id
    preferred_language: str  # "ar" | "en"
    preferred_currency: str  # "SAR" | "USD" | "AED"
    notifications_enabled: bool
    marketing_emails: bool
```

## Future Schemas

```python
class UserCreate(BaseModel):
    email: EmailStr
    name: str
    avatar_url: str | None = None

class UserUpdate(BaseModel):
    name: str | None = None
    phone: str | None = None
    bio: str | None = None
    avatar_url: str | None = None

class UserResponse(BaseModel):
    id: int
    email: str
    name: str
    avatar_url: str | None
    phone: str | None
    role: str
    is_active: bool
    created_at: datetime

class RoleUpdate(BaseModel):
    role: Literal["owner", "buyer", "admin"]
```

## Future Services

- `UserService` — CRUD, profile updates, role changes
- `UserQueryService` — search, filter, pagination (admin)

## Future Routes / API

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/api/users/me` | Current user profile | Required |
| PUT | `/api/users/me` | Update own profile | Required |
| GET | `/api/users/{id}` | View user (public fields) | Required |
| GET | `/api/users` | List users (paginated) | Admin |
| PUT | `/api/users/{id}/role` | Change user role | Admin |
| DELETE | `/api/users/{id}` | Deactivate user | Admin |

## Dependencies

- **auth** module — creates users on first login
- **properties** module — owners have properties
- **favorites** module — buyers have favorites
- **inquiries** module — buyers send inquiries

## Permissions

| Role | Access |
|------|--------|
| Anonymous | No access |
| Buyer | View own profile, edit own profile |
| Owner | View own profile, edit own profile |
| Admin | All operations, role changes, deactivation |

## Business Rules

- Email is immutable (comes from Google, always verified)
- A user can be both an owner and a buyer (role = primary role)
- Role `admin` can only be assigned by another admin
- Deactivation is soft-delete (`is_active = false`), not hard delete
- Phone number is optional but required before listing a property
- Avatar URL comes from Google profile, can be overridden

## Future Extensions

- User verification badges (phone, ID verification)
- User ratings and reviews
- User activity log
- Export user data (GDPR compliance)
- Account merge (multiple Google accounts → one user)
