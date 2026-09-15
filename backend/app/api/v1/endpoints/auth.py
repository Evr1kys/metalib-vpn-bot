"""
Authentication endpoints for admin panel with 2FA support

Features:
- Rate limiting on login/2FA endpoints
- httpOnly cookie support for tokens
- Redis-based 2FA session storage
- IP-based brute force protection
"""
import secrets
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from pydantic import BaseModel, EmailStr
import httpx

from app.core.database import get_db
from app.core.config import settings
from app.core.redis import get_redis, cache_set, cache_get, cache_delete
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.core.logging import logger
from app.core.rate_limit import limiter, RateLimitConfig, get_user_identifier
from app.core.audit import audit
from app.models import AdminUser
from app.api.deps import get_current_admin

router = APIRouter()

# ===== Cookie Configuration =====
COOKIE_NAME = "admin_session"
COOKIE_REFRESH_NAME = "admin_refresh"
COOKIE_MAX_AGE = 60 * 60 * 24 * 7  # 7 days
COOKIE_SECURE = settings.environment == "production"
COOKIE_SAMESITE = "lax"  # Allows cross-origin POST from same site
COOKIE_DOMAIN = ".metalib.xyz" if settings.environment == "production" else None


def set_auth_cookies(response: Response, access_token: str, refresh_token: str):
    """Set httpOnly cookies for authentication tokens"""
    response.set_cookie(
        key=COOKIE_NAME,
        value=access_token,
        max_age=settings.jwt_access_token_expire_minutes * 60,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        domain=COOKIE_DOMAIN,
        path="/",
    )
    response.set_cookie(
        key=COOKIE_REFRESH_NAME,
        value=refresh_token,
        max_age=COOKIE_MAX_AGE,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        domain=COOKIE_DOMAIN,
        path="/api/v1/auth/refresh",  # Only sent for refresh endpoint
    )


def clear_auth_cookies(response: Response):
    """Clear authentication cookies on logout"""
    response.delete_cookie(key=COOKIE_NAME, domain=COOKIE_DOMAIN, path="/")
    response.delete_cookie(key=COOKIE_REFRESH_NAME, domain=COOKIE_DOMAIN, path="/api/v1/auth/refresh")


class LoginRequest(BaseModel):
    """Login request"""
    username: str
    password: str


class LoginResponse(BaseModel):
    """Login response"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    admin: dict


class TwoFARequiredResponse(BaseModel):
    """2FA required response"""
    requires_2fa: bool = True
    session_token: str
    message: str = "2FA code sent to Telegram"


class Verify2FARequest(BaseModel):
    """Verify 2FA request"""
    session_token: str
    code: str


class RefreshRequest(BaseModel):
    """Refresh token request"""
    refresh_token: str


async def send_telegram_message(chat_id: int, message: str) -> bool:
    """Send message via Telegram Bot"""
    try:
        bot_token = settings.telegram_bot_token
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json={
                "chat_id": chat_id,
                "text": message,
                "parse_mode": "HTML"
            })
            return response.status_code == 200
    except Exception as e:
        logger.error(f"Failed to send Telegram message: {e}")
        return False


async def generate_2fa_code(db: AsyncSession, admin_id: str, ip_address: str = None) -> str:
    """Generate and store 2FA code in Redis (more reliable than dict)"""
    # Generate 6-digit code
    code = ''.join([str(secrets.randbelow(10)) for _ in range(6)])
    
    # Store code in Redis with 5 minute TTL
    redis_key = f"2fa:code:{admin_id}"
    await cache_set(redis_key, {
        "code": code,
        "ip_address": ip_address,
        "created_at": datetime.utcnow().isoformat()
    }, expire=300)  # 5 minutes
    
    logger.info(f"2FA code generated for admin {admin_id}")
    
    return code


async def verify_2fa_code(db: AsyncSession, admin_id: str, code: str) -> bool:
    """Verify 2FA code from Redis"""
    redis_key = f"2fa:code:{admin_id}"
    stored = await cache_get(redis_key)
    
    if not stored:
        logger.warning(f"2FA code not found for admin {admin_id}")
        return False
    
    if stored.get("code") != code:
        logger.warning(f"Invalid 2FA code for admin {admin_id}")
        return False
    
    # Delete code after successful verification
    await cache_delete(redis_key)
    logger.info(f"2FA code verified for admin {admin_id}")
    
    return True


# Redis-based 2FA sessions (replaces in-memory dict)
async def create_2fa_session(admin_id: str) -> str:
    """Create 2FA session token in Redis"""
    session_token = secrets.token_urlsafe(32)
    redis_key = f"2fa:session:{session_token}"
    
    await cache_set(redis_key, {
        "admin_id": admin_id,
        "created_at": datetime.utcnow().isoformat()
    }, expire=300)  # 5 minutes
    
    return session_token


async def get_2fa_session(session_token: str) -> Optional[dict]:
    """Get 2FA session from Redis"""
    redis_key = f"2fa:session:{session_token}"
    return await cache_get(redis_key)


async def delete_2fa_session(session_token: str):
    """Delete 2FA session from Redis"""
    redis_key = f"2fa:session:{session_token}"
    await cache_delete(redis_key)


@router.post("/login")
@limiter.limit("5/minute")
@limiter.limit("20/hour")
async def login(
    request: Request,
    credentials: LoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """Admin login with 2FA support"""
    # Find admin by username
    stmt = select(AdminUser).where(AdminUser.username == credentials.username)
    result = await db.execute(stmt)
    admin = result.scalar_one_or_none()
    
    if not admin:
        logger.warning(f"Login attempt with unknown username: {credentials.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
    # Check if account is locked
    if admin.is_locked():
        logger.warning(f"Login attempt for locked account: {admin.username}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is locked"
        )
    
    # Check if account is active
    if not admin.is_active:
        logger.warning(f"Login attempt for inactive account: {admin.username}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive"
        )
    
    # Verify password
    if not verify_password(credentials.password, admin.password_hash):
        admin.failed_login_attempts += 1
        if admin.failed_login_attempts >= 5:
            admin.locked_until = datetime.utcnow() + timedelta(minutes=30)
            logger.warning(f"Account locked due to failed attempts: {admin.username}")
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
    # Check if 2FA is enabled and admin has telegram_id
    twofa_enabled = getattr(admin, 'twofa_enabled', True)
    telegram_id = getattr(admin, 'telegram_id', None)
    
    if twofa_enabled and telegram_id:
        # Generate 2FA code
        ip_address = request.client.host if request.client else None
        code = await generate_2fa_code(db, str(admin.id), ip_address)
        
        # Send code via Telegram
        message = f"""🔐 <b>Код подтверждения входа</b>

Ваш код: <code>{code}</code>

⏱ Действителен 5 минут
🌐 IP: {ip_address or 'Unknown'}

Если это не вы - игнорируйте это сообщение."""
        
        sent = await send_telegram_message(telegram_id, message)
        
        if not sent:
            logger.error(f"Failed to send 2FA code to admin {admin.username}")
            # Fall back to direct login if Telegram fails
        else:
            # Create session token for 2FA verification (Redis-based)
            session_token = await create_2fa_session(str(admin.id))
            
            logger.info(f"2FA code sent to admin: {admin.username}")
            
            return {
                "requires_2fa": True,
                "session_token": session_token,
                "message": "Код подтверждения отправлен в Telegram"
            }
    
    # No 2FA - direct login
    admin.failed_login_attempts = 0
    admin.last_login_at = datetime.utcnow()
    await db.commit()
    
    # Audit log
    ip_address = request.client.host if request.client else None
    await audit.log_login(
        admin_id=admin.id,
        ip_address=ip_address,
        user_agent=request.headers.get("User-Agent"),
        success=True
    )
    
    access_token = create_access_token({"sub": str(admin.id), "role": admin.role.value})
    refresh_token = create_refresh_token({"sub": str(admin.id)})
    
    logger.info(f"Admin logged in (no 2FA): {admin.username}")
    
    # Create response with httpOnly cookies
    response = JSONResponse(content={
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "admin": {
            "id": str(admin.id),
            "username": admin.username,
            "email": admin.email,
            "role": admin.role.value,
            "first_name": admin.first_name,
            "last_name": admin.last_name,
        }
    })
    
    # Set httpOnly cookies
    set_auth_cookies(response, access_token, refresh_token)
    
    return response


@router.post("/verify-2fa")
@limiter.limit("10/minute")
async def verify_2fa(
    request: Request,
    data: Verify2FARequest,
    db: AsyncSession = Depends(get_db)
):
    """Verify 2FA code and complete login"""
    # Check session token (Redis-based)
    session = await get_2fa_session(data.session_token)
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired session"
        )
    
    admin_id = session["admin_id"]
    
    # Verify 2FA code
    if not await verify_2fa_code(db, admin_id, data.code):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired code"
        )
    
    # Clean up session (Redis-based)
    await delete_2fa_session(data.session_token)
    
    # Get admin
    admin = await db.get(AdminUser, admin_id)
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admin not found"
        )
    
    # Complete login
    admin.failed_login_attempts = 0
    admin.last_login_at = datetime.utcnow()
    await db.commit()
    
    # Audit log
    ip_address = request.client.host if request.client else None
    await audit.log_login(
        admin_id=admin.id,
        ip_address=ip_address,
        user_agent=request.headers.get("User-Agent"),
        success=True
    )
    await audit.log_2fa_verified(admin_id=admin.id, ip_address=ip_address)
    
    access_token = create_access_token({"sub": str(admin.id), "role": admin.role.value})
    refresh_token = create_refresh_token({"sub": str(admin.id)})
    
    logger.info(f"Admin logged in with 2FA: {admin.username}")
    
    # Create response with httpOnly cookies
    response = JSONResponse(content={
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "admin": {
            "id": str(admin.id),
            "username": admin.username,
            "email": admin.email,
            "role": admin.role.value,
            "first_name": admin.first_name,
            "last_name": admin.last_name,
        }
    })
    
    # Set httpOnly cookies
    set_auth_cookies(response, access_token, refresh_token)
    
    return response


@router.post("/resend-2fa")
@limiter.limit("3/minute")
async def resend_2fa(
    request: Request,
    data: dict,
    db: AsyncSession = Depends(get_db)
):
    """Resend 2FA code"""
    session_token = data.get("session_token")
    session = await get_2fa_session(session_token)
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid session"
        )
    
    admin_id = session["admin_id"]
    admin = await db.get(AdminUser, admin_id)
    
    if not admin or not admin.telegram_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot resend code"
        )
    
    # Generate new code
    ip_address = request.client.host if request.client else None
    code = await generate_2fa_code(db, str(admin.id), ip_address)
    
    # Send via Telegram
    message = f"""🔐 <b>Новый код подтверждения</b>

Ваш код: <code>{code}</code>

⏱ Действителен 5 минут"""
    
    await send_telegram_message(admin.telegram_id, message)
    
    return {"message": "Новый код отправлен"}


class RefreshFromCookieRequest(BaseModel):
    """Request for refresh from cookie (optional body)"""
    refresh_token: Optional[str] = None


@router.post("/refresh", response_model=dict)
@limiter.limit("30/minute")
async def refresh_token(
    request: Request,
    body: Optional[RefreshFromCookieRequest] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Refresh access token.
    
    Supports both:
    - httpOnly cookie (preferred)
    - Request body with refresh_token (backward compatibility)
    """
    # Try to get refresh token from cookie first
    token = request.cookies.get(COOKIE_REFRESH_NAME)
    
    # Fallback to body if no cookie
    if not token and body:
        token = body.refresh_token
    
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token required"
        )
    
    payload = decode_token(token)
    
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    admin_id = payload.get("sub")
    admin = await db.get(AdminUser, admin_id)
    
    if not admin or not admin.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin not found or inactive"
        )
    
    access_token = create_access_token({"sub": str(admin.id), "role": admin.role.value})
    
    # Return new token with cookie
    response = JSONResponse(content={
        "access_token": access_token,
        "token_type": "bearer"
    })
    
    # Update access token cookie
    response.set_cookie(
        key=COOKIE_NAME,
        value=access_token,
        max_age=settings.jwt_access_token_expire_minutes * 60,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        domain=COOKIE_DOMAIN,
        path="/",
    )
    
    return response


@router.post("/logout")
async def logout(request: Request, admin: AdminUser = Depends(get_current_admin)):
    """Logout and clear cookies"""
    # Audit log
    ip_address = request.client.host if request.client else None
    await audit.log_logout(admin_id=admin.id, ip_address=ip_address)
    
    response = JSONResponse(content={"message": "Logged out successfully"})
    clear_auth_cookies(response)
    return response


@router.get("/me")
async def get_current_admin_info(
    admin: AdminUser = Depends(get_current_admin)
):
    """Get current admin info"""
    return {
        "id": str(admin.id),
        "username": admin.username,
        "email": admin.email,
        "role": admin.role.value,
        "first_name": admin.first_name,
        "last_name": admin.last_name,
        "last_login_at": admin.last_login_at,
        "twofa_enabled": getattr(admin, 'twofa_enabled', True),
    }
