"""
VPN Agent Configuration
"""
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Agent settings"""
    
    # Server configuration
    agent_host: str = Field(default="0.0.0.0", description="Agent host")
    agent_port: int = Field(default=8444, description="Agent port")
    
    # Security - this MUST match backend VPN_AGENT_SECRET_KEY
    agent_secret_key: str = Field(
        ...,
        description="Secret key for HMAC authentication"
    )
    
    # VPN configuration
    wireguard_enabled: bool = Field(default=True, description="Enable WireGuard")
    openvpn_enabled: bool = Field(default=True, description="Enable OpenVPN")
    amnezia_enabled: bool = Field(default=True, description="Enable Amnezia")
    vless_reality_enabled: bool = Field(default=True, description="Enable VLESS+Reality")
    
    # WireGuard paths
    wg_config_dir: str = Field(default="/etc/wireguard", description="WireGuard config directory")
    wg_interface: str = Field(default="wg0", description="WireGuard interface name")
    wg_server_ip: str = Field(default="10.8.0.1", description="WireGuard server IP")
    wg_subnet: str = Field(default="10.8.0.0/24", description="WireGuard subnet")
    wg_port: int = Field(default=51820, description="WireGuard port")
    
    # OpenVPN paths
    ovpn_config_dir: str = Field(default="/etc/openvpn", description="OpenVPN config directory")
    ovpn_client_config_dir: str = Field(default="/etc/openvpn/clients", description="OpenVPN client configs")
    ovpn_ca_cert: str = Field(default="/etc/openvpn/ca.crt", description="OpenVPN CA certificate")
    ovpn_server_cert: str = Field(default="/etc/openvpn/server.crt", description="OpenVPN server cert")
    ovpn_server_key: str = Field(default="/etc/openvpn/server.key", description="OpenVPN server key")
    ovpn_dh: str = Field(default="/etc/openvpn/dh2048.pem", description="OpenVPN DH params")
    ovpn_server_ip: str = Field(default="10.9.0.1", description="OpenVPN server IP")
    ovpn_subnet: str = Field(default="10.9.0.0", description="OpenVPN subnet")
    ovpn_subnet_mask: str = Field(default="255.255.255.0", description="OpenVPN subnet mask")
    ovpn_port: int = Field(default=1194, description="OpenVPN port")
    
    # Amnezia paths (WireGuard-based with obfuscation)
    amnezia_config_dir: str = Field(default="/etc/amnezia", description="Amnezia config directory")
    amnezia_interface: str = Field(default="awg0", description="Amnezia interface name")
    amnezia_server_ip: str = Field(default="10.10.0.1", description="Amnezia server IP")
    amnezia_subnet: str = Field(default="10.10.0.0/24", description="Amnezia subnet")
    amnezia_port: int = Field(default=52820, description="Amnezia port")
    
    # VLESS+Reality (XRay-core)
    vless_port: int = Field(default=443, description="VLESS port")
    vless_domain: str = Field(default="www.microsoft.com", description="Reality SNI domain")
    server_ip: str = Field(default="0.0.0.0", description="Server public IP")
    
    # Performance optimization
    vless_transport: str = Field(default="tcp", description="VLESS transport: tcp, grpc, ws")
    grpc_service_name: str = Field(default="vpn", description="gRPC service name")
    enable_tcp_fast_open: bool = Field(default=True, description="Enable TCP Fast Open")
    buffer_size_mb: int = Field(default=10, description="Buffer size in MB for Xray policy")
    
    # Logging
    log_level: str = Field(default="INFO", description="Logging level")
    
    model_config = {
        "env_file": ".env",
        "case_sensitive": False,
        "extra": "ignore"
    }


settings = Settings()
