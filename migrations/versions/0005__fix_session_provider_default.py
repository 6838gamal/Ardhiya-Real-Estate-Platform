"""fix_session_provider_default

Revision ID: xxxxx
Revises: 
Create Date: 2026-09-05 10:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '0005'
down_revision: Union[str, None] = '0004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # تعيين قيمة افتراضية لعمود provider
    op.execute("ALTER TABLE user_sessions ALTER COLUMN provider SET DEFAULT 'google'")
    # تحديث السجلات الموجودة
    op.execute("UPDATE user_sessions SET provider = 'google' WHERE provider IS NULL")
    # التأكد من بقاء شرط NOT NULL مع وجود قيمة افتراضية
    op.execute("ALTER TABLE user_sessions ALTER COLUMN provider SET NOT NULL")

def downgrade() -> None:
    op.execute("ALTER TABLE user_sessions ALTER COLUMN provider DROP DEFAULT")
