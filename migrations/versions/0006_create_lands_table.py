"""create lands table

Revision ID: 0001_create_lands
Revises:
Create Date: 2026-09-22
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """إنشاء جدول lands إن لم يكن موجوداً."""
    op.create_table(
        "lands",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(255), nullable=False),
        sa.Column("short_description", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),

        # بيانات عقارية
        sa.Column("land_type", sa.String(50), nullable=True),
        sa.Column("purpose", sa.String(20), nullable=True),
        sa.Column("price", sa.Float(), server_default="0"),
        sa.Column("currency", sa.String(10), server_default="SAR"),
        sa.Column("area", sa.Float(), nullable=True),
        sa.Column("rooms", sa.Integer(), nullable=True),
        sa.Column("bathrooms", sa.Integer(), nullable=True),
        sa.Column("address", sa.String(500), nullable=True),
        sa.Column("city", sa.String(100), nullable=True),
        sa.Column("district", sa.String(100), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("features", postgresql.JSONB(), server_default="[]"),
        sa.Column("images", postgresql.JSONB(), server_default="[]"),

        # الحالة
        sa.Column("featured", sa.Boolean(), server_default=sa.false()),
        sa.Column("is_published", sa.Boolean(), server_default=sa.false()),
        sa.Column("cover_image", sa.String(500), nullable=True),

        # طوابع زمنية
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
    )

    # فهارس
    op.create_index("ix_lands_slug", "lands", ["slug"], unique=True)
    op.create_index("ix_lands_is_published", "lands", ["is_published"])
    op.create_index("ix_lands_featured", "lands", ["featured"])
    op.create_index("ix_lands_city", "lands", ["city"])
    op.create_index("ix_lands_purpose", "lands", ["purpose"])
    op.create_index("ix_lands_created_at", "lands", ["created_at"])


def downgrade() -> None:
    """حذف الجدول عند التراجع."""
    op.drop_index("ix_lands_created_at", table_name="lands")
    op.drop_index("ix_lands_purpose", table_name="lands")
    op.drop_index("ix_lands_city", table_name="lands")
    op.drop_index("ix_lands_featured", table_name="lands")
    op.drop_index("ix_lands_is_published", table_name="lands")
    op.drop_index("ix_lands_slug", table_name="lands")
    op.drop_table("lands")
