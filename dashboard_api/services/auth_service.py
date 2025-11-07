"""Authentication service logic."""

from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from models.user import User, Token
from models.audit import AuditLog
from utils.crypto import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    hash_token_for_storage,
    verify_token,
)
from config import settings


class AuthService:
    """Authentication service."""

    def __init__(self, db: Session):
        """Initialize auth service.

        Args:
            db: Database session.
        """
        self.db = db

    def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """Authenticate user with username and password.

        Args:
            username: Username.
            password: Plain text password.

        Returns:
            Optional[User]: User if authenticated, None otherwise.
        """
        user = self.db.query(User).filter(User.username == username).first()

        if not user:
            return None

        # Check if account is locked
        if user.locked_until and user.locked_until > datetime.utcnow():
            return None

        # Verify password
        if not verify_password(password, user.password_hash):
            # Increment failed attempts
            user.failed_login_attempts += 1

            # Lock account after 5 failed attempts
            if user.failed_login_attempts >= 5:
                user.locked_until = datetime.utcnow() + timedelta(minutes=15)

            self.db.commit()
            return None

        # Reset failed attempts on successful login
        user.failed_login_attempts = 0
        user.locked_until = None
        user.last_login = datetime.utcnow()
        self.db.commit()

        return user

    def create_tokens(
        self, user: User, ip_address: Optional[str] = None, user_agent: Optional[str] = None
    ) -> dict:
        """Create access and refresh tokens for user.

        Args:
            user: User to create tokens for.
            ip_address: Optional client IP address.
            user_agent: Optional client user agent.

        Returns:
            dict: Access token, refresh token, and expiry info.
        """
        # Create token payload
        payload = {"user_id": user.id, "username": user.username, "role": user.role}

        # Generate tokens
        access_token = create_access_token(payload)
        refresh_token = create_refresh_token(payload)

        # Store refresh token in database for tracking
        token_record = Token(
            user_id=user.id,
            token_hash=hash_token_for_storage(refresh_token),
            token_type="refresh",
            expires_at=datetime.utcnow() + timedelta(days=settings.refresh_token_expire_days),
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self.db.add(token_record)
        self.db.commit()

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": settings.access_token_expire_minutes * 60,
        }

    def refresh_access_token(self, refresh_token: str) -> Optional[dict]:
        """Refresh access token using refresh token.

        Args:
            refresh_token: Valid refresh token.

        Returns:
            Optional[dict]: New access token or None if refresh token invalid.
        """
        # Verify refresh token
        payload = verify_token(refresh_token, token_type="refresh")
        if not payload:
            return None

        # Check if token exists and is not revoked
        token_hash = hash_token_for_storage(refresh_token)
        token_record = (
            self.db.query(Token)
            .filter(Token.token_hash == token_hash, Token.revoked == False)
            .first()
        )

        if not token_record:
            return None

        # Get user
        user = self.db.query(User).filter(User.id == payload["user_id"]).first()
        if not user or not user.is_active:
            return None

        # Create new access token
        new_payload = {"user_id": user.id, "username": user.username, "role": user.role}

        access_token = create_access_token(new_payload)

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": settings.access_token_expire_minutes * 60,
        }

    def revoke_token(self, refresh_token: str) -> bool:
        """Revoke a refresh token (logout).

        Args:
            refresh_token: Refresh token to revoke.

        Returns:
            bool: True if revoked successfully.
        """
        token_hash = hash_token_for_storage(refresh_token)
        token_record = self.db.query(Token).filter(Token.token_hash == token_hash).first()

        if token_record:
            token_record.revoked = True
            token_record.revoked_at = datetime.utcnow()
            self.db.commit()
            return True

        return False

    def log_audit(
        self,
        user_id: int,
        action: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[dict] = None,
        ip_address: Optional[str] = None,
        success: bool = True,
        error_message: Optional[str] = None,
    ) -> None:
        """Log audit event.

        Args:
            user_id: User ID.
            action: Action performed.
            resource_type: Type of resource.
            resource_id: Resource identifier.
            details: Additional details.
            ip_address: Client IP address.
            success: Whether action succeeded.
            error_message: Error message if failed.
        """
        audit_log = AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            ip_address=ip_address,
            success=success,
            error_message=error_message,
        )
        self.db.add(audit_log)
        self.db.commit()
