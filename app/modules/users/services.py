"""User services for business logic."""

from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, desc, func

from app.database import SessionLocal
from app.modules.users.models import User, UserProfile
from app.modules.users.schemas import UserCreate, UserUpdate, UserProfileUpdate


class UserService:
    """Service for user CRUD operations."""
    
    @staticmethod
    def get_user_by_id(user_id: int, include_profile: bool = True) -> Optional[User]:
        """Get user by ID with optional profile loading."""
        db = SessionLocal()
        try:
            query = db.query(User)
            if include_profile:
                query = query.options(joinedload(User.profile))
            return query.filter(User.id == user_id, User.is_active == True).first()
        finally:
            db.close()
    
    @staticmethod
    def get_user_by_email(email: str, include_profile: bool = True) -> Optional[User]:
        """Get user by email with optional profile loading."""
        db = SessionLocal()
        try:
            query = db.query(User)
            if include_profile:
                query = query.options(joinedload(User.profile))
            return query.filter(User.email == email).first()
        finally:
            db.close()
    
    @staticmethod
    def get_user_by_email_strict(email: str) -> Optional[User]:
        """Get user by email even if inactive (for auth)."""
        db = SessionLocal()
        try:
            return db.query(User).filter(User.email == email).first()
        finally:
            db.close()
    
    @staticmethod
    def create_user(data: UserCreate) -> User:
        """Create a new user with profile."""
        db = SessionLocal()
        try:
            # Check if user exists
            existing = db.query(User).filter(User.email == data.email).first()
            if existing:
                raise ValueError(f"User with email {data.email} already exists")
            
            # Create user
            user = User(
                email=data.email,
                name=data.name,
                avatar_url=data.avatar_url,
                role=data.role,
                is_active=True
            )
            db.add(user)
            db.flush()  # Get user.id
            
            # Create default profile
            profile = UserProfile(
                user_id=user.id,
                preferred_language="en",
                preferred_currency="SAR",
                notifications_enabled=True,
                marketing_emails=True
            )
            db.add(profile)
            
            db.commit()
            db.refresh(user)
            
            # Load profile for response
            return db.query(User).options(joinedload(User.profile)).filter(User.id == user.id).first()
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()
    
    @staticmethod
    def update_user(user_id: int, data: UserUpdate) -> Optional[User]:
        """Update user information."""
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return None
            
            update_data = data.model_dump(exclude_unset=True)
            for key, value in update_data.items():
                if hasattr(user, key) and value is not None:
                    setattr(user, key, value)
            
            user.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(user)
            
            return db.query(User).options(joinedload(User.profile)).filter(User.id == user_id).first()
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()
    
    @staticmethod
    def update_user_profile(user_id: int, data: UserProfileUpdate) -> Optional[UserProfile]:
        """Update user profile/preferences."""
        db = SessionLocal()
        try:
            profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
            if not profile:
                return None
            
            update_data = data.model_dump(exclude_unset=True)
            for key, value in update_data.items():
                if hasattr(profile, key) and value is not None:
                    setattr(profile, key, value)
            
            profile.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(profile)
            
            return profile
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()
    
    @staticmethod
    def update_role(user_id: int, new_role: str, admin_user_id: int) -> Optional[User]:
        """Update user role (admin only)."""
        db = SessionLocal()
        try:
            # Verify admin exists and is admin
            admin = db.query(User).filter(User.id == admin_user_id).first()
            if not admin or admin.role != "admin":
                raise PermissionError("Only admins can change user roles")
            
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return None
            
            # Prevent self-demotion from admin? Allow for flexibility
            if user_id == admin_user_id and new_role != "admin":
                # Allow but warn? We'll allow it
                pass
            
            user.role = new_role
            user.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(user)
            
            return db.query(User).options(joinedload(User.profile)).filter(User.id == user_id).first()
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()
    
    @staticmethod
    def deactivate_user(user_id: int, admin_user_id: int) -> bool:
        """Soft-delete user (set is_active=False)."""
        db = SessionLocal()
        try:
            # Verify admin
            admin = db.query(User).filter(User.id == admin_user_id).first()
            if not admin or admin.role != "admin":
                raise PermissionError("Only admins can deactivate users")
            
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return False
            
            # Prevent self-deactivation
            if user_id == admin_user_id:
                raise ValueError("Admin cannot deactivate themselves")
            
            user.is_active = False
            user.updated_at = datetime.utcnow()
            db.commit()
            
            return True
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()
    
    @staticmethod
    def record_last_login(user_id: int) -> None:
        """Record user's last login timestamp."""
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                user.last_login = datetime.utcnow()
                db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()


class UserQueryService:
    """Service for user queries (search, filter, pagination)."""
    
    @staticmethod
    def list_users(
        page: int = 1,
        per_page: int = 20,
        search: Optional[str] = None,
        role: Optional[str] = None,
        is_active: Optional[bool] = None,
        order_by: str = "created_at",
        order_desc: bool = True
    ) -> Dict[str, Any]:
        """List users with filtering and pagination."""
        db = SessionLocal()
        try:
            query = db.query(User).options(joinedload(User.profile))
            
            # Apply filters
            if search:
                search_term = f"%{search}%"
                query = query.filter(
                    or_(
                        User.email.ilike(search_term),
                        User.name.ilike(search_term)
                    )
                )
            
            if role:
                query = query.filter(User.role == role)
            
            if is_active is not None:
                query = query.filter(User.is_active == is_active)
            
            # Count total
            total = query.count()
            
            # Apply ordering
            if order_by == "created_at":
                order_col = User.created_at
            elif order_by == "name":
                order_col = User.name
            elif order_by == "email":
                order_col = User.email
            else:
                order_col = User.created_at
            
            if order_desc:
                query = query.order_by(desc(order_col))
            else:
                query = query.order_by(order_col)
            
            # Apply pagination
            offset = (page - 1) * per_page
            items = query.offset(offset).limit(per_page).all()
            
            total_pages = (total + per_page - 1) // per_page if total > 0 else 1
            
            return {
                "items": items,
                "total": total,
                "page": page,
                "per_page": per_page,
                "total_pages": total_pages
            }
        finally:
            db.close()
    
    @staticmethod
    def get_users_by_role(role: str, limit: int = 100) -> List[User]:
        """Get all users with a specific role."""
        db = SessionLocal()
        try:
            return (
                db.query(User)
                .filter(User.role == role, User.is_active == True)
                .limit(limit)
                .all()
            )
        finally:
            db.close()
    
    @staticmethod
    def search_users_by_email(email_prefix: str, limit: int = 10) -> List[User]:
        """Search users by email prefix (for autocomplete)."""
        db = SessionLocal()
        try:
            term = f"{email_prefix}%"
            return (
                db.query(User)
                .filter(User.email.ilike(term), User.is_active == True)
                .limit(limit)
                .all()
            )
        finally:
            db.close()
