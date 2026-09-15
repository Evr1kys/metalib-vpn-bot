"""
VLESS+Reality Provider
"""
from typing import Dict, Any
from app.integrations.vpn.interface import VPNProviderInterface
from app.integrations.vpn.agent_client import AgentClient
from app.models import Server, ManagementType
from app.core.logging import logger


class VlessRealityProvider(VPNProviderInterface):
    """VLESS+Reality VPN provider"""
    
    async def create_user(self, username: str) -> Dict[str, Any]:
        """Create VLESS+Reality user"""
        logger.info(f"Creating VLESS+Reality user: {username} on server {self.server.name}")
        
        if self.server.management_type == ManagementType.AGENT:
            # Use agent API
            agent = AgentClient(self.server.agent_url, self.server.agent_token)
            
            try:
                response = await agent.create_user(username, "vless+reality", str(self.server.id))
                
                return {
                    "username": username,
                    "config": response["config"],
                    "user_id": response.get("user_id"),
                    "public_key": response.get("public_key"),
                    "short_id": response.get("short_id"),
                }
            finally:
                await agent.close()
        
        elif self.server.management_type == ManagementType.SSH:
            # Use SSH commands
            return await self._create_user_via_ssh(username)
        
        else:
            raise ValueError(f"Unsupported management type: {self.server.management_type}")
    
    async def delete_user(self, username: str) -> None:
        """Delete VLESS+Reality user"""
        logger.info(f"Deleting VLESS+Reality user: {username} on server {self.server.name}")
        
        if self.server.management_type == ManagementType.AGENT:
            agent = AgentClient(self.server.agent_url, self.server.agent_token)
            
            try:
                await agent.delete_user(username, "vless+reality", str(self.server.id))
            finally:
                await agent.close()
        
        elif self.server.management_type == ManagementType.SSH:
            await self._delete_user_via_ssh(username)
    
    async def get_config(self, username: str) -> str:
        """Get VLESS+Reality config"""
        # Config is stored in database, this is a fallback
        if self.server.management_type == ManagementType.AGENT:
            agent = AgentClient(self.server.agent_url, self.server.agent_token)
            
            try:
                response = await agent.create_user(username, "vless+reality", str(self.server.id))
                return response["config"]
            finally:
                await agent.close()
        
        raise NotImplementedError("Config retrieval via SSH not implemented")
    
    async def rotate_keys(self, username: str) -> Dict[str, Any]:
        """Rotate VLESS+Reality keys"""
        logger.info(f"Rotating VLESS+Reality keys: {username}")
        
        # For VLESS+Reality, we need to delete and recreate
        await self.delete_user(username)
        return await self.create_user(username)
    
    async def get_stats(self, username: str) -> Dict[str, Any]:
        """Get VLESS+Reality user stats"""
        if self.server.management_type == ManagementType.AGENT:
            agent = AgentClient(self.server.agent_url, self.server.agent_token)
            
            try:
                return await agent.get_user_stats(username, "vless+reality", str(self.server.id))
            finally:
                await agent.close()
        
        return {"bytes_sent": 0, "bytes_received": 0}
    
    async def _create_user_via_ssh(self, username: str) -> Dict[str, Any]:
        """Create user via SSH (fallback)"""
        raise NotImplementedError("SSH-based VLESS+Reality provisioning not implemented")
    
    async def _delete_user_via_ssh(self, username: str) -> None:
        """Delete user via SSH (fallback)"""
        raise NotImplementedError("SSH-based VLESS+Reality deletion not implemented")
