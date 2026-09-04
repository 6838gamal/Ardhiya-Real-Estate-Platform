"""User models for database."""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Integer,
    String,
    Text,
    ForeignKey,
    Index,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class User(Base):
    """User model - core user account."""
    
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    avatar_url = Column(String(500), nullable=True)
    phone = Column(String(20), nullable=True)
    bio = Column(Text, nullable=True)
    role = Column(String(20), nullable=False, default="buyer")  # "owner" | "buyer" | "admin"
    is_active = Column(Boolean, nullable=False, default=True)
    last_login = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
    
    # Relationships
    profile = relationship("UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    # Future relationships (will be added when modules are implemented)
    # properties = relationship("Property", back_populates="owner")
    # favorites = relationship("Favorite", back_populates="user")
    # inquiries = relationship("Inquiry", back_populates="user")
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, role={self.role})>"


class UserProfile(Base):
    """User profile - extended user settings and preferences."""
    
    __tablename__ = "user_profiles"
    
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True, index=True)
    preferred_language = Column(String(10), nullable=False, default="en")  # "ar" | "en"
    preferred_currency = Column(String(10), nullable=False, default="SAR")  # "SAR" | "USD" | "AED"
    notifications_enabled = Column(Boolean, nullable=False, default=True)
    marketing_emails = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="profile")
    
    def __repr__(self) -> str:
        return f"<UserProfile(user_id={self.user_id}, language={self.preferred_language})>"

# Indexes for performance
Index("idx_users_email_active", User.email, User.is_active)
Index("idx_users_role_active", User.role, User.is_active)
Index("idx_users_created_at", User.created_at)
