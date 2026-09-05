import os
import sys
from logging.config import fileConfig

from sqlalchemy import create_engine, pool
from alembic import context

# إضافة مسار المشروع
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

# استيراد Base والإعدادات
from app.config.database import Base
from app.config.settings import settings
from app.modules.users.models import User, UserProfile

# استيراد جميع النماذج للتأكد من تسجيلها في Base.metadata

# إعداد التكوين
config = context.config

# إعداد التسجيل
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# هدف Alembic - جميع النماذج مسجلة هنا
target_metadata = Base.metadata

def get_sync_url():
    """
    الحصول على URL متزامن للاتصال بقاعدة البيانات
    """
    # الحصول على URL من متغيرات البيئة أو الإعدادات
    url = os.environ.get("DATABASE_URL")
    if not url:
        url = settings.DATABASE_URL
    
    # تحويل من asyncpg إلى psycopg2 إذا لزم الأمر
    if "asyncpg" in url:
        url = url.replace("postgresql+asyncpg://", "postgresql://")
    
    return url

def run_migrations_offline() -> None:
    """تشغيل الترحيلات في وضع غير متصل."""
    url = get_sync_url()
    
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    """تشغيل الترحيلات في وضع متصل (باستخدام اتصال متزامن)."""
    sync_url = get_sync_url()
    
    # إنشاء engine متزامن
    connectable = create_engine(
        sync_url,
        poolclass=pool.NullPool,
        pool_pre_ping=True,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
