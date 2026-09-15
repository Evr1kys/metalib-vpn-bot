"""
OpenVPN Provider
"""
from typing import Dict, Any
from app.integrations.vpn.interface import VPNProviderInterface
from app.integrations.vpn.agent_client import AgentClient
from app.models import ManagementType
from app.core.logging import logger


class OpenVPNProvider(VPNProviderInterface):
    """OpenVPN provider"""
    
    async def create_user(self, username: str) -> Dict[str, Any]:
        """Create OpenVPN user"""
        logger.info(f"Creating OpenVPN user: {username} on server {self.server.name}")
        
        if self.server.management_type == ManagementType.AGENT:
            agent = AgentClient(self.server.agent_url, self.server.agent_token)
            
            try:
                response = await agent.create_openvpn_user(username, str(self.server.id))
                
                return {
                    "username": username,
                    "config": response["config"],  # .ovpn file content
                }
            finally:
                await agent.close()
        
        elif self.server.management_type == ManagementType.SSH:
            return await self._create_user_via_ssh(username)
        
        raise ValueError(f"Unsupported management type: {self.server.management_type}")
    
    async def delete_user(self, username: str) -> None:
        """Delete OpenVPN user"""
        logger.info(f"Deleting OpenVPN user: {username}")
        
        if self.server.management_type == ManagementType.AGENT:
            agent = AgentClient(self.server.agent_url, self.server.agent_token)
            
            try:
                await agent.delete_openvpn_user(username, str(self.server.id))
            finally:
                await agent.close()
        
        elif self.server.management_type == ManagementType.SSH:
            await self._delete_user_via_ssh(username)
    
    async def get_config(self, username: str) -> str:
        """Get OpenVPN config"""
        # Config stored in DB
        raise NotImplementedError("Use stored config from database")
    
    async def rotate_keys(self, username: str) -> Dict[str, Any]:
        """Rotate OpenVPN certificates"""
        logger.info(f"Rotating OpenVPN certificates: {username}")
        
        # Regenerate certificates
        await self.delete_user(username)
        return await self.create_user(username)
    
    async def get_stats(self, username: str) -> Dict[str, Any]:
        """Get OpenVPN user stats"""
        if self.server.management_type == ManagementType.AGENT:
            agent = AgentClient(self.server.agent_url, self.server.agent_token)
            
            try:
                return await agent.get_user_stats(username, "openvpn", str(self.server.id))
            finally:
                await agent.close()
        
        return {"bytes_sent": 0, "bytes_received": 0}
    
    async def _create_user_via_ssh(self, username: str) -> Dict[str, Any]:
        """Create user via SSH"""
        raise NotImplementedError("SSH-based OpenVPN provisioning not implemented")
    
    async def _delete_user_via_ssh(self, username: str) -> None:
        """Delete user via SSH"""
        raise NotImplementedError("SSH-based OpenVPN deletion not implemented")
