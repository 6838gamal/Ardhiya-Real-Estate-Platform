# app/config/database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config.settings import settings

# ✅ استبدل asyncpg بـ psycopg2
db_url = settings.database_url.replace("+asyncpg", "+psycopg2")

engine = create_engine(
    db_url,
    pool_pre_ping=True,
    echo=settings.is_dev,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
