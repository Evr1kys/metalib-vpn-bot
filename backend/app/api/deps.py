"""
API Dependencies

Provides dependency injection for:
- Database sessions
- Authentication (JWT via cookies or headers)
- Bot API token verification
- Admin permission checks
"""
from typing import Optional
from fastapi import Depends, HTTPException, status, Header, Security, Request, Cookie
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.config import settings
from app.core.security import decode_token, verify_api_key
from app.models import AdminUser, User
from sqlalchemy import select


# Cookie name for admin sessions
ADMIN_SESSION_COOKIE = "admin_session"

# Security schemes
security = HTTPBearer(auto_error=False)  # auto_error=False to allow cookie fallback


async def verify_bot_token(
    x_bot_token: str = Header(None, alias="X-Bot-Token"),
    authorization: Optional[str] = Header(None)
) -> bool:
    """Verify bot API token"""
    token = None
    
    # Try X-Bot-Token header first
    if x_bot_token:
        token = x_bot_token
    # Then try Authorization header
    elif authorization:
        if authorization.startswith("Bearer "):
            token = authorization.replace("Bearer ", "")
        else:
            token = authorization
    
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API token"
        )
    
    if not verify_api_key(token, settings.bot_api_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API token"
        )
    
    return True


async def get_current_admin(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security),
    db: AsyncSession = Depends(get_db)
) -> AdminUser:
    """
    Get current admin user from JWT token.
    
    Supports both:
    - httpOnly cookie (preferred, more secure)
    - Authorization header with Bearer token (backward compatibility)
    """
    token = None
    
    # Priority 1: httpOnly cookie (most secure)
    cookie_token = request.cookies.get(ADMIN_SESSION_COOKIE)
    if cookie_token:
        token = cookie_token
    
    # Priority 2: Authorization header
    elif credentials:
        token = credentials.credentials
    
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    payload = decode_token(token)
    
    if not payload or payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    admin_id = payload.get("sub")
    
    if not admin_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )
    
    admin = await db.get(AdminUser, admin_id)
    
    if not admin or not admin.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin user not found or inactive"
        )
    
    if admin.is_locked():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is locked"
        )
    
    # Store user_id in request state for rate limiting
    request.state.user_id = str(admin.id)
    
    return admin


async def require_admin_permission(
    permission: str,
    admin: AdminUser = Depends(get_current_admin)
) -> AdminUser:
    """Check if admin has specific permission"""
    if not admin.has_permission(permission):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permission denied: {permission}"
        )
    
    return admin


def get_admin_with_permission(permission: str):
    """Dependency factory for permission check"""
    async def _check(admin: AdminUser = Depends(get_current_admin)) -> AdminUser:
        return await require_admin_permission(permission, admin)
    
    return _check


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Get current user from JWT token"""
    token = credentials.credentials
    
    payload = decode_token(token)
    
    if not payload or payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    
    user_id = payload.get("sub")
    
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )
    
    # Try to get by UUID first, then by telegram_id
    user = await db.get(User, user_id)
    
    if not user:
        # Try by telegram_id
        try:
            telegram_id = int(user_id)
            stmt = select(User).where(User.telegram_id == telegram_id)
            result = await db.execute(stmt)
            user = result.scalar_one_or_none()
        except (ValueError, TypeError):
            pass
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    return user


async def get_bot_user(
    telegram_id: int = None,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_bot_token)  # SECURITY: Require bot token
) -> User:
    """
    Get user by telegram_id (for bot endpoints)
    
    SECURITY: This endpoint is protected by bot token verification.
    Only the bot can call this endpoint.
    """
    if not telegram_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="telegram_id is required"
        )
    
    stmt = select(User).where(User.telegram_id == telegram_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return user
