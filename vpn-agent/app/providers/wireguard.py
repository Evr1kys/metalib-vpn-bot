"""
WireGuard VPN Provider
"""
import os
import subprocess
from typing import Dict, Optional
from pathlib import Path

from app.config import settings
from loguru import logger


class WireGuardManager:
    """WireGuard VPN management"""
    
    def __init__(self):
        self.config_dir = Path(settings.wg_config_dir)
        self.interface = settings.wg_interface
        self.server_ip = settings.wg_server_ip
        self.subnet = settings.wg_subnet
        self.port = settings.wg_port
        
        # Ensure config directory exists
        self.config_dir.mkdir(parents=True, exist_ok=True)
    
    async def create_user(self, username: str) -> Dict[str, str]:
        """
        Create WireGuard user
        
        Args:
            username: Unique username
        
        Returns:
            Dict with config file content and public key
        """
        try:
            # Generate keys
            private_key = self._generate_private_key()
            public_key = self._get_public_key(private_key)
            
            # Get next available IP
            client_ip = await self._get_next_ip()
            
            # Create client config
            config = self._generate_client_config(
                private_key=private_key,
                client_ip=client_ip
            )
            
            # Save client config
            config_file = self.config_dir / f"{username}.conf"
            config_file.write_text(config)
            
            # Add peer to server config
            await self._add_peer(public_key, client_ip)
            
            # Reload WireGuard
            await self._reload_interface()
            
            logger.info(f"WireGuard user created: {username}")
            
            return {
                "config": config,
                "public_key": public_key,
                "client_ip": client_ip
            }
        
        except Exception as e:
            logger.error(f"Failed to create WireGuard user {username}: {e}")
            raise
    
    async def delete_user(self, username: str, public_key: Optional[str] = None) -> bool:
        """
        Delete WireGuard user
        
        Args:
            username: Username to delete
            public_key: Optional public key to remove from interface
        
        Returns:
            True if successful
        """
        try:
            # Remove config file
            config_file = self.config_dir / f"{username}.conf"
            if config_file.exists():
                config_file.unlink()
            
            # Remove peer from interface
            if public_key:
                await self._remove_peer(public_key)
            
            logger.info(f"WireGuard user deleted: {username}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to delete WireGuard user {username}: {e}")
            raise
    
    async def rotate_keys(self, username: str) -> Dict[str, str]:
        """
        Rotate user keys
        
        Args:
            username: Username
        
        Returns:
            New config and keys
        """
        # Delete old user
        await self.delete_user(username)
        
        # Create new user with same name
        return await self.create_user(username)
    
    def _generate_private_key(self) -> str:
        """Generate WireGuard private key"""
        result = subprocess.run(
            ["wg", "genkey"],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    
    def _get_public_key(self, private_key: str) -> str:
        """Get public key from private key"""
        result = subprocess.run(
            ["wg", "pubkey"],
            input=private_key,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    
    async def _get_next_ip(self) -> str:
        """Get next available IP address in subnet"""
        # Get existing IPs from interface
        result = subprocess.run(
            ["wg", "show", self.interface, "allowed-ips"],
            capture_output=True,
            text=True
        )
        
        # Parse existing IPs
        used_ips = set()
        if result.returncode == 0:
            for line in result.stdout.strip().split('\n'):
                if line:
                    parts = line.split('\t')
                    if len(parts) >= 2:
                        ip = parts[1].split('/')[0]
                        used_ips.add(ip)
        
        # Find next available IP
        base_ip = self.server_ip.rsplit('.', 1)[0]
        for i in range(2, 255):
            ip = f"{base_ip}.{i}"
            if ip not in used_ips:
                return ip
        
        raise Exception("No available IPs in subnet")
    
    def _generate_client_config(self, private_key: str, client_ip: str) -> str:
        """Generate client configuration file"""
        # Get server public key
        server_config = self.config_dir / f"{self.interface}.conf"
        if server_config.exists():
            content = server_config.read_text()
            for line in content.split('\n'):
                if line.startswith('PrivateKey'):
                    server_private_key = line.split('=')[1].strip()
                    server_public_key = self._get_public_key(server_private_key)
                    break
        else:
            raise Exception("Server config not found")
        
        # Get server endpoint (public IP)
        # This should be configured or detected
        server_endpoint = os.getenv('WG_SERVER_ENDPOINT', 'SERVER_IP')
        
        config = f"""[Interface]
PrivateKey = {private_key}
Address = {client_ip}/32
DNS = 1.1.1.1, 8.8.8.8

[Peer]
PublicKey = {server_public_key}
Endpoint = {server_endpoint}:{self.port}
AllowedIPs = 0.0.0.0/0
PersistentKeepalive = 25
"""
        return config
    
    async def _add_peer(self, public_key: str, allowed_ip: str):
        """Add peer to WireGuard interface"""
        subprocess.run(
            [
                "wg", "set", self.interface,
                "peer", public_key,
                "allowed-ips", f"{allowed_ip}/32"
            ],
            check=True
        )
    
    async def _remove_peer(self, public_key: str):
        """Remove peer from WireGuard interface"""
        subprocess.run(
            ["wg", "set", self.interface, "peer", public_key, "remove"],
            check=False  # Don't fail if peer doesn't exist
        )
    
    async def _reload_interface(self):
        """Reload WireGuard interface"""
        subprocess.run(
            ["wg", "syncconf", self.interface, f"{self.config_dir}/{self.interface}.conf"],
            check=False
        )
