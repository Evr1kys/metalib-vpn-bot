"""
VLESS over CDN (Cloudflare) - Обход блокировок РКН
Использует WebSocket через Cloudflare CDN для маскировки трафика

Принцип работы:
1. Трафик идёт через Cloudflare CDN (не блокируется РКН)
2. WebSocket маскирует VPN под обычный HTTPS
3. Cloudflare проксирует на наш сервер
"""
import subprocess
import json
import uuid
import os
from typing import Dict, Optional
from pathlib import Path
from urllib.parse import quote

from app.config import settings
from loguru import logger


class VlessCDNManager:
    """VLESS over Cloudflare CDN - обход блокировок РКН"""
    
    def __init__(self):
        self.config_dir = Path("/etc/xray")
        self.xray_bin = "/usr/local/bin/xray"
        self.server_ip = settings.server_ip
        
        # CDN настройки - пользователь задаёт свой домен через Cloudflare
        self.cdn_domain = getattr(settings, 'cdn_domain', None)  # Например: vpn.metalib.xyz
        self.cdn_port = 443  # Всегда HTTPS через Cloudflare
        self.ws_path = getattr(settings, 'ws_path', '/ws')  # WebSocket путь
        self.local_port = getattr(settings, 'vless_ws_port', 8443)  # Локальный порт для WS
        
        self.config_dir.mkdir(parents=True, exist_ok=True)
    
    async def create_user(self, username: str) -> Dict[str, str]:
        """
        Создать VLESS пользователя с CDN туннелем
        """
        try:
            user_id = str(uuid.uuid4())
            
            await self._add_user_to_config(username, user_id)
            await self._reload_xray()
            
            # Генерируем ссылку через CDN
            vless_link = self._generate_vless_cdn_link(
                user_id=user_id,
                cdn_domain=self.cdn_domain or self.server_ip,
                port=self.cdn_port if self.cdn_domain else self.local_port
            )
            
            logger.info(f"Created VLESS CDN user: {username}")
            
            return {
                "protocol": "vless-cdn",
                "user_id": user_id,
                "server": self.cdn_domain or self.server_ip,
                "port": str(self.cdn_port if self.cdn_domain else self.local_port),
                "config": vless_link,
                "instructions": self._get_instructions()
            }
            
        except Exception as e:
            logger.error(f"Failed to create VLESS CDN user {username}: {e}")
            raise
    
    async def add_client(self, client_uuid: str, client_email: str) -> bool:
        """Добавить клиента"""
        try:
            await self._add_user_to_config(client_email, client_uuid)
            await self._reload_xray()
            return True
        except Exception as e:
            logger.error(f"Failed to add VLESS CDN client {client_email}: {e}")
            return False
    
    async def remove_client(self, client_uuid: str) -> bool:
        """Удалить клиента"""
        try:
            config_path = self.config_dir / "config.json"
            
            if not config_path.exists():
                return False
            
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            for inbound in config.get('inbounds', []):
                if inbound.get('tag') == 'vless-ws-in':
                    clients = inbound.get('settings', {}).get('clients', [])
                    inbound['settings']['clients'] = [
                        c for c in clients if c.get('id') != client_uuid
                    ]
            
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)
            
            await self._reload_xray()
            return True
            
        except Exception as e:
            logger.error(f"Failed to remove client {client_uuid}: {e}")
            return False
    
    async def _add_user_to_config(self, username: str, user_id: str):
        """Добавить пользователя в конфиг"""
        config_path = self.config_dir / "config.json"
        
        if config_path.exists():
            with open(config_path, 'r') as f:
                config = json.load(f)
        else:
            config = self._create_base_config()
        
        # Ищем WebSocket inbound
        ws_inbound = None
        for inbound in config.get('inbounds', []):
            if inbound.get('tag') == 'vless-ws-in':
                ws_inbound = inbound
                break
        
        if not ws_inbound:
            # Добавляем WebSocket inbound если нет
            ws_inbound = self._create_ws_inbound()
            config['inbounds'].append(ws_inbound)
        
        # Добавляем клиента
        clients = ws_inbound.setdefault('settings', {}).setdefault('clients', [])
        
        if not any(c.get('id') == user_id for c in clients):
            clients.append({
                "id": user_id,
                "email": username,
                "level": 0
            })
        
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
    
    def _create_ws_inbound(self) -> dict:
        """Создать WebSocket inbound для CDN"""
        return {
            "tag": "vless-ws-in",
            "port": self.local_port,
            "protocol": "vless",
            "settings": {
                "clients": [],
                "decryption": "none"
            },
            "streamSettings": {
                "network": "ws",
                "wsSettings": {
                    "path": self.ws_path,
                    "headers": {
                        "Host": self.cdn_domain or ""
                    }
                },
                "sockopt": {
                    "tcpFastOpen": True,
                    "tcpNoDelay": True
                }
            },
            "sniffing": {
                "enabled": True,
                "destOverride": ["http", "tls", "quic"]
            }
        }
    
    def _create_base_config(self) -> dict:
        """Базовый конфиг XRay с WebSocket для CDN"""
        return {
            "log": {
                "loglevel": "warning",
                "access": "/var/log/xray/access.log",
                "error": "/var/log/xray/error.log"
            },
            "dns": {
                "servers": [
                    {"address": "8.8.8.8", "port": 53},
                    {"address": "1.1.1.1", "port": 53}
                ],
                "queryStrategy": "UseIP"
            },
            "inbounds": [
                self._create_ws_inbound()
            ],
            "outbounds": [
                {
                    "protocol": "freedom",
                    "tag": "direct",
                    "settings": {"domainStrategy": "UseIP"},
                    "streamSettings": {
                        "sockopt": {
                            "tcpFastOpen": True,
                            "tcpNoDelay": True
                        }
                    }
                },
                {
                    "protocol": "blackhole",
                    "tag": "blocked"
                }
            ],
            "routing": {
                "domainStrategy": "IPIfNonMatch",
                "rules": [
                    {"type": "field", "ip": ["geoip:private"], "outboundTag": "direct"}
                ]
            },
            "policy": {
                "levels": {
                    "0": {
                        "handshake": 4,
                        "connIdle": 300,
                        "uplinkOnly": 2,
                        "downlinkOnly": 5,
                        "bufferSize": 10240
                    }
                }
            }
        }
    
    def _generate_vless_cdn_link(self, user_id: str, cdn_domain: str, port: int) -> str:
        """Генерировать VLESS ссылку через CDN"""
        # Если есть CDN домен - используем TLS
        if self.cdn_domain:
            params = [
                "type=ws",
                f"path={quote(self.ws_path)}",
                "security=tls",
                f"sni={cdn_domain}",
                f"host={cdn_domain}",
                "encryption=none"
            ]
        else:
            # Без CDN - без TLS (для локального тестирования)
            params = [
                "type=ws",
                f"path={quote(self.ws_path)}",
                "security=none",
                "encryption=none"
            ]
        
        alias = "MetaLib"
        link = f"vless://{user_id}@{cdn_domain}:{port}?{'&'.join(params)}#{quote(alias)}"
        return link
    
    async def _reload_xray(self):
        """Перезагрузить XRay"""
        try:
            subprocess.run(["systemctl", "reload", "xray"], check=True, capture_output=True)
        except subprocess.CalledProcessError:
            try:
                subprocess.run(["systemctl", "restart", "xray"], check=True, capture_output=True)
            except subprocess.CalledProcessError as e:
                logger.error(f"Failed to restart XRay: {e}")
                raise
    
    def _get_instructions(self) -> str:
        """Инструкции для пользователя"""
        return """
🛡️ MetaLib VPN - Подключение

📱 Приложения:
• Android: v2rayNG, NekoBox
• iOS: Shadowrocket, FoXray, Streisand
• Windows: v2rayN, Nekoray
• macOS: V2RayXS, FoXray

📋 Установка:
1. Скопируйте ключ выше
2. В приложении нажмите + → Импорт
3. Вставьте ключ
4. Подключитесь!

✅ Работает даже при блокировках РКН
"""
