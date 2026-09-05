"""Add_OAuth_and_authentication_columns_to_users_table

Revision ID: 002_add_oauth_columns
Revises: 001_create_users_tables
Create Date: 2026-09-05 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '0003'
down_revision: Union[str, None] = '0002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None




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


def upgrade() -> None:
    """Add OAuth and authentication columns to users table."""
    
    # ============================================================
    # 1. إضافة الأعمدة الجديدة إلى جدول users
    # ============================================================
    
    # عمود is_verified
    if not column_exists('users', 'is_verified'):
        op.add_column('users', sa.Column('is_verified', sa.Boolean(), nullable=False, server_default=sa.text('false')))
        print("✅ Column 'is_verified' added to users")
    
    # عمود password_hash
    if not column_exists('users', 'password_hash'):
        op.add_column('users', sa.Column('password_hash', sa.String(length=255), nullable=True))
        print("✅ Column 'password_hash' added to users")
    
    # عمود oauth_provider
    if not column_exists('users', 'oauth_provider'):
        op.add_column('users', sa.Column('oauth_provider', sa.String(length=50), nullable=True))
        print("✅ Column 'oauth_provider' added to users")
    
    # عمود oauth_id
    if not column_exists('users', 'oauth_id'):
        op.add_column('users', sa.Column('oauth_id', sa.String(length=255), nullable=True))
        print("✅ Column 'oauth_id' added to users")
    
    # ============================================================
    # 2. إنشاء فهرس OAuth
    # ============================================================
    if not index_exists('idx_users_oauth'):
        op.create_index('idx_users_oauth', 'users', ['oauth_provider', 'oauth_id'])
        print("✅ Index 'idx_users_oauth' created")
    
    # ============================================================
    # 3. إنشاء جدول user_sessions
    # ============================================================
    if not table_exists('user_sessions'):
        op.create_table(
            'user_sessions',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('token', sa.String(length=255), nullable=False),
            sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id'),
        )
        print("✅ Table 'user_sessions' created successfully")
        
        # إنشاء الفهارس
        op.create_index('idx_user_sessions_token', 'user_sessions', ['token'], unique=True)
        op.create_index('idx_user_sessions_expires_at', 'user_sessions', ['expires_at'])
        print("✅ Indexes for 'user_sessions' created")
    else:
        print("ℹ️ Table 'user_sessions' already exists")


def downgrade() -> None:
    """Remove OAuth columns and user_sessions table."""
    
    # حذف جدول user_sessions
    if table_exists('user_sessions'):
        op.drop_table('user_sessions')
        print("✅ Table 'user_sessions' dropped")
    
    # حذف الفهارس
    op.drop_index('idx_users_oauth', table_name='users')
    
    # حذف الأعمدة
    op.drop_column('users', 'oauth_id')
    op.drop_column('users', 'oauth_provider')
    op.drop_column('users', 'password_hash')
    op.drop_column('users', 'is_verified')
    
    print("✅ OAuth columns removed from users")
