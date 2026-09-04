# أرضية — Real Estate Platform

A modular monolith real estate platform built with **FastAPI**, **PostgreSQL**, **Jinja2**, and **Docker**.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.12, FastAPI |
| Database | PostgreSQL 16, SQLAlchemy, Alembic |
| Templating | Jinja2 |
| Frontend | HTML, CSS, JavaScript (no SPA framework) |
| Containerization | Docker, Docker Compose |
| Architecture | Modular Monolith |

## Quick Start

```bash
# 1. Copy environment file
cp .env.example .env

# 2. Build and run
docker compose up --build

# 3. Open in browser
# http://localhost:8000
```

## Project Structure

```
app/
├── config/           # Settings & database connection
│   ├── settings.py
│   └── database.py
├── localization/     # ar.json, en.json + loader
├── modules/          # Feature modules (README contracts)
│   ├── auth/
│   ├── users/
│   ├── properties/
│   ├── media/
│   ├── favorites/
│   ├── inquiries/
│   └── admin/
├── templates/        # Jinja2 templates
├── static/           # CSS, JS, images
└── main.py           # FastAPI application entry point
```

## Features

- **Bilingual**: Arabic (RTL) & English (LTR) with JSON-based localization
- **Theming**: Light & Dark mode with `localStorage` persistence
- **Responsive**: Mobile-first design (320px → 1024px+)
- **Modular**: Each module is self-contained with documented architecture contracts
- **Dockerized**: One command to run the app + database

## Modules (Architecture Contracts)

| Module | Purpose |
|--------|---------|
| `auth` | Google OAuth, sessions, JWT, authorization |
| `users` | User profiles, roles (Owner, Buyer, Admin) |
| `properties` | Property CRUD, search, filtering, status |
| `media` | Property images, files, future video |
| `favorites` | Save/remove favorite properties |
| `inquiries` | Buyer inquiries, contact requests |
| `admin` | Property review, approvals, user management |

Each module contains a `README.md` documenting its future architecture. No business logic is implemented yet — this is the foundation only.

## Localization

Translation files live in `app/localization/`. Use translation keys in templates:

```jinja2
{{ _("home.title") }}
```

Default language is **Arabic**. Language switching is designed for easy future implementation.
# Ardhiya-Real-Estate-Platform
