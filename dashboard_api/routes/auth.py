"""Authentication routes."""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from database import get_db
from dependencies import get_current_user
from models.user import LoginRequest, TokenResponse, TokenRefreshRequest, UserResponse
from services.auth_service import AuthService

router = APIRouter()


@router.post("/login", response_model=TokenResponse)
async def login(request: Request, login_data: LoginRequest, db: Session = Depends(get_db)):
    """Login with username and password.

    Args:
        request: FastAPI request.
        login_data: Login credentials.
        db: Database session.

    Returns:
        TokenResponse: Access and refresh tokens.

    Raises:
        HTTPException: If credentials are invalid.
    """
    auth_service = AuthService(db)

    # Authenticate user
    user = auth_service.authenticate_user(login_data.username, login_data.password)
    if not user:
        # Log failed login attempt
        auth_service.log_audit(
            user_id=0,  # Unknown user
            action="login_failed",
            details={"username": login_data.username},
            ip_address=request.client.host if request.client else None,
            success=False,
            error_message="Invalid credentials",
        )

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create tokens
    tokens = auth_service.create_tokens(
        user,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )

    # Log successful login
    auth_service.log_audit(
        user_id=user.id,
        action="login_success",
        ip_address=request.client.host if request.client else None,
    )

    return tokens


@router.post("/refresh", response_model=dict)
async def refresh_token(refresh_data: TokenRefreshRequest, db: Session = Depends(get_db)):
    """Refresh access token using refresh token.

    Args:
        refresh_data: Refresh token.
        db: Database session.

    Returns:
        dict: New access token.

    Raises:
        HTTPException: If refresh token is invalid.
    """
    auth_service = AuthService(db)

    tokens = auth_service.refresh_access_token(refresh_data.refresh_token)
    if not tokens:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return tokens


@router.post("/logout")
async def logout(
    request: Request,
    refresh_data: TokenRefreshRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Logout and revoke refresh token.

    Args:
        request: FastAPI request.
        refresh_data: Refresh token to revoke.
        current_user: Current authenticated user.
        db: Database session.

    Returns:
        dict: Logout confirmation.
    """
    auth_service = AuthService(db)

    # Revoke refresh token
    auth_service.revoke_token(refresh_data.refresh_token)

    # Log logout
    auth_service.log_audit(
        user_id=current_user.id,
        action="logout",
        ip_address=request.client.host if request.client else None,
    )

    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user=Depends(get_current_user)):
    """Get current user information.

    Args:
        current_user: Current authenticated user.

    Returns:
        UserResponse: Current user details.
    """
    return current_user
