# Properties Module — Architecture Contract

> **Status:** Not Implemented. This document defines the future architecture.

## Purpose

Core module for property listings. Handles creation, editing, deletion, publishing, searching, and filtering of real estate properties. Properties go through an approval workflow before going live.

## Responsibilities

- Property CRUD operations
- Property status lifecycle (draft → pending → published → sold/rented)
- Search with filters (type, status, price range, location, area, bedrooms)
- Sorting (price, date, area)
- Pagination of results
- Property approval workflow
- View tracking

## Future Models

```python
class Property:
    id: int
    owner_id: int              # FK → users.id
    title: str
    description: str
    property_type: str         # "apartment" | "villa" | "land" | "office" | "shop"
    listing_type: str          # "sale" | "rent"
    status: str                # "draft" | "pending" | "published" | "sold" | "rented" | "rejected"
    price: Decimal
    currency: str              # "SAR" | "USD" | "AED"
    city: str
    district: str
    latitude: float | None
    longitude: float | None
    bedrooms: int | None
    bathrooms: int | None
    area_sqm: Decimal | None
    year_built: int | None
    furnished: bool
    amenities: list[str]       # JSON array
    view_count: int
    created_at: datetime
    updated_at: datetime
    published_at: datetime | None
    approved_by: int | None    # FK → users.id (admin)
    approved_at: datetime | None
```

## Future Schemas

```python
class PropertyCreate(BaseModel):
    title: str
    description: str
    property_type: Literal["apartment", "villa", "land", "office", "shop"]
    listing_type: Literal["sale", "rent"]
    price: Decimal
    currency: str = "SAR"
    city: str
    district: str
    bedrooms: int | None = None
    bathrooms: int | None = None
    area_sqm: Decimal | None = None
    year_built: int | None = None
    furnished: bool = False
    amenities: list[str] = []

class PropertyUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    price: Decimal | None = None

class PropertyFilter(BaseModel):
    property_type: str | None = None
    listing_type: str | None = None
    min_price: Decimal | None = None
    max_price: Decimal | None = None
    city: str | None = None
    district: str | None = None
    min_bedrooms: int | None = None
    min_area: Decimal | None = None
    sort_by: Literal["price_asc", "price_desc", "date_desc", "area_desc"] = "date_desc"
    page: int = 1
    per_page: int = 12

class PropertyResponse(BaseModel):
    id: int
    title: str
    description: str
    property_type: str
    listing_type: str
    status: str
    price: Decimal
    currency: str
    city: str
    district: str
    bedrooms: int | None
    bathrooms: int | None
    area_sqm: Decimal | None
    owner: UserResponse
    created_at: datetime
```

## Future Services

- `PropertyService` — CRUD, status transitions, validation
- `PropertySearchService` — filter, sort, paginate
- `PropertyApprovalService` — admin review workflow

## Future Routes / API

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/api/properties` | Search/list properties | Public |
| GET | `/api/properties/{id}` | Property detail | Public |
| POST | `/api/properties` | Create property | Owner |
| PUT | `/api/properties/{id}` | Update property | Owner (own) |
| DELETE | `/api/properties/{id}` | Delete property | Owner (own) |
| POST | `/api/properties/{id}/submit` | Submit for review | Owner (own) |
| POST | `/api/properties/{id}/approve` | Approve property | Admin |
| POST | `/api/properties/{id}/reject` | Reject property | Admin |
| POST | `/api/properties/{id}/mark-sold` | Mark as sold/rented | Owner (own) |

## Dependencies

- **users** module — owner relationship
- **media** module — property images
- **favorites** module — favoriting
- **inquiries** module — buyer inquiries
- **admin** module — approval workflow

## Permissions

| Role | Access |
|------|--------|
| Anonymous | View published properties, search |
| Buyer | All above + favorite, inquire |
| Owner | All above + create/edit/delete own, submit for review |
| Admin | All above + approve/reject any property |

## Business Rules

- Properties start as `draft`, owner submits → `pending`, admin approves → `published`
- Only `published` properties appear in public search
- Owner can edit draft/pending properties, not published/sold ones
- Price must be positive; area must be positive if provided
- Land properties have no bedrooms/bathrooms
- Rejected properties return to `draft` with optional rejection reason
- View count increments on each detail page view (deduplicated by IP+session)

## Future Extensions

- Full-text search on title and description
- Geo-search with map integration
- Saved searches with email alerts
- Property comparison tool
- Price history tracking
- Virtual tours / 3D views
- Automated valuation estimates
