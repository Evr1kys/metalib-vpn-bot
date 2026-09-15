"""
Amnezia VPN Provider
"""
from typing import Dict, Any
from app.integrations.vpn.interface import VPNProviderInterface
from app.integrations.vpn.agent_client import AgentClient
from app.models import ManagementType
from app.core.logging import logger


class AmneziaProvider(VPNProviderInterface):
    """Amnezia VPN provider (based on WireGuard with obfuscation)"""
    
    async def create_user(self, username: str) -> Dict[str, Any]:
        """Create Amnezia user"""
        logger.info(f"Creating Amnezia user: {username} on server {self.server.name}")
        
        if self.server.management_type == ManagementType.AGENT:
            agent = AgentClient(self.server.agent_url, self.server.agent_token)
            
            try:
                response = await agent.create_amnezia_user(username, str(self.server.id))
                
                return {
                    "username": username,
                    "config": response["config"],  # Amnezia config
                    "public_key": response.get("public_key"),
                    "private_key": response.get("private_key"),
                    "ip_address": response.get("ip_address"),
                }
            finally:
                await agent.close()
        
        elif self.server.management_type == ManagementType.SSH:
            return await self._create_user_via_ssh(username)
        
        raise ValueError(f"Unsupported management type: {self.server.management_type}")
    
    async def delete_user(self, username: str) -> None:
        """Delete Amnezia user"""
        logger.info(f"Deleting Amnezia user: {username}")
        
        if self.server.management_type == ManagementType.AGENT:
            agent = AgentClient(self.server.agent_url, self.server.agent_token)
            
            try:
                await agent.delete_amnezia_user(username, str(self.server.id))
            finally:
                await agent.close()
        
        elif self.server.management_type == ManagementType.SSH:
            await self._delete_user_via_ssh(username)
    
    async def get_config(self, username: str) -> str:
        """Get Amnezia config"""
        raise NotImplementedError("Use stored config from database")
    
    async def rotate_keys(self, username: str) -> Dict[str, Any]:
        """Rotate Amnezia keys"""
        logger.info(f"Rotating Amnezia keys: {username}")
        
        await self.delete_user(username)
        return await self.create_user(username)
    
    async def get_stats(self, username: str) -> Dict[str, Any]:
        """Get Amnezia user stats"""
        if self.server.management_type == ManagementType.AGENT:
            agent = AgentClient(self.server.agent_url, self.server.agent_token)
            
            try:
                return await agent.get_user_stats(username, "amnezia", str(self.server.id))
            finally:
                await agent.close()
        
        return {"bytes_sent": 0, "bytes_received": 0}
    
    async def _create_user_via_ssh(self, username: str) -> Dict[str, Any]:
        """Create user via SSH"""
        raise NotImplementedError("SSH-based Amnezia provisioning not implemented")
    
    async def _delete_user_via_ssh(self, username: str) -> None:
        """Delete user via SSH"""
        raise NotImplementedError("SSH-based Amnezia deletion not implemented")
