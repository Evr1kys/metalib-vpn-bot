"""
VLESS+Reality VPN Provider (XRay-core)
"""
import subprocess
import json
import uuid
from typing import Dict
from pathlib import Path

from app.config import settings
from loguru import logger


class VlessRealityManager:
    """VLESS+Reality VPN management using XRay-core"""
    
    def __init__(self):
        self.config_dir = Path("/etc/xray")
        self.xray_bin = "/usr/local/bin/xray"
        self.server_ip = settings.server_ip
        self.port = settings.vless_port if hasattr(settings, 'vless_port') else 443
        self.domain = settings.vless_domain if hasattr(settings, 'vless_domain') else "www.microsoft.com"
        
        # Reality parameters
        self.dest = f"{self.domain}:443"
        self.server_names = [self.domain]
        
        # Ensure config directory exists
        self.config_dir.mkdir(parents=True, exist_ok=True)
    
    async def create_user(self, username: str) -> Dict[str, str]:
        """
        Create VLESS+Reality user
        
        Args:
            username: Unique username
        
        Returns:
            Dict with connection details
        """
        try:
            # Generate UUID for user
            user_id = str(uuid.uuid4())
            
            # Generate Reality keypair if not exists
            private_key, public_key = await self._get_or_generate_keys()
            
            # Add user to XRay config
            await self._add_user_to_config(username, user_id)
            
            # Reload XRay
            await self._reload_xray()
            
            # Generate connection string (vless://)
            vless_link = self._generate_vless_link(
                user_id=user_id,
                server=self.server_ip,
                port=self.port,
                public_key=public_key,
                domain=self.domain
            )
            
            logger.info(f"Created VLESS+Reality user: {username}")
            
            return {
                "protocol": "vless+reality",
                "user_id": user_id,
                "server": self.server_ip,
                "port": str(self.port),
                "public_key": public_key,
                "domain": self.domain,
                "config": vless_link,
                "instructions": self._get_instructions()
            }
            
        except Exception as e:
            logger.error(f"Failed to create VLESS+Reality user {username}: {e}")
            raise
    
    async def delete_user(self, username: str) -> bool:
        """
        Delete VLESS+Reality user
        
        Args:
            username: Username to delete
        
        Returns:
            Success status
        """
        try:
            # Remove user from XRay config
            config_path = self.config_dir / "config.json"
            
            if not config_path.exists():
                logger.warning(f"XRay config not found")
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
            
            # Reload XRay
            await self._reload_xray()
            
            logger.info(f"Deleted VLESS+Reality user: {username}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete VLESS+Reality user {username}: {e}")
            return False
    
    async def get_user_status(self, username: str) -> Dict:
        """
        Get user connection status
        
        Args:
            username: Username
        
        Returns:
            Status dict
        """
        # XRay doesn't provide built-in stats API by default
        # Would need to enable stats API in config
        return {
            "connected": False,
            "traffic_up": 0,
            "traffic_down": 0
        }
    
    async def _get_or_generate_keys(self) -> tuple[str, str]:
        """Generate or load Reality keypair"""
        keys_file = self.config_dir / "reality_keys.json"
        
        if keys_file.exists():
            with open(keys_file, 'r') as f:
                keys = json.load(f)
                return keys['private_key'], keys['public_key']
        
        # Generate new keys
        result = subprocess.run(
            [self.xray_bin, "x25519"],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            raise Exception(f"Failed to generate keys: {result.stderr}")
        
        lines = result.stdout.strip().split('\n')
        private_key = lines[0].split(': ')[1]
        public_key = lines[1].split(': ')[1]
        
        # Save keys
        with open(keys_file, 'w') as f:
            json.dump({
                'private_key': private_key,
                'public_key': public_key
            }, f)
        
        return private_key, public_key
    
    async def _add_user_to_config(self, username: str, user_id: str):
        """Add user to XRay config"""
        config_path = self.config_dir / "config.json"
        
        # Load or create config
        if config_path.exists():
            with open(config_path, 'r') as f:
                config = json.load(f)
        else:
            private_key, public_key = await self._get_or_generate_keys()
            config = self._create_base_config(private_key)
        
        # Add user to VLESS inbound
        for inbound in config.get('inbounds', []):
            if inbound.get('protocol') == 'vless':
                clients = inbound.setdefault('settings', {}).setdefault('clients', [])
                clients.append({
                    "id": user_id,
                    "email": username,
                    "flow": "xtls-rprx-vision"
                })
                break
        
        # Save config
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
    
    def _create_base_config(self, private_key: str) -> dict:
        """Create optimized XRay config with Reality"""
        return {
            "log": {
                "loglevel": "warning"
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
                    "streamSettings": {
                        "network": "tcp",
                        "security": "reality",
                        "realitySettings": {
                            "show": False,
                            "dest": self.dest,
                            "xver": 0,
                            "serverNames": self.server_names,
                            "privateKey": private_key,
                            "shortIds": [""]
                        },
                        # TCP optimization for speed
                        "tcpSettings": {
                            "acceptProxyProtocol": False,
                            "header": {
                                "type": "none"
                            }
                        },
                        # Socket-level optimizations
                        "sockopt": {
                            "mark": 0,
                            "tcpFastOpen": True,  # Enable TCP Fast Open
                            "tproxy": "off",
                            "tcpKeepAliveInterval": 30,
                            "tcpNoDelay": True  # Disable Nagle's algorithm for lower latency
                        }
                    },
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
                            "tcpFastOpen": True,
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
                        "bufferSize": 10240  # 10MB buffer for faster transfers
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
    
    def _generate_vless_link(self, user_id: str, server: str, port: int, 
                            public_key: str, domain: str) -> str:
        """Generate VLESS connection link"""
        from urllib.parse import quote
        
        params = [
            f"security=reality",
            f"pbk={public_key}",
            f"fp=chrome",
            f"sni={domain}",
            f"type=tcp",
            f"flow=xtls-rprx-vision"
        ]
        
        # Простое название ключа
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
            subprocess.run(
                ["systemctl", "restart", "xray"],
                check=True,
                capture_output=True
            )
    
    def _get_instructions(self) -> str:
        """Get client setup instructions"""
        return """
1. Установите клиент v2rayN (Windows), v2rayNG (Android), или FoXray (iOS)
2. Нажмите "+" или "Добавить конфигурацию"
3. Выберите "Импорт из буфера обмена" и вставьте vless:// ссылку
4. Нажмите "Подключиться"

Поддерживаемые клиенты:
- Windows: v2rayN, NekoRay
- Android: v2rayNG, SagerNet
- iOS: FoXray, Shadowrocket
- macOS: V2RayXS, FoXray
"""
