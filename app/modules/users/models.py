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

from app.config.database import Base


class User(Base):
    """User model - core user account."""
    
    __tablename__ = "users"
    __table_args__ = {"extend_existing": True}
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    avatar_url = Column(String(500), nullable=True)
    phone = Column(String(20), nullable=True)
    bio = Column(Text, nullable=True)
    role = Column(String(20), nullable=False, default="buyer")
    is_active = Column(Boolean, nullable=False, default=True)
    is_verified = Column(Boolean, nullable=False, default=False)
    last_login = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
    
    # حقول OAuth والمصادقة
    password_hash = Column(String(255), nullable=True)
    oauth_provider = Column(String(50), nullable=True)
    oauth_id = Column(String(255), nullable=True)
    
    # Relationships
    profile = relationship("UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    sessions = relationship("UserSession", back_populates="user", lazy="select")
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, role={self.role})>"
    
    @property
    def is_oauth_user(self) -> bool:
        return self.oauth_provider is not None and self.oauth_id is not None
    
    @property
    def has_password(self) -> bool:
        return self.password_hash is not None


class UserProfile(Base):
    """User profile - extended user settings and preferences."""
    
    __tablename__ = "user_profiles"
    __table_args__ = {"extend_existing": True}
    
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True, index=True)
    preferred_language = Column(String(10), nullable=False, default="en")
    preferred_currency = Column(String(10), nullable=False, default="SAR")
    notifications_enabled = Column(Boolean, nullable=False, default=True)
    marketing_emails = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="profile")
    
    def __repr__(self) -> str:
        return f"<UserProfile(user_id={self.user_id}, language={self.preferred_language})>"


class UserSession(Base):
    """User session model for storing active sessions."""
    
    __tablename__ = "user_sessions"
    __table_args__ = {"extend_existing": True}
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token = Column(String(255), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationship
    user = relationship("User", back_populates="sessions")
    
    def __repr__(self) -> str:
        return f"<UserSession(id={self.id}, user_id={self.user_id}, expires_at={self.expires_at})>"


# Indexes for performance
Index("idx_users_email_active", User.email, User.is_active)
Index("idx_users_role_active", User.role, User.is_active)
Index("idx_users_created_at", User.created_at)
Index("idx_users_oauth", User.oauth_provider, User.oauth_id)
Index("idx_user_sessions_token", UserSession.token)
Index("idx_user_sessions_expires_at", UserSession.expires_at)
