"""
Amnezia VPN Provider (WireGuard with obfuscation)
"""
import subprocess
from typing import Dict
from pathlib import Path

from app.config import settings
from loguru import logger


class AmneziaManager:
    """Amnezia VPN management (AmneziaWG)"""
    
    def __init__(self):
        self.config_dir = Path(settings.amnezia_config_dir)
        self.interface = settings.amnezia_interface
        self.server_ip = settings.amnezia_server_ip
        self.subnet = settings.amnezia_subnet
        self.port = settings.amnezia_port
        
        # Ensure config directory exists
        self.config_dir.mkdir(parents=True, exist_ok=True)
    
    async def create_user(self, username: str) -> Dict[str, str]:
        """
        Create Amnezia user
        
        Args:
            username: Unique username
        
        Returns:
            Dict with config file content
        """
        try:
            # Generate keys (same as WireGuard)
            private_key = self._generate_private_key()
            public_key = self._get_public_key(private_key)
            
            # Get next available IP
            client_ip = await self._get_next_ip()
            
            # Generate obfuscation parameters
            junk_packet_count = 5  # Jc parameter
            junk_packet_min_size = 50  # Jmin parameter
            junk_packet_max_size = 100  # Jmax parameter
            init_packet_junk_size = 50  # S1 parameter
            response_packet_junk_size = 50  # S2 parameter
            init_packet_magic_header = 1234567890  # H1 parameter
            response_packet_magic_header = 9876543210  # H2 parameter
            
            # Create client config with obfuscation
            config = self._generate_client_config(
                private_key=private_key,
                client_ip=client_ip,
                jc=junk_packet_count,
                jmin=junk_packet_min_size,
                jmax=junk_packet_max_size,
                s1=init_packet_junk_size,
                s2=response_packet_junk_size,
                h1=init_packet_magic_header,
                h2=response_packet_magic_header
            )
            
            # Save client config
            config_file = self.config_dir / f"{username}.conf"
            config_file.write_text(config)
            
            # Add peer to server
            await self._add_peer(public_key, client_ip)
            
            # Reload interface
            await self._reload_interface()
            
            logger.info(f"Amnezia user created: {username}")
            
            return {
                "config": config,
                "public_key": public_key,
                "client_ip": client_ip
            }
        
        except Exception as e:
            logger.error(f"Failed to create Amnezia user {username}: {e}")
            raise
    
    async def delete_user(self, username: str, public_key: str = None) -> bool:
        """
        Delete Amnezia user
        
        Args:
            username: Username to delete
            public_key: Optional public key
        
        Returns:
            True if successful
        """
        try:
            # Remove config file
            config_file = self.config_dir / f"{username}.conf"
            if config_file.exists():
                config_file.unlink()
            
            # Remove peer
            if public_key:
                await self._remove_peer(public_key)
            
            logger.info(f"Amnezia user deleted: {username}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to delete Amnezia user {username}: {e}")
            raise
    
    async def rotate_keys(self, username: str) -> Dict[str, str]:
        """
        Rotate user keys
        
        Args:
            username: Username
        
        Returns:
            New config
        """
        await self.delete_user(username)
        return await self.create_user(username)
    
    def _generate_private_key(self) -> str:
        """Generate private key"""
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
        """Get next available IP"""
        # Similar to WireGuard implementation
        result = subprocess.run(
            ["wg", "show", self.interface, "allowed-ips"],
            capture_output=True,
            text=True
        )
        
        used_ips = set()
        if result.returncode == 0:
            for line in result.stdout.strip().split('\n'):
                if line:
                    parts = line.split('\t')
                    if len(parts) >= 2:
                        ip = parts[1].split('/')[0]
                        used_ips.add(ip)
        
        base_ip = self.server_ip.rsplit('.', 1)[0]
        for i in range(2, 255):
            ip = f"{base_ip}.{i}"
            if ip not in used_ips:
                return ip
        
        raise Exception("No available IPs")
    
    def _generate_client_config(
        self,
        private_key: str,
        client_ip: str,
        jc: int,
        jmin: int,
        jmax: int,
        s1: int,
        s2: int,
        h1: int,
        h2: int
    ) -> str:
        """Generate Amnezia client config with obfuscation parameters"""
        import os
        
        # Get server public key (would be pre-configured)
        server_public_key = os.getenv('AMNEZIA_SERVER_PUBLIC_KEY', 'SERVER_PUBLIC_KEY')
        server_endpoint = os.getenv('AMNEZIA_SERVER_ENDPOINT', 'SERVER_IP')
        
        config = f"""[Interface]
PrivateKey = {private_key}
Address = {client_ip}/32
DNS = 1.1.1.1, 8.8.8.8
Jc = {jc}
Jmin = {jmin}
Jmax = {jmax}
S1 = {s1}
S2 = {s2}
H1 = {h1}
H2 = {h2}

[Peer]
PublicKey = {server_public_key}
Endpoint = {server_endpoint}:{self.port}
AllowedIPs = 0.0.0.0/0
PersistentKeepalive = 25
"""
        return config
    
    async def _add_peer(self, public_key: str, allowed_ip: str):
        """Add peer to interface"""
        subprocess.run(
            [
                "wg", "set", self.interface,
                "peer", public_key,
                "allowed-ips", f"{allowed_ip}/32"
            ],
            check=True
        )
    
    async def _remove_peer(self, public_key: str):
        """Remove peer from interface"""
        subprocess.run(
            ["wg", "set", self.interface, "peer", public_key, "remove"],
            check=False
        )
    
    async def _reload_interface(self):
        """Reload interface"""
        subprocess.run(
            ["wg", "syncconf", self.interface, f"{self.config_dir}/{self.interface}.conf"],
            check=False
        )
