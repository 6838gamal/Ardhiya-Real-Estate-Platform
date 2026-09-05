"""Add_missing_columns_to_user_sessions

Revision ID: 20260905_073830
Revises: 
Create Date: 2026-09-05 07:38:30.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect, text

# revision identifiers, used by Alembic.
revision = '0004'
down_revision = '0003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    ✅ الترقية: إضافة جميع الأعمدة المفقودة إلى جدول user_sessions
    """
    conn = op.get_bind()
    inspector = inspect(conn)
    
    # ============================================================
    # 1. التحقق من وجود الجدول
    # ============================================================
    if 'user_sessions' not in inspector.get_table_names():
        print("❌ جدول user_sessions غير موجود")
        return
    
    print("✅ جدول user_sessions موجود")
    
    # ============================================================
    # 2. الحصول على الأعمدة الموجودة
    # ============================================================
    existing_columns = [col['name'] for col in inspector.get_columns('user_sessions')]
    print(f"📋 الأعمدة الموجودة: {existing_columns}")
    
    added = []
    
    # ============================================================
    # 3. إضافة الأعمدة المفقودة
    # ============================================================
    
    # ✅ عمود provider
    if 'provider' not in existing_columns:
        op.add_column('user_sessions', sa.Column('provider', sa.String(50), nullable=True))
        op.execute("UPDATE user_sessions SET provider = 'google' WHERE provider IS NULL")
        op.alter_column('user_sessions', 'provider', nullable=False)
        added.append('provider')
        print("✅ تم إضافة عمود provider")
    else:
        print("✅ عمود provider موجود مسبقاً")
    
    # ✅ عمود provider_user_id
    if 'provider_user_id' not in existing_columns:
        op.add_column('user_sessions', sa.Column('provider_user_id', sa.String(255), nullable=True))
        added.append('provider_user_id')
        print("✅ تم إضافة عمود provider_user_id")
    else:
        print("✅ عمود provider_user_id موجود مسبقاً")
    
    # ✅ عمود ip_address
    if 'ip_address' not in existing_columns:
        op.add_column('user_sessions', sa.Column('ip_address', sa.String(45), nullable=True))
        added.append('ip_address')
        print("✅ تم إضافة عمود ip_address")
    else:
        print("✅ عمود ip_address موجود مسبقاً")
    
    # ✅ عمود user_agent
    if 'user_agent' not in existing_columns:
        op.add_column('user_sessions', sa.Column('user_agent', sa.Text(), nullable=True))
        added.append('user_agent')
        print("✅ تم إضافة عمود user_agent")
    else:
        print("✅ عمود user_agent موجود مسبقاً")
    
    # ✅ عمود is_revoked (المفقود حالياً)
    if 'is_revoked' not in existing_columns:
        op.add_column('user_sessions', sa.Column('is_revoked', sa.Boolean(), nullable=False, server_default='false'))
        added.append('is_revoked')
        print("✅ تم إضافة عمود is_revoked")
    else:
        print("✅ عمود is_revoked موجود مسبقاً")
    
    # ============================================================
    # 4. إضافة المؤشرات (Indexes)
    # ============================================================
    
    indexes = [idx['name'] for idx in inspector.get_indexes('user_sessions')]
    
    # مؤشر provider_user_id
    if 'idx_sessions_provider_user_id' not in indexes:
        op.create_index('idx_sessions_provider_user_id', 'user_sessions', ['provider_user_id'])
        print("✅ تم إضافة مؤشر idx_sessions_provider_user_id")
    else:
        print("✅ مؤشر idx_sessions_provider_user_id موجود مسبقاً")
    
    # مؤشر ip_address
    if 'idx_sessions_ip_address' not in indexes:
        op.create_index('idx_sessions_ip_address', 'user_sessions', ['ip_address'])
        print("✅ تم إضافة مؤشر idx_sessions_ip_address")
    else:
        print("✅ مؤشر idx_sessions_ip_address موجود مسبقاً")
    
    # مؤشر is_revoked (لتحسين الأداء)
    if 'idx_sessions_is_revoked' not in indexes:
        op.create_index('idx_sessions_is_revoked', 'user_sessions', ['is_revoked'])
        print("✅ تم إضافة مؤشر idx_sessions_is_revoked")
    else:
        print("✅ مؤشر idx_sessions_is_revoked موجود مسبقاً")
    
    # ============================================================
    # 5. ملخص
    # ============================================================
    if added:
        print(f"✅ تم إضافة الأعمدة: {added}")
    else:
        print("✅ جميع الأعمدة موجودة مسبقاً")
    
    print("✅ اكتمل ترحيل جدول user_sessions بنجاح")


def downgrade() -> None:
    """
    ❌ الرجوع: حذف الأعمدة المضافة
    """
    conn = op.get_bind()
    inspector = inspect(conn)
    
    if 'user_sessions' not in inspector.get_table_names():
        return
    
    existing_columns = [col['name'] for col in inspector.get_columns('user_sessions')]
    
    # حذف المؤشرات
    op.drop_index('idx_sessions_is_revoked', table_name='user_sessions')
    op.drop_index('idx_sessions_ip_address', table_name='user_sessions')
    op.drop_index('idx_sessions_provider_user_id', table_name='user_sessions')
    
    # حذف الأعمدة (إذا كانت موجودة)
    columns_to_drop = ['provider', 'provider_user_id', 'ip_address', 'user_agent', 'is_revoked']
    for col in columns_to_drop:
        if col in existing_columns:
            op.drop_column('user_sessions', col)
            print(f"❌ تم حذف عمود {col}")
