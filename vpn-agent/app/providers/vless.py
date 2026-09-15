"""
Plain VLESS VPN Provider (XRay-core) - Without Reality
Simpler and more reliable than VLESS+Reality
Supports TCP, gRPC, and WebSocket transports for optimal speed
"""
import subprocess
import json
import uuid
from typing import Dict
from pathlib import Path

from app.config import settings
from loguru import logger


class VlessManager:
    """Plain VLESS VPN management using XRay-core (without Reality)"""
    
    def __init__(self):
        self.config_dir = Path("/etc/xray")
        self.xray_bin = "/usr/local/bin/xray"
        self.server_ip = settings.server_ip
        self.port = settings.vless_port if hasattr(settings, 'vless_port') else 443
        self.transport = getattr(settings, 'vless_transport', 'tcp')
        self.grpc_service_name = getattr(settings, 'grpc_service_name', 'vpn')
        self.buffer_size = getattr(settings, 'buffer_size_mb', 10) * 1024  # Convert to KB
        self.tcp_fast_open = getattr(settings, 'enable_tcp_fast_open', True)
        
        # Ensure config directory exists
        self.config_dir.mkdir(parents=True, exist_ok=True)
    
    async def create_user(self, username: str) -> Dict[str, str]:
        """
        Create VLESS user
        
        Args:
            username: Unique username
        
        Returns:
            Dict with connection details
        """
        try:
            # Generate UUID for user
            user_id = str(uuid.uuid4())
            
            # Add user to XRay config
            await self._add_user_to_config(username, user_id)
            
            # Reload XRay
            await self._reload_xray()
            
            # Generate connection string (vless://)
            vless_link = self._generate_vless_link(
                user_id=user_id,
                server=self.server_ip,
                port=self.port
            )
            
            logger.info(f"Created VLESS user: {username}")
            
            return {
                "protocol": "vless",
                "user_id": user_id,
                "server": self.server_ip,
                "port": str(self.port),
                "config": vless_link,
                "instructions": self._get_instructions()
            }
            
        except Exception as e:
            logger.error(f"Failed to create VLESS user {username}: {e}")
            raise
    
    async def add_client(self, client_uuid: str, client_email: str) -> bool:
        """
        Add client to XRay config (called from backend API)
        
        Args:
            client_uuid: Client UUID
            client_email: Client email/identifier
        
        Returns:
            Success status
        """
        try:
            await self._add_user_to_config(client_email, client_uuid)
            await self._reload_xray()
            logger.info(f"Added VLESS client: {client_email} ({client_uuid})")
            return True
        except Exception as e:
            logger.error(f"Failed to add VLESS client {client_email}: {e}")
            return False
    
    async def remove_client(self, client_uuid: str) -> bool:
        """
        Remove client from XRay config
        
        Args:
            client_uuid: Client UUID to remove
        
        Returns:
            Success status
        """
        try:
            config_path = self.config_dir / "config.json"
            
            if not config_path.exists():
                logger.warning("XRay config not found")
                return False
            
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            # Find and remove user by UUID
            for inbound in config.get('inbounds', []):
                if inbound.get('protocol') == 'vless':
                    clients = inbound.get('settings', {}).get('clients', [])
                    inbound['settings']['clients'] = [
                        c for c in clients if c.get('id') != client_uuid
                    ]
            
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)
            
            await self._reload_xray()
            logger.info(f"Removed VLESS client: {client_uuid}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to remove VLESS client {client_uuid}: {e}")
            return False
    
    async def delete_user(self, username: str) -> bool:
        """
        Delete VLESS user by username
        
        Args:
            username: Username to delete
        
        Returns:
            Success status
        """
        try:
            config_path = self.config_dir / "config.json"
            
            if not config_path.exists():
                logger.warning("XRay config not found")
                return False
            
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            # Find and remove user
            for inbound in config.get('inbounds', []):
                if inbound.get('protocol') == 'vless':
                    clients = inbound.get('settings', {}).get('clients', [])
                    inbound['settings']['clients'] = [
                        c for c in clients if c.get('email') != username
                    ]
            
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)
            
            await self._reload_xray()
            logger.info(f"Deleted VLESS user: {username}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete VLESS user {username}: {e}")
            return False
    
    async def get_user_status(self, username: str) -> Dict:
        """
        Get user connection status
        
        Args:
            username: Username
        
        Returns:
            Status dict
        """
        return {
            "connected": False,
            "traffic_up": 0,
            "traffic_down": 0
        }
    
    async def _add_user_to_config(self, username: str, user_id: str):
        """Add user to XRay config"""
        config_path = self.config_dir / "config.json"
        
        # Load or create config
        if config_path.exists():
            with open(config_path, 'r') as f:
                config = json.load(f)
        else:
            config = self._create_base_config()
        
        # Check if user already exists
        for inbound in config.get('inbounds', []):
            if inbound.get('protocol') == 'vless':
                clients = inbound.setdefault('settings', {}).setdefault('clients', [])
                
                # Check if UUID already exists
                if any(c.get('id') == user_id for c in clients):
                    logger.info(f"Client {user_id} already exists in config")
                    return
                
                clients.append({
                    "id": user_id,
                    "email": username
                })
                break
        
        # Save config
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
    
    def _create_base_config(self) -> dict:
        """Create optimized XRay config for plain VLESS (no Reality, no TLS)
        Supports TCP, gRPC, and WebSocket transports for optimal speed"""
        
        # Build stream settings based on transport type
        stream_settings = self._build_stream_settings()
        
        return {
            "log": {
                "loglevel": "warning",
                "access": "/var/log/xray/access.log",
                "error": "/var/log/xray/error.log"
            },
            # DNS optimization for faster resolution
            "dns": {
                "hosts": {
                    "dns.google": "8.8.8.8"
                },
                "servers": [
                    {
                        "address": "8.8.8.8",
                        "port": 53,
                        "domains": ["geosite:geolocation-!cn"]
                    },
                    {
                        "address": "1.1.1.1",
                        "port": 53
                    }
                ],
                "queryStrategy": "UseIP",
                "disableCache": False,
                "disableFallback": False
            },
            "inbounds": [
                {
                    "port": self.port,
                    "protocol": "vless",
                    "settings": {
                        "clients": [],
                        "decryption": "none"
                    },
                    "streamSettings": stream_settings,
                    "sniffing": {
                        "enabled": True,
                        "destOverride": ["http", "tls", "quic"],
                        "metadataOnly": False,
                        "routeOnly": False
                    }
                }
            ],
            "outbounds": [
                {
                    "protocol": "freedom",
                    "tag": "direct",
                    "settings": {
                        "domainStrategy": "UseIP"  # Faster DNS resolution
                    },
                    "streamSettings": {
                        "sockopt": {
                            "tcpFastOpen": self.tcp_fast_open,
                            "tcpNoDelay": True,
                            "tcpKeepAliveInterval": 30
                        }
                    }
                },
                {
                    "protocol": "blackhole",
                    "tag": "blocked"
                }
            ],
            "routing": {
                "domainStrategy": "IPIfNonMatch",  # Better routing performance
                "rules": [
                    {
                        "type": "field",
                        "ip": ["geoip:private"],
                        "outboundTag": "direct"
                    }
                ]
            },
            # Buffer size optimization
            "policy": {
                "levels": {
                    "0": {
                        "handshake": 4,
                        "connIdle": 300,
                        "uplinkOnly": 2,
                        "downlinkOnly": 5,
                        "statsUserUplink": False,
                        "statsUserDownlink": False,
                        "bufferSize": self.buffer_size  # Configurable buffer for faster transfers
                    }
                },
                "system": {
                    "statsInboundUplink": False,
                    "statsInboundDownlink": False,
                    "statsOutboundUplink": False,
                    "statsOutboundDownlink": False
                }
            }
        }
    
    def _build_stream_settings(self) -> dict:
        """Build stream settings based on transport type"""
        base_sockopt = {
            "mark": 0,
            "tcpFastOpen": self.tcp_fast_open,
            "tproxy": "off",
            "tcpKeepAliveInterval": 30,
            "tcpNoDelay": True  # Disable Nagle's algorithm for lower latency
        }
        
        if self.transport == "grpc":
            # gRPC transport - best for high-speed connections
            return {
                "network": "grpc",
                "grpcSettings": {
                    "serviceName": self.grpc_service_name,
                    "multiMode": True,  # Enable multi-mode for better performance
                    "idle_timeout": 60,
                    "health_check_timeout": 20,
                    "permit_without_stream": False,
                    "initial_windows_size": 65535  # Larger window for speed
                },
                "sockopt": base_sockopt
            }
        elif self.transport == "ws":
            # WebSocket transport - good compatibility
            return {
                "network": "ws",
                "wsSettings": {
                    "path": "/vpn",
                    "headers": {
                        "Host": "www.example.com"
                    }
                },
                "sockopt": base_sockopt
            }
        elif self.transport == "h2":
            # HTTP/2 transport - good balance of speed and compatibility
            return {
                "network": "h2",
                "httpSettings": {
                    "host": ["www.example.com"],
                    "path": "/vpn"
                },
                "sockopt": base_sockopt
            }
        else:
            # TCP transport - default, simple setup
            return {
                "network": "tcp",
                "tcpSettings": {
                    "acceptProxyProtocol": False,
                    "header": {
                        "type": "none"
                    }
                },
                "sockopt": base_sockopt
            }
    
    def _generate_vless_link(self, user_id: str, server: str, port: int) -> str:
        """Generate VLESS connection link (without Reality)"""
        from urllib.parse import quote
        
        if self.transport == "grpc":
            params = [
                "type=grpc",
                f"serviceName={self.grpc_service_name}",
                "mode=multi",
                "security=none",
                "encryption=none"
            ]
        elif self.transport == "ws":
            params = [
                "type=ws",
                "path=/vpn",
                "security=none",
                "encryption=none"
            ]
        elif self.transport == "h2":
            params = [
                "type=http",
                "path=/vpn",
                "security=none",
                "encryption=none"
            ]
        else:
            params = [
                "type=tcp",
                "security=none",
                "encryption=none"
            ]
        
        alias = "MetaLib"
        link = f"vless://{user_id}@{server}:{port}?{'&'.join(params)}#{quote(alias)}"
        return link
    
    async def _reload_xray(self):
        """Reload XRay service"""
        try:
            subprocess.run(
                ["systemctl", "reload", "xray"],
                check=True,
                capture_output=True
            )
        except subprocess.CalledProcessError as e:
            logger.warning(f"Failed to reload XRay: {e}")
            # Try restart instead
            try:
                subprocess.run(
                    ["systemctl", "restart", "xray"],
                    check=True,
                    capture_output=True
                )
            except subprocess.CalledProcessError as e2:
                logger.error(f"Failed to restart XRay: {e2}")
                raise
    
    def _get_instructions(self) -> str:
        """Get client setup instructions"""
        return """
🔌 Установка VPN клиента:

📱 Android: v2rayNG (Google Play)
📱 iOS: Shadowrocket, FoXray, V2Box
💻 Windows: v2rayN, Nekoray
💻 macOS: V2RayXS, FoXray

📋 Инструкция:
1. Скачайте приложение
2. Нажмите + → Импорт из буфера
3. Вставьте ссылку vless://...
4. Подключитесь!

❓ Проблемы? Напишите в поддержку.
"""
