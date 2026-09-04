# Admin Module — Architecture Contract

> **Status:** Not Implemented. This document defines the future architecture.

## Purpose

Administrative panel for platform management. Admins review and approve properties, manage users, view statistics, and handle moderation tasks.

## Responsibilities

- Review and approve/reject pending properties
- User management (view, activate/deactivate, role changes)
- Platform statistics and dashboards
- Content moderation (flagged properties, reported users)
- System configuration (future)
- Audit log (future)

## Future Models

```python
class PropertyReview:
    id: int
    property_id: int        # FK → properties.id
    admin_id: int           # FK → users.id
    action: str             # "approved" | "rejected"
    rejection_reason: str | None
    notes: str | None
    created_at: datetime

class AuditLog:
    id: int
    actor_id: int           # FK → users.id
    action: str             # e.g., "property.approve", "user.deactivate"
    target_type: str        # "property" | "user" | "inquiry"
    target_id: int
    metadata: dict          # JSON
    created_at: datetime

class PlatformStats:
    total_users: int
    total_properties: int
    pending_properties: int
    published_properties: int
    sold_properties: int
    total_inquiries: int
    new_users_this_week: int
    new_properties_this_week: int
```

## Future Schemas

```python
class PropertyApprovalRequest(BaseModel):
    action: Literal["approve", "reject"]
    rejection_reason: str | None = None
    notes: str | None = None

class AdminStatsResponse(BaseModel):
    total_users: int
    total_properties: int
    pending_properties: int
    published_properties: int
    total_inquiries: int
    new_users_this_week: int
    new_properties_this_week: int

class AdminUserListResponse(BaseModel):
    items: list[UserResponse]
    total: int
    page: int
    per_page: int
```

## Future Services

- `AdminPropertyService` — approve/reject properties, review queue
- `AdminUserService` — user management, role changes, deactivation
- `StatsService` — aggregate platform statistics
- `AuditService` — log and retrieve admin actions

## Future Routes / API

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/api/admin/stats` | Platform statistics | Admin |
| GET | `/api/admin/properties/pending` | Pending review queue | Admin |
| POST | `/api/admin/properties/{id}/review` | Approve/reject property | Admin |
| GET | `/api/admin/users` | List all users | Admin |
| PUT | `/api/admin/users/{id}/role` | Change user role | Admin |
| PUT | `/api/admin/users/{id}/status` | Activate/deactivate user | Admin |
| GET | `/api/admin/audit-log` | View audit log | Admin |

## Dependencies

- **users** module — user management
- **properties** module — property review
- **inquiries** module — moderation
- **media** module — media moderation

## Permissions

| Role | Access |
|------|--------|
| Anonymous | No access |
| Buyer | No access |
| Owner | No access |
| Admin | Full access to all admin endpoints |

## Business Rules

- Only users with role `admin` can access admin endpoints
- Admin cannot deactivate their own account (prevent lockout)
- Admin cannot change their own role (prevent self-demotion lockout)
- Property rejection requires a reason (min 10 characters)
- All admin actions are logged in the audit log
- Statistics are computed in real-time (cached for 5 minutes in future)
- Admin can view but not edit inquiry content (moderation only)

## Future Extensions

- Bulk property approval/rejection
- Admin dashboard with charts and trends
- Content moderation queue (reported properties/users)
- System settings management (approval thresholds, rate limits)
- Export reports (CSV, PDF)
- Scheduled maintenance mode
- Admin role hierarchy (super admin vs moderator)
- API key management for integrations
- Feature flags management
