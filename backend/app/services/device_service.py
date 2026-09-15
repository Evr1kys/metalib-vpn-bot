"""
Device Service - device binding and management
"""
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.models import Device, Subscription, VPNAccount
from app.core.security import generate_device_binding_token
from app.core.config import settings
from app.core.logging import logger


class DeviceService:
    """Device management service"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def generate_binding_token(self, subscription_id: str) -> Dict[str, Any]:
        """
        Generate device binding token
        
        Args:
            subscription_id: Subscription UUID
        
        Returns:
            Token data with token and expiry
        """
        subscription = await self.db.get(Subscription, subscription_id)
        
        if not subscription:
            raise ValueError("Subscription not found")
        
        # Check device limit
        if not await self.check_device_limit(subscription_id):
            raise ValueError("Device limit reached")
        
        # Generate unique token
        token = generate_device_binding_token()
        expires_at = datetime.utcnow() + timedelta(
            minutes=settings.device_binding_token_expiry_minutes
        )
        
        # Create device with pending token
        device = Device(
            subscription_id=subscription_id,
            user_id=subscription.user_id,
            device_token=token,
            is_active=False,
            is_token_used=False,
            token_expires_at=expires_at,
        )
        
        self.db.add(device)
        await self.db.commit()
        
        logger.info(f"Device binding token generated: subscription_id={subscription_id}, token={token}")
        
        return {
            "token": token,
            "expires_at": expires_at,
            "expires_in_seconds": settings.device_binding_token_expiry_minutes * 60,
        }
    
    async def bind_device(
        self,
        token: str,
        device_info: Dict[str, Any],
        vpn_account_id: Optional[str] = None,
    ) -> Device:
        """
        Bind device using token
        
        Args:
            token: Binding token
            device_info: Device information (name, type, model, etc.)
            vpn_account_id: VPN account to bind to (optional)
        
        Returns:
            Bound device
        """
        # Find device by token
        stmt = select(Device).where(Device.device_token == token)
        result = await self.db.execute(stmt)
        device = result.scalar_one_or_none()
        
        if not device:
            raise ValueError("Invalid token")
        
        if not device.is_token_valid():
            raise ValueError("Token expired or already used")
        
        # Update device info
        device.device_name = device_info.get("name")
        device.device_type = device_info.get("type")
        device.device_model = device_info.get("model")
        device.os_version = device_info.get("os_version")
        device.device_fingerprint = device_info.get("fingerprint")
        device.vpn_account_id = vpn_account_id
        device.is_active = True
        device.is_token_used = True
        device.last_used_at = datetime.utcnow()
        
        await self.db.commit()
        
        logger.info(f"Device bound: id={device.id}, name={device.device_name}, type={device.device_type}")
        
        return device
    
    async def unbind_device(self, device_id: str) -> None:
        """Unbind/remove device"""
        device = await self.db.get(Device, device_id)
        
        if not device:
            raise ValueError("Device not found")
        
        device.is_active = False
        await self.db.commit()
        
        logger.info(f"Device unbound: id={device_id}")
    
    async def check_device_limit(self, subscription_id: str) -> bool:
        """
        Check if subscription can add more devices
        
        Args:
            subscription_id: Subscription UUID
        
        Returns:
            True if can add more devices
        """
        subscription = await self.db.get(Subscription, subscription_id)
        
        if not subscription:
            return False
        
        plan = subscription.plan
        
        # Count active devices
        stmt = select(Device).where(
            and_(
                Device.subscription_id == subscription_id,
                Device.is_active == True,
            )
        )
        result = await self.db.execute(stmt)
        active_devices = len(result.scalars().all())
        
        return active_devices < plan.max_devices
    
    async def get_devices(self, subscription_id: str) -> List[Device]:
        """Get all devices for subscription"""
        stmt = select(Device).where(
            and_(
                Device.subscription_id == subscription_id,
                Device.is_active == True,
            )
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
    
    async def update_device_usage(
        self,
        device_id: str,
        ip_address: Optional[str] = None,
    ) -> None:
        """Update device last used timestamp"""
        device = await self.db.get(Device, device_id)
        
        if device:
            device.last_used_at = datetime.utcnow()
            device.connection_count += 1
            
            if ip_address:
                device.last_ip = ip_address
            
            await self.db.commit()
