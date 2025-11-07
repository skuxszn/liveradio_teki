"""Configuration management routes."""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import List, Optional

from database import get_db
from dependencies import get_current_user, require_admin, require_operator
from models.config import Setting, SettingResponse, SettingUpdate, SettingsBulkUpdate
from services.auth_service import AuthService

router = APIRouter()


@router.get("/internal/export")
async def export_settings_internal(
    request: Request,
    db: Session = Depends(get_db)
):
    """Export all settings for internal services (metadata_watcher, etc.).
    
    This endpoint is for internal service-to-service communication.
    Requires API token authentication (no user session needed).
    
    Args:
        request: FastAPI request for token validation.
        db: Database session.
        
    Returns:
        dict: All settings organized by category.
        
    Raises:
        HTTPException: If API token is invalid.
    """
    import os
    from datetime import datetime
    
    # Validate API token for internal services
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header"
        )
    
    provided_token = auth_header.split(" ")[1]
    expected_token = os.getenv("API_TOKEN", "")
    
    if not expected_token or provided_token != expected_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API token"
        )
    
    # Fetch all settings from database
    settings = db.query(Setting).all()
    
    config_dict = {}
    for setting in settings:
        if setting.category not in config_dict:
            config_dict[setting.category] = {}
        
        # Use actual value or default, and don't mask secrets for internal services
        config_dict[setting.category][setting.key] = setting.value or setting.default_value
    
    return {
        "settings": config_dict,
        "exported_at": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }


@router.get("/", response_model=List[SettingResponse])
async def get_all_settings(
    category: Optional[str] = None,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all configuration settings.
    
    Args:
        category: Optional category filter.
        current_user: Current authenticated user.
        db: Database session.
        
    Returns:
        List[SettingResponse]: List of settings.
    """
    query = db.query(Setting)
    
    if category:
        query = query.filter(Setting.category == category)
    
    settings = query.all()
    
    # Mask secret values for non-admin users
    if current_user.role != "admin":
        for setting in settings:
            if setting.is_secret and setting.value:
                setting.value = "••••••••"
    
    return settings


@router.get("/{category}", response_model=List[SettingResponse])
async def get_settings_by_category(
    category: str,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get settings by category.
    
    Args:
        category: Settings category.
        current_user: Current authenticated user.
        db: Database session.
        
    Returns:
        List[SettingResponse]: Settings in category.
    """
    settings = db.query(Setting).filter(Setting.category == category).all()
    
    # Mask secret values for non-admin users
    if current_user.role != "admin":
        for setting in settings:
            if setting.is_secret and setting.value:
                setting.value = "••••••••"
    
    return settings


@router.put("/{category}/{key}")
async def update_setting(
    request: Request,
    category: str,
    key: str,
    update_data: SettingUpdate,
    current_user = Depends(require_operator),
    db: Session = Depends(get_db)
):
    """Update a single setting.
    
    Args:
        request: FastAPI request.
        category: Setting category.
        key: Setting key.
        update_data: New value.
        current_user: Current authenticated user (operator or admin).
        db: Database session.
        
    Returns:
        SettingResponse: Updated setting.
        
    Raises:
        HTTPException: If setting not found.
    """
    setting = db.query(Setting).filter(
        Setting.category == category,
        Setting.key == key
    ).first()
    
    if not setting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Setting not found: {category}.{key}"
        )
    
    # Store old value for audit
    old_value = setting.value
    
    # Update value
    setting.value = update_data.value
    db.commit()
    db.refresh(setting)
    
    # Log action
    auth_service = AuthService(db)
    auth_service.log_audit(
        user_id=current_user.id,
        action="config_updated",
        resource_type="setting",
        resource_id=f"{category}.{key}",
        details={"old_value": old_value, "new_value": update_data.value if not setting.is_secret else "***"},
        ip_address=request.client.host if request.client else None
    )
    
    return setting


@router.post("/bulk-update")
async def bulk_update_settings(
    request: Request,
    bulk_data: SettingsBulkUpdate,
    current_user = Depends(require_operator),
    db: Session = Depends(get_db)
):
    """Bulk update multiple settings.
    
    Args:
        request: FastAPI request.
        bulk_data: Map of settings to update.
        current_user: Current authenticated user (operator or admin).
        db: Database session.
        
    Returns:
        dict: Update results.
    """
    updated = []
    errors = []
    
    for full_key, new_value in bulk_data.updates.items():
        try:
            category, key = full_key.split(".", 1)
            
            setting = db.query(Setting).filter(
                Setting.category == category,
                Setting.key == key
            ).first()
            
            if setting:
                setting.value = new_value
                updated.append(full_key)
            else:
                errors.append(f"Setting not found: {full_key}")
        
        except ValueError:
            errors.append(f"Invalid setting key format: {full_key}")
    
    db.commit()
    
    # Log bulk update
    auth_service = AuthService(db)
    auth_service.log_audit(
        user_id=current_user.id,
        action="config_bulk_updated",
        resource_type="settings",
        details={"updated_count": len(updated), "error_count": len(errors)},
        ip_address=request.client.host if request.client else None
    )
    
    return {
        "updated": updated,
        "errors": errors,
        "success_count": len(updated),
        "error_count": len(errors)
    }


@router.get("/export", response_model=dict)
async def export_configuration(
    current_user = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Export all configuration settings.
    
    Args:
        current_user: Current authenticated user (admin only).
        db: Database session.
        
    Returns:
        dict: All settings organized by category.
    """
    from datetime import datetime
    
    settings = db.query(Setting).all()
    
    config_dict = {}
    for setting in settings:
        if setting.category not in config_dict:
            config_dict[setting.category] = {}
        
        config_dict[setting.category][setting.key] = setting.value or setting.default_value
    
    return {
        "settings": config_dict,
        "exported_at": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }


@router.post("/test-azuracast")
async def test_azuracast_connection(
    request: Request,
    current_user = Depends(require_operator),
    db: Session = Depends(get_db)
):
    """Test connection to AzuraCast instance.
    
    Args:
        request: FastAPI request.
        current_user: Current authenticated user (operator or admin).
        db: Database session.
        
    Returns:
        dict: Connection test results.
    """
    import httpx
    from datetime import datetime
    
    # Get AzuraCast settings
    azuracast_url = db.query(Setting).filter(
        Setting.category == "stream",
        Setting.key == "AZURACAST_URL"
    ).first()
    
    azuracast_api_key = db.query(Setting).filter(
        Setting.category == "stream",
        Setting.key == "AZURACAST_API_KEY"
    ).first()
    
    if not azuracast_url or not azuracast_url.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="AzuraCast URL not configured"
        )
    
    if not azuracast_api_key or not azuracast_api_key.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="AzuraCast API key not configured"
        )
    
    # Test connection
    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            response = await client.get(
                f"{azuracast_url.value}/api/status",
                headers={"X-API-Key": azuracast_api_key.value}
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Log successful test
                auth_service = AuthService(db)
                auth_service.log_audit(
                    user_id=current_user.id,
                    action="azuracast_connection_tested",
                    resource_type="config",
                    details={"success": True},
                    ip_address=request.client.host if request.client else None
                )
                
                return {
                    "success": True,
                    "message": "Successfully connected to AzuraCast",
                    "azuracast_version": data.get("version", "unknown"),
                    "online": data.get("online", False),
                    "tested_at": datetime.utcnow().isoformat()
                }
            else:
                return {
                    "success": False,
                    "message": f"AzuraCast returned status code {response.status_code}",
                    "tested_at": datetime.utcnow().isoformat()
                }
    
    except httpx.TimeoutException:
        return {
            "success": False,
            "message": "Connection timeout - AzuraCast instance not responding",
            "tested_at": datetime.utcnow().isoformat()
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Connection failed: {str(e)}",
            "tested_at": datetime.utcnow().isoformat()
        }


@router.post("/generate-token")
async def generate_security_token(
    request: Request,
    token_type: str,
    current_user = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Generate a new security token.
    
    Args:
        request: FastAPI request.
        token_type: Type of token to generate (webhook_secret, api_token, jwt_secret).
        current_user: Current authenticated user (admin only).
        db: Database session.
        
    Returns:
        dict: New token value.
        
    Raises:
        HTTPException: If token type is invalid.
    """
    import secrets
    from datetime import datetime
    
    valid_token_types = ["webhook_secret", "api_token", "jwt_secret"]
    
    if token_type not in valid_token_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid token type. Must be one of: {', '.join(valid_token_types)}"
        )
    
    # Map token type to setting key
    token_key_map = {
        "webhook_secret": "WEBHOOK_SECRET",
        "api_token": "API_TOKEN",
        "jwt_secret": "JWT_SECRET"
    }
    
    setting_key = token_key_map[token_type]
    
    # Generate secure random token (64 characters)
    new_token = secrets.token_urlsafe(48)
    
    # Update setting
    setting = db.query(Setting).filter(
        Setting.category == "security",
        Setting.key == setting_key
    ).first()
    
    if not setting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Setting not found: security.{setting_key}"
        )
    
    old_value = setting.value
    setting.value = new_token
    db.commit()
    
    # Log token generation
    auth_service = AuthService(db)
    auth_service.log_audit(
        user_id=current_user.id,
        action="security_token_generated",
        resource_type="setting",
        resource_id=f"security.{setting_key}",
        details={"token_type": token_type, "regenerated": True},
        ip_address=request.client.host if request.client else None
    )
    
    return {
        "success": True,
        "token": new_token,
        "token_type": token_type,
        "generated_at": datetime.utcnow().isoformat(),
        "message": f"New {token_type} generated successfully. Please update your configuration."
    }

