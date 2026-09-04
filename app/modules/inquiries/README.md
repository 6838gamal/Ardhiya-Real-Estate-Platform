# Inquiries Module — Architecture Contract

> **Status:** Not Implemented. This document defines the future architecture.

## Purpose

Connect buyers with property owners. Buyers can send inquiries or contact requests on properties they're interested in. Owners receive and respond to these inquiries.

## Responsibilities

- Buyer submits inquiry on a property
- Owner views inquiries on their properties
- Owner responds to inquiries (accept/reject/contact)
- Inquiry status tracking
- Notification triggers (future)
- Spam prevention (rate limiting)

## Future Models

```python
class Inquiry:
    id: int
    property_id: int       # FK → properties.id
    buyer_id: int          # FK → users.id
    owner_id: int          # FK → users.id (denormalized for quick lookup)
    message: str
    contact_phone: str | None
    contact_email: str | None
    status: str            # "pending" | "responded" | "accepted" | "rejected" | "closed"
    owner_response: str | None
    created_at: datetime
    responded_at: datetime | None
    closed_at: datetime | None
```

## Future Schemas

```python
class InquiryCreate(BaseModel):
    property_id: int
    message: str            # min 10, max 1000 chars
    contact_phone: str | None = None
    contact_email: EmailStr | None = None

class InquiryResponse(BaseModel):
    id: int
    property_id: int
    buyer: UserResponse
    message: str
    status: str
    owner_response: str | None
    created_at: datetime
    responded_at: datetime | None

class InquiryUpdate(BaseModel):
    status: Literal["responded", "accepted", "rejected", "closed"]
    owner_response: str | None = None
```

## Future Services

- `InquiryService` — create, list, respond, close
- `InquiryNotificationService` — trigger notifications (future)

## Future Routes / API

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| POST | `/api/inquiries` | Submit inquiry | Buyer |
| GET | `/api/inquiries` | List inquiries (role-dependent) | Required |
| GET | `/api/inquiries/{id}` | Inquiry detail | Buyer (own) / Owner (own property) |
| PUT | `/api/inquiries/{id}` | Owner responds | Owner (own property) |
| DELETE | `/api/inquiries/{id}` | Withdraw inquiry | Buyer (own) |

## Dependencies

- **users** module — buyer and owner identity
- **properties** module — property existence, owner relationship
- **auth** module — authorization checks

## Permissions

| Role | Access |
|------|--------|
| Anonymous | No access |
| Buyer | Create inquiries, view own, withdraw own |
| Owner | View inquiries on own properties, respond |
| Admin | View all inquiries, moderate, delete any |

## Business Rules

- Only `published` properties can receive inquiries
- A buyer can submit one inquiry per property (unique constraint)
- Message is required (10–1000 characters)
- Contact phone or email is optional but recommended
- Owner can respond once; status transitions: pending → responded → accepted/rejected → closed
- Buyer can withdraw (close) an inquiry at any time
- Rate limit: max 5 inquiries per buyer per hour (spam prevention)
- Inquiries on sold/rented properties are blocked but existing ones remain visible

## Future Extensions

- In-app messaging between buyer and owner (threaded conversation)
- Email notifications on new inquiry and response
- Inquiry templates (buyer can select from pre-written messages)
- Inquiry analytics for owners (response rate, time-to-respond)
- Spam detection and auto-filtering
- WhatsApp integration for direct contact
- Scheduled property viewing appointments
