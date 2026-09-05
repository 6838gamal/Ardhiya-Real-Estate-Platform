"""Auth module models."""
from datetime import datetime
from typing import Optional
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.config.database import Base


class UserSession(Base):
    """User session model for OAuth authentication."""
    __tablename__ = "user_sessions"
    __table_args__ = {"extend_existing": True}  # ✅ لتجنب خطأ التعريف المتكرر

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token = Column(String(255), unique=True, nullable=False, index=True)  # ✅ غيرت من session_token إلى token
   # provider = Column(String(50), nullable=False, default="google")
   # provider_user_id = Column(String(255), nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)  # ✅ أضفت timezone=True
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)  # ✅ أضفت timezone=True
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    is_revoked = Column(Boolean, default=False, nullable=False)  # ✅ غيرت من Integer إلى Boolean

    # Relationships
    user = relationship("User", back_populates="sessions")

    def __repr__(self) -> str:
        return f"<UserSession id={self.id} user_id={self.user_id} provider={self.provider}>"

    def is_expired(self) -> bool:
        """Check if session is expired."""
        return datetime.utcnow() > self.expires_at.replace(tzinfo=None)

    def is_active(self) -> bool:
        """Check if session is active (not expired and not revoked)."""
        return not self.is_expired() and not self.is_revoked


# Indexes for performance
Index("idx_sessions_user_id", UserSession.user_id)
Index("idx_sessions_token_revoked", UserSession.token, UserSession.is_revoked)  # ✅ غيرت من session_token إلى token
Index("idx_sessions_expires_at", UserSession.expires_at)
Index("idx_sessions_provider_user_id", UserSession.provider_user_id)
