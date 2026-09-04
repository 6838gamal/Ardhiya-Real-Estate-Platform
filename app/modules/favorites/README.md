# Favorites Module — Architecture Contract

> **Status:** Not Implemented. This document defines the future architecture.

## Purpose

Allow buyers to save properties they are interested in for later viewing. Simple many-to-many relationship between users and properties.

## Responsibilities

- Add property to favorites
- Remove property from favorites
- List user's favorited properties
- Check if a property is favorited (for UI state)
- Favorite count per property (display)

## Future Models

```python
class Favorite:
    id: int
    user_id: int        # FK → users.id
    property_id: int    # FK → properties.id
    created_at: datetime

    # Unique constraint: (user_id, property_id)
```

## Future Schemas

```python
class FavoriteToggleResponse(BaseModel):
    favorited: bool
    count: int

class FavoriteListResponse(BaseModel):
    items: list[PropertyResponse]
    total: int
    page: int
    per_page: int
```

## Future Services

- `FavoriteService` — add, remove, list, toggle, count

## Future Routes / API

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/api/favorites` | List user's favorites | Buyer |
| POST | `/api/properties/{id}/favorite` | Add to favorites | Buyer |
| DELETE | `/api/properties/{id}/favorite` | Remove from favorites | Buyer |
| GET | `/api/properties/{id}/favorite` | Check if favorited | Buyer |

## Dependencies

- **users** module — user identity
- **properties** module — property existence and status

## Permissions

| Role | Access |
|------|--------|
| Anonymous | No access |
| Buyer | Full access to own favorites |
| Owner | Can favorite properties too (dual role) |
| Admin | No special access (favorites are personal) |

## Business Rules

- Only `published` properties can be favorited
- A user can favorite a property only once (unique constraint)
- Removing a non-existent favorite is a no-op (idempotent)
- Favorites are private — only the user sees their own
- Favorite count is public (shown on property card/detail)
- When a property is sold/deleted, it remains in favorites but marked as unavailable

## Future Extensions

- Favorite collections/folders (e.g., "Beach Houses", "Investments")
- Favorite sharing (public wish lists)
- Email notifications when a favorited property price changes
- Export favorites to PDF/CSV
- Notes on favorited properties
