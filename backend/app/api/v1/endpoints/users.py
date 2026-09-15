"""
Users endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, Field
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.database import get_db
from app.models import User
from app.api.deps import verify_bot_token

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


class UserCreateRequest(BaseModel):
    """User creation request"""
    telegram_id: int
    username: str | None = Field(None, max_length=100)
    first_name: str | None = Field(None, max_length=100)
    last_name: str | None = Field(None, max_length=100)
    language_code: str = "ru"
    referrer_telegram_id: int | None = None


class UserResponse(BaseModel):
    """User response"""
    id: str
    telegram_id: int
    username: str | None
    first_name: str | None
    last_name: str | None
    is_blocked: bool
    is_banned: bool
    
    class Config:
        from_attributes = True


@router.post("/", response_model=UserResponse, dependencies=[Depends(verify_bot_token)])
@limiter.limit("30/minute")
async def create_or_get_user(
    request: Request,
    user_data: UserCreateRequest,
    db: AsyncSession = Depends(get_db)
):
    """Create or get existing user"""
    # Check if user exists
    stmt = select(User).where(User.telegram_id == user_data.telegram_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if user:
        # Update user data
        if user_data.username:
            user.username = user_data.username
        if user_data.first_name:
            user.first_name = user_data.first_name
        if user_data.last_name:
            user.last_name = user_data.last_name
        
        await db.commit()
        await db.refresh(user)
    else:
        # Create new user
        user = User(
            telegram_id=user_data.telegram_id,
            username=user_data.username,
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            language_code=user_data.language_code,
        )
        
        # Handle referrer
        if user_data.referrer_telegram_id:
            stmt = select(User).where(User.telegram_id == user_data.referrer_telegram_id)
            result = await db.execute(stmt)
            referrer = result.scalar_one_or_none()
            
            if referrer:
                user.referrer_id = referrer.id
        
        db.add(user)
        await db.commit()
        await db.refresh(user)
    
    return UserResponse(
        id=str(user.id),
        telegram_id=user.telegram_id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        is_blocked=user.is_blocked,
        is_banned=user.is_banned,
    )


@router.get("/{telegram_id}", response_model=UserResponse, dependencies=[Depends(verify_bot_token)])
@limiter.limit("60/minute")
async def get_user_by_telegram_id(
    request: Request,
    telegram_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get user by Telegram ID"""
    stmt = select(User).where(User.telegram_id == telegram_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return UserResponse(
        id=str(user.id),
        telegram_id=user.telegram_id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        is_blocked=user.is_blocked,
        is_banned=user.is_banned,
    )


@router.patch("/{telegram_id}/notifications", dependencies=[Depends(verify_bot_token)])
@limiter.limit("10/minute")
async def update_notification_settings(
    request: Request,
    telegram_id: int,
    disable_broadcasts: bool,
    db: AsyncSession = Depends(get_db)
):
    """Update user notification settings"""
    stmt = select(User).where(User.telegram_id == telegram_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.disable_broadcast_notifications = disable_broadcasts
    await db.commit()
    
    return {
        "success": True,
        "disable_broadcast_notifications": user.disable_broadcast_notifications
    }
