"""
Devices endpoints
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.core.database import get_db
from app.services.device_service import DeviceService
from app.api.deps import verify_bot_token

router = APIRouter()


class DeviceTokenResponse(BaseModel):
    """Device token response"""
    token: str
    expires_in_seconds: int


class DeviceBindRequest(BaseModel):
    """Device bind request"""
    token: str
    device_name: str | None = None
    device_type: str | None = None
    device_model: str | None = None
    os_version: str | None = None
    fingerprint: str | None = None


class DeviceResponse(BaseModel):
    """Device response"""
    id: str
    device_name: str | None
    device_type: str | None
    is_active: bool
    last_used_at: str | None
    
    class Config:
        from_attributes = True


@router.post("/generate-token", response_model=DeviceTokenResponse, dependencies=[Depends(verify_bot_token)])
async def generate_device_token(
    subscription_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Generate device binding token"""
    device_service = DeviceService(db)
    
    try:
        token_data = await device_service.generate_binding_token(subscription_id)
        return DeviceTokenResponse(
            token=token_data["token"],
            expires_in_seconds=token_data["expires_in_seconds"],
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/bind", response_model=DeviceResponse, dependencies=[Depends(verify_bot_token)])
async def bind_device(
    bind_data: DeviceBindRequest,
    db: AsyncSession = Depends(get_db)
):
    """Bind device using token"""
    device_service = DeviceService(db)
    
    device_info = {
        "name": bind_data.device_name,
        "type": bind_data.device_type,
        "model": bind_data.device_model,
        "os_version": bind_data.os_version,
        "fingerprint": bind_data.fingerprint,
    }
    
    try:
        device = await device_service.bind_device(bind_data.token, device_info)
        
        return DeviceResponse(
            id=str(device.id),
            device_name=device.device_name,
            device_type=device.device_type,
            is_active=device.is_active,
            last_used_at=device.last_used_at.isoformat() if device.last_used_at else None,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/subscription/{subscription_id}", response_model=List[DeviceResponse], dependencies=[Depends(verify_bot_token)])
async def get_devices(
    subscription_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get subscription devices"""
    device_service = DeviceService(db)
    devices = await device_service.get_devices(subscription_id)
    
    return [
        DeviceResponse(
            id=str(device.id),
            device_name=device.device_name,
            device_type=device.device_type,
            is_active=device.is_active,
            last_used_at=device.last_used_at.isoformat() if device.last_used_at else None,
        )
        for device in devices
    ]


@router.delete("/{device_id}", dependencies=[Depends(verify_bot_token)])
async def unbind_device(
    device_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Unbind device"""
    device_service = DeviceService(db)
    
    try:
        await device_service.unbind_device(device_id)
        return {"status": "ok", "message": "Device unbound"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
