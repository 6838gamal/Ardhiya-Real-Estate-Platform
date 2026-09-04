# Media Module — Architecture Contract

> **Status:** Not Implemented. This document defines the future architecture.

## Purpose

Manage property media assets — images now, video and documents in the future. Media is linked to a property and displayed in galleries. Handles upload, storage, ordering, and deletion.

## Responsibilities

- Image upload and storage
- Image ordering (primary image, gallery order)
- Image deletion
- Future: video upload and streaming
- Future: document attachments (title deeds, floor plans)
- Thumbnail generation
- Image optimization (compression, resizing)

## Future Models

```python
class Media:
    id: int
    property_id: int          # FK → properties.id
    media_type: str           # "image" | "video" | "document"
    url: str                  # CDN/storage URL
    thumbnail_url: str | None
    alt_text: str | None
    file_size: int            # bytes
    mime_type: str
    width: int | None
    height: int | None
    sort_order: int           # 0 = primary/cover image
    created_at: datetime

class MediaVariant:
    id: int
    media_id: int             # FK → media.id
    variant: str              # "thumbnail" | "small" | "medium" | "large" | "original"
    url: str
    width: int
    height: int
```

## Future Schemas

```python
class MediaUploadResponse(BaseModel):
    id: int
    url: str
    thumbnail_url: str | None
    sort_order: int

class MediaReorder(BaseModel):
    media_ids: list[int]      # ordered list

class MediaResponse(BaseModel):
    id: int
    media_type: str
    url: str
    thumbnail_url: str | None
    alt_text: str | None
    sort_order: int
    created_at: datetime
```

## Future Services

- `MediaService` — upload, delete, reorder
- `ImageProcessor` — resize, compress, generate thumbnails
- `StorageService` — file storage abstraction (local, S3, CDN)

## Future Routes / API

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/api/properties/{id}/media` | List media for property | Public |
| POST | `/api/properties/{id}/media` | Upload media | Owner (own) |
| PUT | `/api/properties/{id}/media/reorder` | Reorder media | Owner (own) |
| DELETE | `/api/media/{id}` | Delete media | Owner (own) |

## Dependencies

- **properties** module — property ownership check
- Pillow / Pillow-SIMD — image processing
- File storage backend (local filesystem initially, S3-compatible in future)

## Permissions

| Role | Access |
|------|--------|
| Anonymous | View published property media |
| Buyer | Same as anonymous |
| Owner | Upload/delete/reorder own property media |
| Admin | Delete any media (moderation) |

## Business Rules

- Maximum 20 images per property
- Maximum file size: 10MB per image
- Accepted formats: JPEG, PNG, WebP
- First uploaded image is the cover image (sort_order = 0)
- Images are automatically resized to variants: thumbnail (150px), small (400px), medium (800px), large (1200px)
- Deleting a property cascades to delete its media
- Video support is future scope — not in initial implementation

## Future Extensions

- Video upload and HLS streaming
- 360-degree panoramic images
- Floor plan uploads
- Watermarking
- AI-powered image tagging and alt-text generation
- Bulk upload via ZIP
- Drag-and-drop reordering in UI
