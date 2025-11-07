"""User management routes."""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import List

from database import get_db
from dependencies import require_admin
from models.user import User, UserCreate, UserUpdate, UserResponse
from utils.crypto import hash_password
from services.auth_service import AuthService

router = APIRouter()


@router.get("/", response_model=List[UserResponse])
async def list_users(current_user=Depends(require_admin), db: Session = Depends(get_db)):
    """List all users (admin only).

    Args:
        current_user: Current authenticated user (admin only).
        db: Database session.

    Returns:
        List[UserResponse]: List of users.
    """
    users = db.query(User).all()
    return users


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int, current_user=Depends(require_admin), db: Session = Depends(get_db)
):
    """Get user by ID (admin only).

    Args:
        user_id: User ID.
        current_user: Current authenticated user (admin only).
        db: Database session.

    Returns:
        UserResponse: User details.

    Raises:
        HTTPException: If user not found.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    request: Request,
    user_data: UserCreate,
    current_user=Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Create a new user (admin only).

    Args:
        request: FastAPI request.
        user_data: User creation data.
        current_user: Current authenticated user (admin only).
        db: Database session.

    Returns:
        UserResponse: Created user.

    Raises:
        HTTPException: If username or email already exists.
    """
    # Check if username exists
    if db.query(User).filter(User.username == user_data.username).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Username already exists"
        )

    # Check if email exists
    if db.query(User).filter(User.email == user_data.email).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already exists")

    # Create user
    new_user = User(
        username=user_data.username,
        email=user_data.email,
        password_hash=hash_password(user_data.password),
        full_name=user_data.full_name,
        role=user_data.role,
        created_by=current_user.id,
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Log action
    auth_service = AuthService(db)
    auth_service.log_audit(
        user_id=current_user.id,
        action="user_created",
        resource_type="user",
        resource_id=str(new_user.id),
        details={"username": new_user.username, "role": new_user.role},
        ip_address=request.client.host if request.client else None,
    )

    return new_user


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    request: Request,
    user_id: int,
    user_data: UserUpdate,
    current_user=Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Update user (admin only).

    Args:
        request: FastAPI request.
        user_id: User ID to update.
        user_data: Update data.
        current_user: Current authenticated user (admin only).
        db: Database session.

    Returns:
        UserResponse: Updated user.

    Raises:
        HTTPException: If user not found or email already exists.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Check email uniqueness if changing
    if user_data.email and user_data.email != user.email:
        if db.query(User).filter(User.email == user_data.email).first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Email already exists"
            )
        user.email = user_data.email

    # Update fields
    if user_data.full_name is not None:
        user.full_name = user_data.full_name
    if user_data.role is not None:
        user.role = user_data.role
    if user_data.is_active is not None:
        user.is_active = user_data.is_active

    db.commit()
    db.refresh(user)

    # Log action
    auth_service = AuthService(db)
    auth_service.log_audit(
        user_id=current_user.id,
        action="user_updated",
        resource_type="user",
        resource_id=str(user.id),
        details={"username": user.username},
        ip_address=request.client.host if request.client else None,
    )

    return user


@router.delete("/{user_id}")
async def delete_user(
    request: Request,
    user_id: int,
    current_user=Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Delete user (admin only).

    Args:
        request: FastAPI request.
        user_id: User ID to delete.
        current_user: Current authenticated user (admin only).
        db: Database session.

    Returns:
        dict: Deletion confirmation.

    Raises:
        HTTPException: If user not found or trying to delete self.
    """
    # Prevent self-deletion
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete your own account"
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    username = user.username

    db.delete(user)
    db.commit()

    # Log action
    auth_service = AuthService(db)
    auth_service.log_audit(
        user_id=current_user.id,
        action="user_deleted",
        resource_type="user",
        resource_id=str(user_id),
        details={"username": username},
        ip_address=request.client.host if request.client else None,
    )

    return {"message": f"User {username} deleted successfully"}
