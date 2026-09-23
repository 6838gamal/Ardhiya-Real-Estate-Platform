"""استعلامات الأراضي/العقارات."""
from __future__ import annotations

from typing import Sequence

from sqlalchemy import select, func, distinct
from sqlalchemy.orm import Session

# ✅ المسار الصحيح حسب هيكل مشروعك
from app.database.lands_base import Land


class LandsRepository:
    """كل استعلامات جدول lands هنا."""

    def __init__(self, db: Session) -> None:
        self.db = db

    # ============ القوائم ============
    def list_published(
        self,
        *,
        land_type: str | None = None,
        purpose: str | None = None,
        city: str | None = None,
        limit: int = 60,
        offset: int = 0,
    ) -> Sequence[Land]:
        stmt = select(Land).where(Land.is_published.is_(True))
        if land_type:
            stmt = stmt.where(Land.land_type == land_type)
        if purpose:
            stmt = stmt.where(Land.purpose == purpose)
        if city:
            stmt = stmt.where(Land.city == city)
        stmt = (
            stmt.order_by(Land.featured.desc(), Land.created_at.desc())
                .limit(limit)
                .offset(offset)
        )
        return self.db.execute(stmt).scalars().all()

    def count_published(
        self,
        *,
        land_type: str | None = None,
        purpose: str | None = None,
        city: str | None = None,
    ) -> int:
        stmt = select(func.count(Land.id)).where(Land.is_published.is_(True))
        if land_type:
            stmt = stmt.where(Land.land_type == land_type)
        if purpose:
            stmt = stmt.where(Land.purpose == purpose)
        if city:
            stmt = stmt.where(Land.city == city)
        return self.db.execute(stmt).scalar_one()

    # ============ التفاصيل ============
    def get_by_slug(self, slug: str, *, published_only: bool = True) -> Land | None:
        stmt = select(Land).where(Land.slug == slug)
        if published_only:
            stmt = stmt.where(Land.is_published.is_(True))
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_id(self, land_id: int) -> Land | None:
        return self.db.get(Land, land_id)

    # ============ مساعدات ============
    def list_cities(self) -> list[str]:
        stmt = (
            select(distinct(Land.city))
            .where(Land.is_published.is_(True), Land.city.is_not(None))
            .order_by(Land.city)
        )
        return [row[0] for row in self.db.execute(stmt).all() if row[0]]

    def list_featured(self, limit: int = 6) -> Sequence[Land]:
        stmt = (
            select(Land)
            .where(Land.is_published.is_(True), Land.featured.is_(True))
            .order_by(Land.created_at.desc())
            .limit(limit)
        )
        return self.db.execute(stmt).scalars().all()

    def list_similar(self, land: Land, limit: int = 3) -> Sequence[Land]:
        conds = [Land.id != land.id, Land.is_published.is_(True)]
        if land.land_type:
            conds.append(Land.land_type == land.land_type)
        elif land.city:
            conds.append(Land.city == land.city)
        stmt = (
            select(Land).where(*conds)
            .order_by(Land.featured.desc(), Land.created_at.desc())
            .limit(limit)
        )
        return self.db.execute(stmt).scalars().all()
