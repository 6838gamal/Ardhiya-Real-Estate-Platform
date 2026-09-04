"""User API routes."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.config.database import get_db
# ❌ حذف الاستيراد المباشر من auth.dependencies
# from app.modules.auth.dependencies import get_current_user, require_admin
from app.modules.users.models import User
from app.modules.users.schemas import (
    UserUpdate,
    UserProfileUpdate,
    UserResponse,
    UserMeResponse,
    UserListResponse,
    RoleUpdate,
    UserNotFoundError,
)
from app.modules.users.services import UserService, UserQueryService

router = APIRouter(prefix="/api/users", tags=["Users"])


# ✅ دوال مساعدة للاستيراد المتأخر
def _get_current_user_dependency():
    """Get current_user dependency with lazy import."""
    from app.modules.auth.dependencies import get_current_user
    return get_current_user


def _get_require_admin_dependency():
    """Get require_admin dependency with lazy import."""
    from app.modules.auth.dependencies import require_admin
    return require_admin


@router.get("/me", response_model=UserMeResponse)
async def get_current_user_profile(
    current_user: User = Depends(_get_current_user_dependency())
):
    """
    Get the current user's full profile.
    
    Returns user details including profile preferences.
    """
    user = UserService.get_user_by_id(current_user.id, include_profile=True)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user


@router.put("/me", response_model=UserMeResponse)
async def update_current_user_profile(
    update_data: UserUpdate,
    current_user: User = Depends(_get_current_user_dependency())
):
    """
    Update the current user's profile.
    
    Updates name, phone, bio, or avatar URL.
    """
    user = UserService.update_user(current_user.id, update_data)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user


@router.put("/me/profile", response_model=UserMeResponse)
async def update_current_user_preferences(
    update_data: UserProfileUpdate,
    current_user: User = Depends(_get_current_user_dependency())
):
    """
    Update the current user's preferences.
    
    Updates language, currency, notification settings.
    """
    # Update profile
    profile = UserService.update_user_profile(current_user.id, update_data)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User profile not found"
        )
    
    # Return full user with updated profile
    user = UserService.get_user_by_id(current_user.id, include_profile=True)
    return user


@router.get("/{user_id}", response_model=UserResponse)
async def get_user_by_id(
    user_id: int,
    current_user: User = Depends(_get_current_user_dependency())
):
    """
    Get a user by ID (public fields).
    
    Users can view any active user's public information.
    """
    user = UserService.get_user_by_id(user_id, include_profile=False)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found"
        )
    return user


@router.get("/", response_model=UserListResponse)
async def list_users(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search by email or name"),
    role: Optional[str] = Query(None, description="Filter by role"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    order_by: str = Query("created_at", description="Order by field"),
    order_desc: bool = Query(True, description="Order descending"),
    current_user: User = Depends(_get_require_admin_dependency())
):
    """
    List users with pagination and filters.
    
    **Admin only.** Allows searching, filtering, and sorting users.
    """
    result = UserQueryService.list_users(
        page=page,
        per_page=per_page,
        search=search,
        role=role,
        is_active=is_active,
        order_by=order_by,
        order_desc=order_desc
    )
    return result


@router.put("/{user_id}/role", response_model=UserResponse)
async def update_user_role(
    user_id: int,
    role_update: RoleUpdate,
    current_user: User = Depends(_get_require_admin_dependency())
):
    """
    Update a user's role.
    
    **Admin only.** Can change any user's role.
    """
    try:
        user = UserService.update_role(user_id, role_update.role, current_user.id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID {user_id} not found"
            )
        return user
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_user(
    user_id: int,
    current_user: User = Depends(_get_require_admin_dependency())
):
    """
    Deactivate a user (soft delete).
    
    **Admin only.** Sets is_active=False. Admin cannot deactivate themselves.
    """
    try:
        success = UserService.deactivate_user(user_id, current_user.id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID {user_id} not found"
            )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    return None


# ============ Health Check ============

@router.get("/health", include_in_schema=False)
async def users_health_check():
    """Health check endpoint for users module."""
    return {"status": "ok", "module": "users"}
