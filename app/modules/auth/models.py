"""Auth module models."""
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import (
    Column, Integer, String, DateTime, ForeignKey, Text,
    Boolean, Index
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.config.database import Base


class UserSession(Base):
    """User session model for OAuth authentication."""
    __tablename__ = "user_sessions"

    # ============ الأعمدة الأساسية ============
    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    token = Column(
        String(255),
        unique=True,
        nullable=False,
        index=True
    )

    expires_at = Column(
        DateTime(timezone=True),
        nullable=False,
        index=True
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    is_revoked = Column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False
    )

    # ============ أعمدة اختيارية (مُعطَّلة) ============
    # ⚠️ فعِّلها فقط إذا كنت تحتاج تتبع الأجهزة/العناوين
    # وتأكد من تمريرها في SessionService.create_session
    #
    # ip_address = Column(String(45), nullable=True)
    # user_agent = Column(Text, nullable=True)
    # provider = Column(String(50), nullable=False, default="google")
    # provider_user_id = Column(String(255), nullable=False, index=True)

    # ============ العلاقات ============
    user = relationship("User", back_populates="sessions")

    # ============ الدوال المساعدة ============
    def __repr__(self) -> str:
        """تمثيل نصي للجلسة (للتسجيل والتصحيح)."""
        return (
            f"<UserSession id={self.id} "
            f"user_id={self.user_id} "
            f"expires_at={self.expires_at} "
            f"is_revoked={self.is_revoked}>"
        )

    def is_expired(self) -> bool:
        """
        التحقق من انتهاء صلاحية الجلسة.

        يستخدم timezone-aware comparison لتجنب أخطاء التوقيت.
        """
        now = datetime.now(timezone.utc)
        expires = self.expires_at

        # ضمان أن expires timezone-aware (احتياط)
        if expires is None:
            return True
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)

        return now > expires

    def is_active(self) -> bool:
        """التحقق من أن الجلسة نشطة (غير منتهية وغير ملغاة)."""
        return not self.is_expired() and not self.is_revoked

    def revoke(self) -> None:
        """إلغاء الجلسة (دالة مساعدة)."""
        self.is_revoked = True

    def to_dict(self) -> dict:
        """تحويل الجلسة إلى قاموس (للاستخدام في API)."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "is_revoked": self.is_revoked,
            "is_expired": self.is_expired(),
            "is_active": self.is_active(),
        }


# ============ الفهارس (Indexes) ============
# ⚠️ ملاحظة: index=True على العمود ينشئ فهرساً تلقائياً
# لذلك لا نكرر الفهارس هنا إلا للفهارس المركبة

# فهرس مركب للبحث السريع عن التوكنات النشطة
Index(
    "idx_sessions_token_active",
    UserSession.token,
    UserSession.is_revoked,
    UserSession.expires_at
)

# فهرس مركب لجلب جلسات المستخدم النشطة
Index(
    "idx_sessions_user_active",
    UserSession.user_id,
    UserSession.is_revoked,
    UserSession.expires_at
)
