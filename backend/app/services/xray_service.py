"""
Xray VPN Service - VLESS/Reality management with gRPC API
"""
import json
import uuid
import asyncio
import aiohttp
from typing import Dict, Optional, List
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.logging import logger
from app.models import VPNAccount, Subscription, Server


class XrayService:
    """Xray-core management service for VLESS using Xray API"""
    
    # VLESS configuration (без Reality - проще и надежнее)
    DEFAULT_PORT = 10443  # Xray VLESS port
    XRAY_API_PORT = 8444  # Xray HTTP API port
    
    # Legacy Reality config - NOT USED in current implementation
    # Kept for reference only, keys were for testing/migration
    # In production, never hardcode cryptographic keys!
    _LEGACY_REALITY_SNI = "www.ozon.ru"
    
    def __init__(self, db: AsyncSession, host_mode: bool = False):
        self.db = db
        self.host_mode = host_mode
    
    async def generate_vless_account(
        self,
        subscription_id: str,
        server_id: str,
        email: Optional[str] = None
    ) -> VPNAccount:
        """
        Generate VLESS account and add to Xray config via VPN Agent
        
        Args:
            subscription_id: Subscription UUID
            server_id: Server UUID
            email: Optional email identifier
        
        Returns:
            Created VPNAccount with config
        """
        from app.models.vpn_account import VPNProtocol, VPNAccountStatus
        
        subscription = await self.db.get(Subscription, subscription_id)
        server = await self.db.get(Server, server_id)
        
        if not subscription or not server:
            raise ValueError("Subscription or Server not found")
        
        client_email = email or f"user_{subscription.user_id}"
        server_ip = str(server.ip_address) if hasattr(server, 'ip_address') else str(server.ip)
        
        # Add client to Xray via VPN Agent - agent generates UUID
        client_uuid = await self._add_client_to_xray(
            server_ip=server_ip,
            client_email=client_email
        )
        
        if not client_uuid:
            raise ValueError("Failed to add client to Xray server")
        
        # Generate VLESS:// connection string
        # Простое название: локация сервера или просто MetaLib
        server_location = getattr(server, 'location', None) or getattr(server, 'country', None) or server.name
        alias = f"MetaLib {server_location}"
        
        vless_config = self._generate_vless_uri(
            server_ip=server_ip,
            server_port=self.DEFAULT_PORT,
            client_uuid=client_uuid,
            alias=alias
        )
        
        # Create VPN account record
        vpn_account = VPNAccount(
            subscription_id=subscription_id,
            server_id=server_id,
            protocol=VPNProtocol.VLESS,
            username=client_email,
            config=json.dumps({"connection_string": vless_config}),
            public_key=client_uuid,
            status=VPNAccountStatus.ACTIVE,
            bandwidth_used=0,
            connection_count=0
        )
        
        self.db.add(vpn_account)
        
        # Increment server load counter
        server.current_users = (server.current_users or 0) + 1
        
        await self.db.commit()
        await self.db.refresh(vpn_account)
        
        logger.info(f"VLESS account created: uuid={client_uuid}, email={client_email}, subscription_id={subscription_id}")
        
        return vpn_account
    
    async def _add_client_to_xray(
        self,
        server_ip: str,
        client_email: str
    ) -> Optional[str]:
        """
        Add client to Xray via HTTP API on VPN server
        
        Args:
            server_ip: Server IP address
            client_email: Client email/identifier
        
        Returns:
            Client UUID if successful, None otherwise
        """
        import hmac
        import hashlib
        from app.core.config import settings
        
        API_SECRET = settings.VPN_AGENT_SECRET_KEY or "metalib-xray-secret-key-2024"
        API_PORT = 8444
        
        try:
            payload = json.dumps({"email": client_email})
            signature = hmac.new(API_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"http://{server_ip}:{API_PORT}/add-client",
                    data=payload,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": signature
                    },
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as resp:
                    result = await resp.json()
                    if result.get("success"):
                        client_uuid = result.get("uuid")
                        logger.info(f"Client added to Xray via API: {client_email} -> {client_uuid}")
                        return client_uuid
                    else:
                        logger.error(f"Xray API error: {result.get('error')}")
                        return None
                        
        except Exception as e:
            logger.error(f"Error calling Xray API: {e}")
            return None
    
    def _generate_vless_uri(
        self,
        server_ip: str,
        server_port: int,
        client_uuid: str,
        alias: str
    ) -> str:
        """
        Generate VLESS:// URI for client import (without Reality - simpler setup)
        
        Format:
        vless://UUID@IP:PORT?type=tcp&security=none#ALIAS
        
        Args:
            server_ip: Server IP
            server_port: Server port (usually 443)
            client_uuid: Client UUID
            alias: Connection name
        
        Returns:
            VLESS URI string
        """
        from urllib.parse import quote
        
        uri = f"vless://{client_uuid}@{server_ip}:{server_port}"
        uri += f"?type=tcp"
        uri += f"&security=none"  # No TLS/Reality - проще в настройке
        uri += f"&encryption=none"
        uri += f"#{quote(alias)}"
        
        return uri
    
    async def revoke_account(self, vpn_account_id: str) -> bool:
        """
        Revoke VPN account - remove from Xray config via API
        
        Args:
            vpn_account_id: VPNAccount UUID
        
        Returns:
            Success status
        """
        import hmac
        import hashlib
        from app.core.config import settings
        from app.models.vpn_account import VPNAccountStatus
        
        vpn_account = await self.db.get(VPNAccount, vpn_account_id)
        if not vpn_account:
            return False
        
        server = await self.db.get(Server, vpn_account.server_id)
        client_uuid = vpn_account.public_key  # We stored UUID in public_key field
        
        API_SECRET = settings.VPN_AGENT_SECRET_KEY or "metalib-xray-secret-key-2024"
        API_PORT = 8444
        
        try:
            payload = json.dumps({"uuid": client_uuid})
            signature = hmac.new(API_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"http://{str(server.ip_address)}:{API_PORT}/remove-client",
                    data=payload,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": signature
                    },
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as resp:
                    result = await resp.json()
                    
            # Update account status
            vpn_account.status = VPNAccountStatus.REVOKED
            await self.db.commit()
            
            logger.info(f"VPN account revoked: {vpn_account_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error revoking account: {e}")
            return False
    
    async def get_server_clients(self, server_id: str) -> List[Dict]:
        """
        Get all clients from database for server
        
        Args:
            server_id: Server UUID
        
        Returns:
            List of client dicts
        """
        from sqlalchemy import select
        
        try:
            result = await self.db.execute(
                select(VPNAccount).where(VPNAccount.server_id == server_id)
            )
            accounts = result.scalars().all()
            
            return [
                {
                    "id": acc.public_key,
                    "email": acc.username,
                    "subscription_id": str(acc.subscription_id)
                }
                for acc in accounts
            ]
            
        except Exception as e:
            logger.error(f"Error getting server clients: {e}")
            return []

    async def get_traffic_stats(self, server_ip: str) -> Dict:
        """
        Get traffic statistics from Xray API
        
        Args:
            server_ip: Server IP address
        
        Returns:
            Traffic statistics dict
        """
        import hmac
        import hashlib
        from app.core.config import settings
        
        API_SECRET = settings.VPN_AGENT_SECRET_KEY or "metalib-xray-secret-key-2024"
        API_PORT = 8444
        
        try:
            payload = json.dumps({})
            signature = hmac.new(API_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"http://{server_ip}:{API_PORT}/stats",
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": signature
                    },
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as resp:
                    return await resp.json()
                    
        except Exception as e:
            logger.error(f"Error getting stats from Xray API: {e}")
            return {"error": str(e)}
