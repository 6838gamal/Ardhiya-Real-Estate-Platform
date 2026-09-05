"""
Security utilities for authentication.
Supports both local (password) and OAuth authentication.
"""
import hashlib
import secrets
import string
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict, Any

from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import timezone

from app.config.settings import settings

# ============================================================
# إعدادات التشفير
# ============================================================

# سياق تشفير كلمات المرور باستخدام bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ============================================================
# دوال تشفير كلمات المرور
# ============================================================

def get_password_hash(password: str) -> str:
    """
    تشفير كلمة المرور باستخدام bcrypt.
    
    Args:
        password: كلمة المرور النصية
        
    Returns:
        النص المشفر
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: Optional[str]) -> bool:
    """
    التحقق من كلمة المرور مع النص المشفر.
    
    Args:
        plain_password: كلمة المرور النصية
        hashed_password: النص المشفر المخزن (قد يكون None لمستخدمي OAuth)
        
    Returns:
        True إذا كانت متطابقة، False إذا لم تكن
        
    ملاحظة:
        إذا كان hashed_password هو None، فهذا يعني أن المستخدم مسجل عبر OAuth
        ولا يمكنه استخدام كلمة المرور للمصادقة.
    """
    # إذا لم يكن هناك كلمة مرور مشفرة (مستخدم OAuth)
    if hashed_password is None:
        return False
    
    return pwd_context.verify(plain_password, hashed_password)


# ============================================================
# دوال إنشاء الرموز (Tokens)
# ============================================================

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    إنشاء رمز JWT للوصول.
    
    Args:
        data: البيانات المراد تضمينها في الرمز
        expires_delta: مدة صلاحية الرمز (اختياري)
        
    Returns:
        رمز JWT
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    
    return encoded_jwt


def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    إنشاء رمز JWT للتحديث.
    
    Args:
        data: البيانات المراد تضمينها في الرمز
        expires_delta: مدة صلاحية الرمز (اختياري)
        
    Returns:
        رمز JWT للتحديث
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    
    return encoded_jwt


def decode_token(token: str) -> dict:
    """
    فك تشفير رمز JWT.
    
    Args:
        token: رمز JWT
        
    Returns:
        البيانات المستخرجة من الرمز
        
    Raises:
        JWTError: إذا كان الرمز غير صالح
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError as e:
        raise JWTError(f"Invalid token: {str(e)}")


# ============================================================
# دوال إنشاء رموز عشوائية
# ============================================================

def generate_random_token(length: int = 32) -> str:
    """
    إنشاء رمز عشوائي آمن.
    
    Args:
        length: طول الرمز
        
    Returns:
        رمز عشوائي
    """
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def generate_verification_code(length: int = 6) -> str:
    """
    إنشاء رمز تحقق رقمي.
    
    Args:
        length: طول الرمز
        
    Returns:
        رمز تحقق رقمي
    """
    return ''.join(secrets.choice(string.digits) for _ in range(length))


def generate_reset_token() -> str:
    """
    إنشاء رمز إعادة تعيين كلمة المرور.
    
    Returns:
        رمز إعادة التعيين
    """
    return generate_random_token(64)


# ============================================================
# دوال التحقق من الأمان
# ============================================================

def validate_password_strength(password: str) -> Tuple[bool, Optional[str]]:
    """
    التحقق من قوة كلمة المرور.
    
    Args:
        password: كلمة المرور المراد التحقق منها
        
    Returns:
        (True, None) إذا كانت قوية، (False, رسالة الخطأ) إذا كانت ضعيفة
    """
    if len(password) < 8:
        return False, "كلمة المرور يجب أن تكون 8 أحرف على الأقل"
    
    if not any(c.isupper() for c in password):
        return False, "كلمة المرور يجب أن تحتوي على حرف كبير واحد على الأقل"
    
    if not any(c.islower() for c in password):
        return False, "كلمة المرور يجب أن تحتوي على حرف صغير واحد على الأقل"
    
    if not any(c.isdigit() for c in password):
        return False, "كلمة المرور يجب أن تحتوي على رقم واحد على الأقل"
    
    if not any(c in string.punctuation for c in password):
        return False, "كلمة المرور يجب أن تحتوي على رمز خاص واحد على الأقل"
    
    return True, None


def sanitize_input(text: str, max_length: int = 1000) -> str:
    """
    تنظيف النص من الأحرف الخطرة.
    
    Args:
        text: النص المراد تنظيفه
        max_length: الحد الأقصى للطول
        
    Returns:
        النص المنظف
    """
    if not text:
        return ""
    
    # قطع النص إذا كان طويلاً
    if len(text) > max_length:
        text = text[:max_length]
    
    # إزالة الأحرف الخطرة
    dangerous_chars = ["<", ">", "&", '"', "'", "/", "\\", ";", "`", "(", ")"]
    for char in dangerous_chars:
        text = text.replace(char, "")
    
    return text.strip()


# ============================================================
# دوال خاصة بـ OAuth
# ============================================================

def generate_state_token() -> str:
    """
    إنشاء رمز حالة لـ OAuth.
    
    Returns:
        رمز الحالة
    """
    return generate_random_token(32)


def generate_nonce() -> str:
    """
    إنشاء nonce لـ OAuth.
    
    Returns:
        رمز nonce
    """
    return generate_random_token(32)


# ============================================================
# دوال المصادقة المتقدمة
# ============================================================

def authenticate_user(db, email: str, password: str):
    """
    مصادقة المستخدم (يدعم المحلي و OAuth).
    
    Args:
        db: جلسة قاعدة البيانات
        email: البريد الإلكتروني
        password: كلمة المرور
        
    Returns:
        كائن المستخدم إذا تم المصادقة بنجاح، None إذا فشلت
    """
    from app.modules.users.models import User
    
    # البحث عن المستخدم
    user = db.query(User).filter(User.email == email).first()
    
    if not user:
        return None
    
    # إذا كان المستخدم مسجلاً عبر OAuth وليس لديه كلمة مرور
    if user.is_oauth_user and user.password_hash is None:
        # لا يمكن المصادقة بكلمة مرور
        return None
    
    # التحقق من كلمة المرور
    if not verify_password(password, user.password_hash):
        return None
    
    # تحديث آخر تسجيل دخول
    user.last_login = datetime.now(timezone.utc)
    db.commit()
    
    return user


def create_oauth_user(
    db,
    provider: str,
    oauth_id: str,
    email: str,
    name: str,
    avatar_url: Optional[str] = None,
    role: str = "buyer"
):
    """
    إنشاء مستخدم جديد عبر OAuth.
    
    Args:
        db: جلسة قاعدة البيانات
        provider: مزود OAuth (google, facebook, github)
        oauth_id: معرف المستخدم من المزود
        email: البريد الإلكتروني
        name: الاسم
        avatar_url: رابط الصورة (اختياري)
        role: الدور (افتراضي: buyer)
        
    Returns:
        كائن المستخدم الذي تم إنشاؤه
    """
    from app.modules.users.models import User
    
    # التحقق من عدم وجود مستخدم بنفس البريد
    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user:
        # إذا كان المستخدم موجوداً ولكن ليس لديه OAuth، قم بربطه
        if not existing_user.is_oauth_user:
            existing_user.oauth_provider = provider
            existing_user.oauth_id = oauth_id
            existing_user.is_verified = True
            db.commit()
            db.refresh(existing_user)
            return existing_user
        else:
            # مستخدم موجود بالفعل مع OAuth
            return existing_user
    
    # إنشاء مستخدم جديد
    user = User(
        email=email,
        name=name,
        avatar_url=avatar_url,
        oauth_provider=provider,
        oauth_id=oauth_id,
        password_hash=None,  # لا يحتاج كلمة مرور
        is_active=True,
        is_verified=True,
        role=role
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # إنشاء ملف تعريف للمستخدم
    from app.modules.users.models import UserProfile
    profile = UserProfile(
        user_id=user.id,
        preferred_language=settings.DEFAULT_LANGUAGE or "en",
        preferred_currency=settings.DEFAULT_CURRENCY or "SAR"
    )
    db.add(profile)
    db.commit()
    
    return user


def get_user_by_oauth(db, provider: str, oauth_id: str):
    """
    الحصول على مستخدم بواسطة معلومات OAuth.
    
    Args:
        db: جلسة قاعدة البيانات
        provider: مزود OAuth
        oauth_id: معرف المستخدم من المزود
        
    Returns:
        كائن المستخدم إذا وجد، None إذا لم يوجد
    """
    from app.modules.users.models import User
    
    return db.query(User).filter(
        User.oauth_provider == provider,
        User.oauth_id == oauth_id
    ).first()


def can_login_with_password(user) -> bool:
    """
    التحقق مما إذا كان المستخدم يمكنه تسجيل الدخول بكلمة مرور.
    
    Args:
        user: كائن المستخدم
        
    Returns:
        True إذا كان يمكنه تسجيل الدخول بكلمة مرور، False إذا كان OAuth فقط
    """
    if user is None:
        return False
    
    # المستخدم لديه كلمة مرور وليس مستخدم OAuth فقط
    return user.has_password and not user.is_oauth_user


def get_auth_methods(user) -> Dict[str, bool]:
    """
    الحصول على طرق المصادقة المتاحة للمستخدم.
    
    Args:
        user: كائن المستخدم
        
    Returns:
        قاموس يحتوي على طرق المصادقة المتاحة
    """
    if user is None:
        return {
            "password": False,
            "oauth": False,
            "oauth_provider": None
        }
    
    return {
        "password": user.has_password,
        "oauth": user.is_oauth_user,
        "oauth_provider": user.oauth_provider if user.is_oauth_user else None
    }


# ============================================================
# دوال إدارة الجلسات
# ============================================================

def create_session_token() -> str:
    """
    إنشاء رمز جلسة عشوائي آمن.
    
    Returns:
        رمز الجلسة
    """
    return generate_random_token(64)


def get_session_expiry(days: int = 7) -> datetime:
    """
    الحصول على تاريخ انتهاء الجلسة.
    
    Args:
        days: عدد أيام الصلاحية
        
    Returns:
        تاريخ انتهاء الجلسة
    """
    return datetime.now(timezone.utc) + timedelta(days=days)
