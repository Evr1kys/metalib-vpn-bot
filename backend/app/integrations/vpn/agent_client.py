"""
VPN Agent Client - for communication with VPN server agents
"""
from typing import Dict, Any, Optional
import httpx
from app.core.config import settings
from app.core.security import create_agent_signature, decrypt_data
from app.core.logging import logger
from datetime import datetime


class AgentClient:
    """Client for VPN server agent API"""
    
    def __init__(self, url: str, token: str):
        self.url = url.rstrip("/")
        self.token = decrypt_data(token) if token else ""
        
        self.client = httpx.AsyncClient(
            base_url=self.url,
            timeout=30.0,
        )
    
    def _get_auth_headers(self, server_id: str) -> Dict[str, str]:
        """Get authentication headers"""
        timestamp = str(int(datetime.utcnow().timestamp()))
        signature = create_agent_signature(server_id, timestamp, self.token)
        
        return {
            "X-Server-ID": server_id,
            "X-Timestamp": timestamp,
            "X-Signature": signature,
            "Authorization": f"Bearer {self.token}",
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Check agent health"""
        try:
            response = await self.client.get("/health")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Agent health check failed: {e}")
            return {"status": "error", "message": str(e)}
    
    async def create_wireguard_user(
        self,
        username: str,
        server_id: str,
    ) -> Dict[str, Any]:
        """Create WireGuard user"""
        payload = {"username": username}
        headers = self._get_auth_headers(server_id)
        
        response = await self.client.post(
            "/vpn/wireguard/users",
            json=payload,
            headers=headers
        )
        response.raise_for_status()
        
        return response.json()
    
    async def delete_wireguard_user(
        self,
        username: str,
        server_id: str,
    ) -> None:
        """Delete WireGuard user"""
        headers = self._get_auth_headers(server_id)
        
        response = await self.client.delete(
            f"/vpn/wireguard/users/{username}",
            headers=headers
        )
        response.raise_for_status()
    
    async def create_openvpn_user(
        self,
        username: str,
        server_id: str,
    ) -> Dict[str, Any]:
        """Create OpenVPN user"""
        payload = {"username": username}
        headers = self._get_auth_headers(server_id)
        
        response = await self.client.post(
            "/vpn/openvpn/users",
            json=payload,
            headers=headers
        )
        response.raise_for_status()
        
        return response.json()
    
    async def delete_openvpn_user(
        self,
        username: str,
        server_id: str,
    ) -> None:
        """Delete OpenVPN user"""
        headers = self._get_auth_headers(server_id)
        
        response = await self.client.delete(
            f"/vpn/openvpn/users/{username}",
            headers=headers
        )
        response.raise_for_status()
    
    async def create_amnezia_user(
        self,
        username: str,
        server_id: str,
    ) -> Dict[str, Any]:
        """Create Amnezia user"""
        payload = {"username": username}
        headers = self._get_auth_headers(server_id)
        
        response = await self.client.post(
            "/vpn/amnezia/users",
            json=payload,
            headers=headers
        )
        response.raise_for_status()
        
        return response.json()
    
    async def delete_amnezia_user(
        self,
        username: str,
        server_id: str,
    ) -> None:
        """Delete Amnezia user"""
        headers = self._get_auth_headers(server_id)
        
        response = await self.client.delete(
            f"/vpn/amnezia/users/{username}",
            headers=headers
        )
        response.raise_for_status()
    
    async def create_user(
        self,
        username: str,
        protocol: str,
        server_id: str,
    ) -> Dict[str, Any]:
        """Create VPN user (generic method)"""
        payload = {
            "username": username,
            "protocol": protocol
        }
        headers = self._get_auth_headers(server_id)
        
        # Get request body bytes for signature
        import json
        body = json.dumps(payload)
        
        # Create signature
        timestamp = headers["X-Timestamp"]
        signature = create_agent_signature(body, timestamp, self.token)
        headers["X-Signature"] = signature
        
        response = await self.client.post(
            "/users/create",
            json=payload,
            headers=headers
        )
        response.raise_for_status()
        
        return response.json()
    
    async def delete_user(
        self,
        username: str,
        protocol: str,
        server_id: str,
    ) -> None:
        """Delete VPN user (generic method)"""
        payload = {
            "username": username,
            "protocol": protocol
        }
        headers = self._get_auth_headers(server_id)
        
        # Get request body bytes for signature
        import json
        body = json.dumps(payload)
        
        # Create signature
        timestamp = headers["X-Timestamp"]
        signature = create_agent_signature(body, timestamp, self.token)
        headers["X-Signature"] = signature
        
        response = await self.client.post(
            "/users/delete",
            json=payload,
            headers=headers
        )
        response.raise_for_status()
    
    async def get_user_stats(
        self,
        username: str,
        protocol: str,
        server_id: str,
    ) -> Dict[str, Any]:
        """Get user statistics"""
        headers = self._get_auth_headers(server_id)
        
        response = await self.client.get(
            f"/vpn/{protocol}/users/{username}/stats",
            headers=headers
        )
        response.raise_for_status()
        
        return response.json()
    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()
