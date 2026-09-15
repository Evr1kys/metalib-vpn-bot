"""
OpenVPN VPN Provider
"""
import os
import subprocess
from typing import Dict
from pathlib import Path

from app.config import settings
from loguru import logger


class OpenVPNManager:
    """OpenVPN management"""
    
    def __init__(self):
        self.config_dir = Path(settings.ovpn_config_dir)
        self.client_config_dir = Path(settings.ovpn_client_config_dir)
        self.ca_cert = settings.ovpn_ca_cert
        self.server_cert = settings.ovpn_server_cert
        self.server_key = settings.ovpn_server_key
        self.dh = settings.ovpn_dh
        self.port = settings.ovpn_port
        
        # Ensure directories exist
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.client_config_dir.mkdir(parents=True, exist_ok=True)
    
    async def create_user(self, username: str) -> Dict[str, str]:
        """
        Create OpenVPN user
        
        Args:
            username: Unique username
        
        Returns:
            Dict with config file content (.ovpn)
        """
        try:
            # Generate client certificate and key
            await self._generate_client_cert(username)
            
            # Generate client config
            config = await self._generate_client_config(username)
            
            # Save config
            config_file = self.client_config_dir / f"{username}.ovpn"
            config_file.write_text(config)
            
            logger.info(f"OpenVPN user created: {username}")
            
            return {
                "config": config
            }
        
        except Exception as e:
            logger.error(f"Failed to create OpenVPN user {username}: {e}")
            raise
    
    async def delete_user(self, username: str) -> bool:
        """
        Delete OpenVPN user
        
        Args:
            username: Username to delete
        
        Returns:
            True if successful
        """
        try:
            # Revoke certificate
            await self._revoke_client_cert(username)
            
            # Remove config file
            config_file = self.client_config_dir / f"{username}.ovpn"
            if config_file.exists():
                config_file.unlink()
            
            # Remove certificate files
            cert_file = self.client_config_dir / f"{username}.crt"
            key_file = self.client_config_dir / f"{username}.key"
            
            if cert_file.exists():
                cert_file.unlink()
            if key_file.exists():
                key_file.unlink()
            
            logger.info(f"OpenVPN user deleted: {username}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to delete OpenVPN user {username}: {e}")
            raise
    
    async def rotate_keys(self, username: str) -> Dict[str, str]:
        """
        Rotate user certificate
        
        Args:
            username: Username
        
        Returns:
            New config
        """
        # Delete old user
        await self.delete_user(username)
        
        # Create new user
        return await self.create_user(username)
    
    async def _generate_client_cert(self, username: str):
        """Generate client certificate using easy-rsa or openssl"""
        # This is a simplified version
        # In production, use easy-rsa or your PKI system
        
        # Generate private key
        subprocess.run(
            [
                "openssl", "genrsa",
                "-out", str(self.client_config_dir / f"{username}.key"),
                "2048"
            ],
            check=True
        )
        
        # Generate certificate signing request
        subprocess.run(
            [
                "openssl", "req",
                "-new",
                "-key", str(self.client_config_dir / f"{username}.key"),
                "-out", str(self.client_config_dir / f"{username}.csr"),
                "-subj", f"/CN={username}"
            ],
            check=True
        )
        
        # Sign certificate with CA
        subprocess.run(
            [
                "openssl", "x509",
                "-req",
                "-in", str(self.client_config_dir / f"{username}.csr"),
                "-CA", self.ca_cert,
                "-CAkey", str(self.config_dir / "ca.key"),
                "-CAcreateserial",
                "-out", str(self.client_config_dir / f"{username}.crt"),
                "-days", "365"
            ],
            check=True
        )
        
        # Remove CSR
        (self.client_config_dir / f"{username}.csr").unlink()
    
    async def _revoke_client_cert(self, username: str):
        """Revoke client certificate"""
        # This should update CRL (Certificate Revocation List)
        # Simplified implementation
        cert_file = self.client_config_dir / f"{username}.crt"
        if cert_file.exists():
            # In production: add to CRL and update server
            pass
    
    async def _generate_client_config(self, username: str) -> str:
        """Generate client .ovpn config file"""
        # Read certificates
        ca_cert_content = Path(self.ca_cert).read_text()
        client_cert_content = (self.client_config_dir / f"{username}.crt").read_text()
        client_key_content = (self.client_config_dir / f"{username}.key").read_text()
        
        # Get server endpoint
        server_endpoint = os.getenv('OVPN_SERVER_ENDPOINT', 'SERVER_IP')
        
        # Generate unified .ovpn file
        config = f"""client
dev tun
proto udp
remote {server_endpoint} {self.port}
resolv-retry infinite
nobind
persist-key
persist-tun
remote-cert-tls server
cipher AES-256-CBC
auth SHA256
verb 3

<ca>
{ca_cert_content}
</ca>

<cert>
{client_cert_content}
</cert>

<key>
{client_key_content}
</key>
"""
        return config
