"""
VPN Provider Interface
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from app.models import Server


class VPNProviderInterface(ABC):
    """Abstract interface for VPN providers"""
    
    def __init__(self, server: Server):
        self.server = server
    
    @abstractmethod
    async def create_user(self, username: str) -> Dict[str, Any]:
        """
        Create VPN user/config
        
        Args:
            username: Unique username
        
        Returns:
            Config data:
            {
                "username": str,
                "config": str,  # Full config file content
                "public_key": str (optional),
                "private_key": str (optional),
                "ip_address": str (optional),
            }
        """
        pass
    
    @abstractmethod
    async def delete_user(self, username: str) -> None:
        """Delete VPN user"""
        pass
    
    @abstractmethod
    async def get_config(self, username: str) -> str:
        """Get VPN config for user"""
        pass
    
    @abstractmethod
    async def rotate_keys(self, username: str) -> Dict[str, Any]:
        """Rotate user keys/credentials"""
        pass
    
    @abstractmethod
    async def get_stats(self, username: str) -> Dict[str, Any]:
        """
        Get user usage stats
        
        Returns:
            {
                "bytes_sent": int,
                "bytes_received": int,
                "last_handshake": datetime (optional),
            }
        """
        pass
