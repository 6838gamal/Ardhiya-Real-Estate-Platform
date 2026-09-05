"""Create_users_and_user_profiles_tables_with_full_existence_checks

Revision ID: 001_create_users_tables
Revises: 
Create Date: 2026-09-05 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identi.
revision: str = '0002'
down_revision: Union[str, None] = '0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def table_exists(table_name: str) -> bool:
    """Check if a table exists in the database."""
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            "SELECT EXISTS ("
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_name = :table_name"
            ")"
        ),
        {"table_name": table_name}
    ).scalar()
    return result


def column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table."""
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            "SELECT EXISTS ("
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name = :table_name AND column_name = :column_name"
            ")"
        ),
        {"table_name": table_name, "column_name": column_name}
    ).scalar()
    return result


def index_exists(index_name: str) -> bool:
    """Check if an index exists in the database."""
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            "SELECT EXISTS ("
            "SELECT 1 FROM pg_indexes "
            "WHERE indexname = :index_name"
            ")"
        ),
        {"index_name": index_name}
    ).scalar()
    return result


def constraint_exists(constraint_name: str, table_name: str) -> bool:
    """Check if a constraint exists in the database."""
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            "SELECT EXISTS ("
            "SELECT 1 FROM information_schema.table_constraints "
            "WHERE constraint_name = :constraint_name "
            "AND table_name = :table_name"
            ")"
        ),
        {"constraint_name": constraint_name, "table_name": table_name}
    ).scalar()
    return result


def upgrade() -> None:
    """
    Create users and user_profiles tables with full existence checks.
    This migration safely handles existing tables and columns.
    """
    
    # ============================================================
    # 1. إنشاء جدول users مع التحقق من وجوده
    # ============================================================
    if not table_exists('users'):
        # إنشاء الجدول كاملاً
        op.create_table(
            'users',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('email', sa.String(length=255), nullable=False),
            sa.Column('name', sa.String(length=255), nullable=False),
            sa.Column('avatar_url', sa.String(length=500), nullable=True),
            sa.Column('phone', sa.String(length=20), nullable=True),
            sa.Column('bio', sa.Text(), nullable=True),
            sa.Column('role', sa.String(length=20), nullable=False, server_default='buyer'),
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
            sa.Column('last_login', sa.DateTime(timezone=True), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint('id'),
        )
        print("✅ Table 'users' created successfully")
    else:
        print("ℹ️ Table 'users' already exists, checking missing columns...")
    
    # ============================================================
    # 2. التحقق من الأعمدة المفقودة في جدول users وإضافتها
    # ============================================================
    # عمود avatar_url
    if not column_exists('users', 'avatar_url'):
        op.add_column('users', sa.Column('avatar_url', sa.String(length=500), nullable=True))
        print("✅ Column 'avatar_url' added to users")
    
    # عمود phone
    if not column_exists('users', 'phone'):
        op.add_column('users', sa.Column('phone', sa.String(length=20), nullable=True))
        print("✅ Column 'phone' added to users")
    
    # عمود bio
    if not column_exists('users', 'bio'):
        op.add_column('users', sa.Column('bio', sa.Text(), nullable=True))
        print("✅ Column 'bio' added to users")
    
    # عمود last_login
    if not column_exists('users', 'last_login'):
        op.add_column('users', sa.Column('last_login', sa.DateTime(timezone=True), nullable=True))
        print("✅ Column 'last_login' added to users")
    
    # عمود updated_at
    if not column_exists('users', 'updated_at'):
        op.add_column('users', sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True))
        print("✅ Column 'updated_at' added to users")
    
    # ============================================================
    # 3. إنشاء الفهارس لجدول users مع التحقق من وجودها
    # ============================================================
    # فهرس idx_users_email_active
    if not index_exists('idx_users_email_active'):
        op.create_index('idx_users_email_active', 'users', ['email', 'is_active'])
        print("✅ Index 'idx_users_email_active' created")
    
    # فهرس idx_users_role_active
    if not index_exists('idx_users_role_active'):
        op.create_index('idx_users_role_active', 'users', ['role', 'is_active'])
        print("✅ Index 'idx_users_role_active' created")
    
    # فهرس idx_users_created_at
    if not index_exists('idx_users_created_at'):
        op.create_index('idx_users_created_at', 'users', ['created_at'])
        print("✅ Index 'idx_users_created_at' created")
    
    # فهرس ix_users_email (فريد)
    if not index_exists('ix_users_email'):
        op.create_index('ix_users_email', 'users', ['email'], unique=True)
        print("✅ Unique index 'ix_users_email' created")
    
    # فهرس ix_users_id
    if not index_exists('ix_users_id'):
        op.create_index('ix_users_id', 'users', ['id'], unique=False)
        print("✅ Index 'ix_users_id' created")
    
    # ============================================================
    # 4. إنشاء جدول user_profiles مع التحقق من وجوده
    # ============================================================
    if not table_exists('user_profiles'):
        op.create_table(
            'user_profiles',
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('preferred_language', sa.String(length=10), nullable=False, server_default='en'),
            sa.Column('preferred_currency', sa.String(length=10), nullable=False, server_default='SAR'),
            sa.Column('notifications_enabled', sa.Boolean(), nullable=False, server_default=sa.text('true')),
            sa.Column('marketing_emails', sa.Boolean(), nullable=False, server_default=sa.text('true')),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('user_id'),
        )
        print("✅ Table 'user_profiles' created successfully")
    else:
        print("ℹ️ Table 'user_profiles' already exists, checking missing columns...")
    
    # ============================================================
    # 5. التحقق من الأعمدة المفقودة في جدول user_profiles وإضافتها
    # ============================================================
    # عمود preferred_language
    if not column_exists('user_profiles', 'preferred_language'):
        op.add_column('user_profiles', sa.Column('preferred_language', sa.String(length=10), nullable=False, server_default='en'))
        print("✅ Column 'preferred_language' added to user_profiles")
    
    # عمود preferred_currency
    if not column_exists('user_profiles', 'preferred_currency'):
        op.add_column('user_profiles', sa.Column('preferred_currency', sa.String(length=10), nullable=False, server_default='SAR'))
        print("✅ Column 'preferred_currency' added to user_profiles")
    
    # عمود notifications_enabled
    if not column_exists('user_profiles', 'notifications_enabled'):
        op.add_column('user_profiles', sa.Column('notifications_enabled', sa.Boolean(), nullable=False, server_default=sa.text('true')))
        print("✅ Column 'notifications_enabled' added to user_profiles")
    
    # عمود marketing_emails
    if not column_exists('user_profiles', 'marketing_emails'):
        op.add_column('user_profiles', sa.Column('marketing_emails', sa.Boolean(), nullable=False, server_default=sa.text('true')))
        print("✅ Column 'marketing_emails' added to user_profiles")
    
    # عمود updated_at
    if not column_exists('user_profiles', 'updated_at'):
        op.add_column('user_profiles', sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True))
        print("✅ Column 'updated_at' added to user_profiles")
    
    # ============================================================
    # 6. إنشاء الفهارس لجدول user_profiles مع التحقق من وجودها
    # ============================================================
    # فهرس ix_user_profiles_user_id
    if not index_exists('ix_user_profiles_user_id'):
        op.create_index('ix_user_profiles_user_id', 'user_profiles', ['user_id'], unique=False)
        print("✅ Index 'ix_user_profiles_user_id' created")
    
    # ============================================================
    # 7. التحقق من وجود المفتاح الخارجي وإضافته إذا لم يكن موجوداً
    # ============================================================
    if not constraint_exists('fk_user_profiles_user_id', 'user_profiles'):
        op.create_foreign_key(
            'fk_user_profiles_user_id',
            'user_profiles',
            'users',
            ['user_id'],
            ['id'],
            ondelete='CASCADE'
        )
        print("✅ Foreign key 'fk_user_profiles_user_id' created")


def downgrade() -> None:
    """
    Drop users and user_profiles tables safely.
    Only drops tables if they exist.
    """
    
    # ============================================================
    # 1. حذف جدول user_profiles إذا كان موجوداً
    # ============================================================
    if table_exists('user_profiles'):
        op.drop_table('user_profiles')
        print("✅ Table 'user_profiles' dropped")
    else:
        print("ℹ️ Table 'user_profiles' does not exist, skipping drop")
    
    # ============================================================
    # 2. حذف جدول users إذا كان موجوداً
    # ============================================================
    if table_exists('users'):
        op.drop_table('users')
        print("✅ Table 'users' dropped")
    else:
        print("ℹ️ Table 'users' does not exist, skipping drop")
