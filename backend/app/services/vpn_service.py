"""
VPN Service - VPN provisioning and management
"""
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models import (
    VPNAccount, VPNAccountStatus, VPNProtocol,
    Subscription, Server
)
from app.services.server_orchestrator import ServerOrchestrator
from app.core.logging import logger
from app.core.security import encrypt_data, decrypt_data


class VPNService:
    """VPN provisioning service"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.orchestrator = ServerOrchestrator(db)
    
    async def provision_access(
        self,
        subscription_id: str,
        protocol: VPNProtocol,
        region: Optional[str] = None,
    ) -> VPNAccount:
        """
        Provision VPN access for subscription
        
        Args:
            subscription_id: Subscription UUID
            protocol: VPN protocol
            region: Preferred region
        
        Returns:
            VPN account with config
        """
        subscription = await self.db.get(Subscription, subscription_id)
        
        if not subscription:
            raise ValueError("Subscription not found")
        
        # Select server
        server = await self.orchestrator.select_server(region=region, protocol=protocol.value)
        
        if not server:
            raise ValueError(f"No available servers in region {region}")
        
        # Get VPN provider
        provider = self._get_provider(protocol, server)
        
        # Create VPN account on server
        try:
            config_data = await provider.create_user(
                username=f"user_{subscription.user_id}_{subscription.id}"
            )
            
            # Encrypt sensitive data
            encrypted_config = encrypt_data(config_data["config"])
            encrypted_private_key = encrypt_data(config_data.get("private_key", "")) if config_data.get("private_key") else None
            
            # Create VPN account
            vpn_account = VPNAccount(
                subscription_id=subscription_id,
                server_id=server.id,
                protocol=protocol,
                username=config_data.get("username"),
                config=encrypted_config,
                public_key=config_data.get("public_key"),
                private_key=encrypted_private_key,
                ip_address=config_data.get("ip_address"),
                status=VPNAccountStatus.ACTIVE,
            )
            
            self.db.add(vpn_account)
            
            # Update subscription with server
            subscription.server_id = server.id
            
            # Increment server load
            await self.orchestrator.increment_server_load(server.id)
            
            await self.db.commit()
            await self.db.refresh(vpn_account)
            
            logger.info(
                f"VPN access provisioned: subscription_id={subscription_id}, "
                f"protocol={protocol}, server={server.name}"
            )
            
            return vpn_account
            
        except Exception as e:
            logger.error(f"VPN provisioning failed: {e}")
            raise
    
    async def revoke_access(self, vpn_account_id: str) -> None:
        """Revoke VPN access"""
        from sqlalchemy.orm import selectinload
        
        # Load vpn_account with server
        result = await self.db.execute(
            select(VPNAccount)
            .options(selectinload(VPNAccount.server))
            .where(VPNAccount.id == vpn_account_id)
        )
        vpn_account = result.scalar_one_or_none()
        
        if not vpn_account:
            return
        
        try:
            # Use XrayService for VLESS protocol
            if vpn_account.protocol in (VPNProtocol.VLESS, VPNProtocol.VLESS_REALITY):
                from app.services.xray_service import XrayService
                xray_service = XrayService(self.db)
                await xray_service.revoke_account(str(vpn_account.id))
                
                # Decrement server load for VLESS too
                server = vpn_account.server
                if server:
                    await self.orchestrator.decrement_server_load(server.id)
                
                vpn_account.status = VPNAccountStatus.REVOKED
                await self.db.commit()
            else:
                # Use provider for other protocols
                server = vpn_account.server
                provider = self._get_provider(vpn_account.protocol, server)
                await provider.delete_user(vpn_account.username)
                
                # Update account status
                vpn_account.status = VPNAccountStatus.REVOKED
                
                # Decrement server load
                if server:
                    await self.orchestrator.decrement_server_load(server.id)
                
                await self.db.commit()
            
            logger.info(f"VPN access revoked: account_id={vpn_account_id}")
            
        except Exception as e:
            logger.error(f"VPN revocation failed: {e}")
            raise
    
    async def get_config(self, vpn_account_id: str) -> str:
        """Get decrypted VPN config"""
        vpn_account = await self.db.get(VPNAccount, vpn_account_id)
        
        if not vpn_account:
            raise ValueError("VPN account not found")
        
        # Decrypt config
        return decrypt_data(vpn_account.config)
    
    async def rotate_keys(self, vpn_account_id: str) -> VPNAccount:
        """Rotate VPN keys"""
        vpn_account = await self.db.get(VPNAccount, vpn_account_id)
        
        if not vpn_account:
            raise ValueError("VPN account not found")
        
        server = vpn_account.server
        provider = self._get_provider(vpn_account.protocol, server)
        
        try:
            # Rotate keys on server
            new_config = await provider.rotate_keys(vpn_account.username)
            
            # Update account
            vpn_account.config = encrypt_data(new_config["config"])
            
            if new_config.get("public_key"):
                vpn_account.public_key = new_config["public_key"]
            
            if new_config.get("private_key"):
                vpn_account.private_key = encrypt_data(new_config["private_key"])
            
            await self.db.commit()
            
            logger.info(f"VPN keys rotated: account_id={vpn_account_id}")
            
            return vpn_account
            
        except Exception as e:
            logger.error(f"Key rotation failed: {e}")
            raise
    
    def _get_provider(self, protocol: VPNProtocol, server: Server):
        """Get VPN provider instance"""
        if protocol == VPNProtocol.WIREGUARD:
            from app.integrations.vpn.wireguard import WireGuardProvider
            return WireGuardProvider(server)
        
        elif protocol == VPNProtocol.OPENVPN:
            from app.integrations.vpn.openvpn import OpenVPNProvider
            return OpenVPNProvider(server)
        
        elif protocol == VPNProtocol.AMNEZIA:
            from app.integrations.vpn.amnezia import AmneziaProvider
            return AmneziaProvider(server)
        
        elif protocol in (VPNProtocol.VLESS_REALITY, VPNProtocol.VLESS):
            from app.integrations.vpn.vless_reality import VlessRealityProvider
            return VlessRealityProvider(server)
        
        else:
            raise ValueError(f"Unsupported protocol: {protocol}")
