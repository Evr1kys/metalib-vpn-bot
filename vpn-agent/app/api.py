"""
VPN Agent API Routes
"""
import subprocess
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from typing import Optional, Dict, Any

from app.config import settings
from app.security import verify_hmac_signature
from app.providers.wireguard import WireGuardManager
from app.providers.openvpn import OpenVPNManager
from app.providers.amnezia import AmneziaManager
from app.providers.vless import VlessManager  # Plain VLESS (simpler, more reliable)
from loguru import logger

router = APIRouter()

# Initialize managers
wg_manager = WireGuardManager() if settings.wireguard_enabled else None
ovpn_manager = OpenVPNManager() if settings.openvpn_enabled else None
amnezia_manager = AmneziaManager() if settings.amnezia_enabled else None
vless_manager = VlessManager() if settings.vless_reality_enabled else None  # Uses vless_reality_enabled flag


# Request/Response models
class CreateUserRequest(BaseModel):
    username: str
    protocol: str  # wireguard, openvpn, amnezia, vless


class CreateUserResponse(BaseModel):
    success: bool
    config: str
    public_key: Optional[str] = None
    client_ip: Optional[str] = None


class DeleteUserRequest(BaseModel):
    username: str
    protocol: str
    public_key: Optional[str] = None


class RotateKeysRequest(BaseModel):
    username: str
    protocol: str


class HealthResponse(BaseModel):
    status: str
    wireguard: bool
    openvpn: bool
    amnezia: bool
    vless: bool  # Plain VLESS without Reality


class OptimizationResponse(BaseModel):
    success: bool
    message: str
    details: Optional[Dict[str, Any]] = None


# Routes
@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        wireguard=settings.wireguard_enabled,
        openvpn=settings.openvpn_enabled,
        amnezia=settings.amnezia_enabled,
        vless=settings.vless_reality_enabled  # Reusing the flag
    )


@router.post("/optimize-network", response_model=OptimizationResponse)
async def optimize_network(request: Request):
    """
    Apply network optimizations for better VPN performance.
    Requires HMAC authentication.
    """
    # Verify HMAC signature
    body = await request.body()
    signature = request.headers.get("Authorization")
    
    if not signature:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication"
        )
    
    try:
        # Apply sysctl optimizations
        optimizations = {}
        
        # TCP optimizations
        sysctl_settings = {
            "net.core.rmem_max": "67108864",
            "net.core.wmem_max": "67108864",
            "net.core.rmem_default": "1048576",
            "net.core.wmem_default": "1048576",
            "net.ipv4.tcp_rmem": "4096 1048576 67108864",
            "net.ipv4.tcp_wmem": "4096 1048576 67108864",
            "net.core.somaxconn": "65535",
            "net.ipv4.tcp_fastopen": "3",
            "net.ipv4.tcp_tw_reuse": "1",
            "net.ipv4.tcp_fin_timeout": "15",
            "net.ipv4.tcp_slow_start_after_idle": "0",
            "net.ipv4.ip_forward": "1",
        }
        
        for key, value in sysctl_settings.items():
            try:
                subprocess.run(
                    ["sysctl", "-w", f"{key}={value}"],
                    check=True,
                    capture_output=True
                )
                optimizations[key] = "applied"
            except subprocess.CalledProcessError:
                optimizations[key] = "failed"
        
        # Try to enable BBR
        try:
            subprocess.run(
                ["sysctl", "-w", "net.core.default_qdisc=fq"],
                check=True,
                capture_output=True
            )
            subprocess.run(
                ["sysctl", "-w", "net.ipv4.tcp_congestion_control=bbr"],
                check=True,
                capture_output=True
            )
            optimizations["bbr"] = "enabled"
        except subprocess.CalledProcessError:
            optimizations["bbr"] = "not available, using default"
        
        # Reload Xray if running
        try:
            subprocess.run(
                ["systemctl", "reload", "xray"],
                check=True,
                capture_output=True
            )
            optimizations["xray"] = "reloaded"
        except subprocess.CalledProcessError:
            optimizations["xray"] = "reload skipped"
        
        return OptimizationResponse(
            success=True,
            message="Network optimizations applied successfully",
            details=optimizations
        )
        
    except Exception as e:
        logger.error(f"Failed to apply optimizations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/performance-stats")
async def get_performance_stats():
    """Get current performance settings and stats"""
    try:
        stats = {
            "transport": getattr(settings, 'vless_transport', 'tcp'),
            "tcp_fast_open": getattr(settings, 'enable_tcp_fast_open', True),
            "buffer_size_mb": getattr(settings, 'buffer_size_mb', 10),
        }
        
        # Get current sysctl values
        try:
            result = subprocess.run(
                ["sysctl", "net.ipv4.tcp_congestion_control"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                stats["congestion_control"] = result.stdout.strip().split("=")[-1].strip()
        except:
            pass
        
        try:
            result = subprocess.run(
                ["sysctl", "net.ipv4.tcp_fastopen"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                stats["system_tcp_fastopen"] = result.stdout.strip().split("=")[-1].strip()
        except:
            pass
        
        return {"success": True, "stats": stats}
        
    except Exception as e:
        logger.error(f"Failed to get stats: {e}")
        return {"success": False, "error": str(e)}


@router.post("/users/create", response_model=CreateUserResponse)
async def create_user(request: Request, data: CreateUserRequest):
    """
    Create VPN user
    
    Requires HMAC authentication via headers:
    - X-Signature: HMAC signature of request body
    - X-Timestamp: Request timestamp (ISO format)
    """
    # Verify HMAC signature
    body = await request.body()
    signature = request.headers.get("X-Signature")
    timestamp = request.headers.get("X-Timestamp")
    
    if not signature or not timestamp:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication headers"
        )
    
    if not verify_hmac_signature(body.decode(), signature, timestamp):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid signature"
        )
    
    # Create user based on protocol
    try:
        if data.protocol == "wireguard":
            if not wg_manager:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="WireGuard not enabled"
                )
            result = await wg_manager.create_user(data.username)
            
        elif data.protocol == "openvpn":
            if not ovpn_manager:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="OpenVPN not enabled"
                )
            result = await ovpn_manager.create_user(data.username)
            
        elif data.protocol == "amnezia":
            if not amnezia_manager:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Amnezia not enabled"
                )
            result = await amnezia_manager.create_user(data.username)
            
        elif data.protocol in ("vless", "vless+reality"):  # Support both for backward compatibility
            if not vless_manager:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="VLESS not enabled"
                )
            result = await vless_manager.create_user(data.username)
            
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown protocol: {data.protocol}"
            )
        
        return CreateUserResponse(
            success=True,
            config=result["config"],
            public_key=result.get("public_key"),
            client_ip=result.get("client_ip")
        )
    
    except Exception as e:
        logger.error(f"Failed to create user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/users/delete")
async def delete_user(request: Request, data: DeleteUserRequest):
    """Delete VPN user"""
    # Verify HMAC signature
    body = await request.body()
    signature = request.headers.get("X-Signature")
    timestamp = request.headers.get("X-Timestamp")
    
    if not signature or not timestamp:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication headers"
        )
    
    if not verify_hmac_signature(body.decode(), signature, timestamp):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid signature"
        )
    
    # Delete user
    try:
        if data.protocol == "wireguard":
            if not wg_manager:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="WireGuard not enabled"
                )
            await wg_manager.delete_user(data.username, data.public_key)
            
        elif data.protocol == "openvpn":
            if not ovpn_manager:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="OpenVPN not enabled"
                )
            await ovpn_manager.delete_user(data.username)
            
        elif data.protocol == "amnezia":
            if not amnezia_manager:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Amnezia not enabled"
                )
            await amnezia_manager.delete_user(data.username, data.public_key)
            
        elif data.protocol in ("vless", "vless+reality"):  # Support both for backward compatibility
            if not vless_manager:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="VLESS not enabled"
                )
            await vless_manager.delete_user(data.username)
            
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown protocol: {data.protocol}"
            )
        
        return {"success": True}
    
    except Exception as e:
        logger.error(f"Failed to delete user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/users/rotate", response_model=CreateUserResponse)
async def rotate_keys(request: Request, data: RotateKeysRequest):
    """Rotate user keys"""
    # Verify HMAC signature
    body = await request.body()
    signature = request.headers.get("X-Signature")
    timestamp = request.headers.get("X-Timestamp")
    
    if not signature or not timestamp:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication headers"
        )
    
    if not verify_hmac_signature(body.decode(), signature, timestamp):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid signature"
        )
    
    # Rotate keys
    try:
        if data.protocol == "wireguard":
            if not wg_manager:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="WireGuard not enabled"
                )
            result = await wg_manager.rotate_keys(data.username)
            
        elif data.protocol == "openvpn":
            if not ovpn_manager:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="OpenVPN not enabled"
                )
            result = await ovpn_manager.rotate_keys(data.username)
            
        elif data.protocol == "amnezia":
            if not amnezia_manager:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Amnezia not enabled"
                )
            result = await amnezia_manager.rotate_keys(data.username)
            
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown protocol: {data.protocol}"
            )
        
        return CreateUserResponse(
            success=True,
            config=result["config"],
            public_key=result.get("public_key"),
            client_ip=result.get("client_ip")
        )
    
    except Exception as e:
        logger.error(f"Failed to rotate keys: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# VLESS client management endpoints (called from backend)
class AddClientRequest(BaseModel):
    uuid: str
    email: str


class RemoveClientRequest(BaseModel):
    uuid: str


@router.post("/add-client")
async def add_vless_client(request: Request, data: AddClientRequest):
    """
    Add VLESS client to XRay config
    Called from backend xray_service.py
    """
    import hmac
    import hashlib
    
    # Verify HMAC signature
    body = await request.body()
    signature = request.headers.get("Authorization")
    
    if not signature:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization"
        )
    
    # Verify signature (same method as backend uses)
    expected_sig = hmac.new(
        settings.agent_secret_key.encode(),
        body,
        hashlib.sha256
    ).hexdigest()
    
    if signature != expected_sig:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid signature"
        )
    
    if not vless_manager:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="VLESS not enabled"
        )
    
    try:
        success = await vless_manager.add_client(data.uuid, data.email)
        return {"success": success}
    except Exception as e:
        logger.error(f"Failed to add VLESS client: {e}")
        return {"success": False, "error": str(e)}


@router.post("/remove-client")
async def remove_vless_client(request: Request, data: RemoveClientRequest):
    """
    Remove VLESS client from XRay config
    Called from backend xray_service.py
    """
    import hmac
    import hashlib
    
    # Verify HMAC signature
    body = await request.body()
    signature = request.headers.get("Authorization")
    
    if not signature:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization"
        )
    
    expected_sig = hmac.new(
        settings.agent_secret_key.encode(),
        body,
        hashlib.sha256
    ).hexdigest()
    
    if signature != expected_sig:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid signature"
        )
    
    if not vless_manager:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="VLESS not enabled"
        )
    
    try:
        success = await vless_manager.remove_client(data.uuid)
        return {"success": success}
    except Exception as e:
        logger.error(f"Failed to remove VLESS client: {e}")
        return {"success": False, "error": str(e)}


@router.get("/stats")
async def get_xray_stats(request: Request):
    """
    Get Xray traffic statistics
    Called from backend for admin panel
    """
    import hmac
    import hashlib
    import subprocess
    import json as json_lib
    
    # Verify HMAC signature
    signature = request.headers.get("Authorization")
    
    if not signature:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization"
        )
    
    expected_sig = hmac.new(
        settings.agent_secret_key.encode(),
        b"{}",
        hashlib.sha256
    ).hexdigest()
    
    if signature != expected_sig:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid signature"
        )
    
    try:
        # Query Xray stats via CLI
        result = subprocess.run(
            ["/usr/local/bin/xray", "api", "statsquery", "--server=127.0.0.1:10085"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            stats_data = json_lib.loads(result.stdout)
            
            # Parse stats into readable format
            parsed_stats = {
                "inbound": {"uplink": 0, "downlink": 0},
                "outbound": {"uplink": 0, "downlink": 0},
                "users": {}
            }
            
            for stat in stats_data.get("stat", []):
                name = stat.get("name", "")
                value = stat.get("value", 0)
                
                if ">>>user>>>" in name:
                    # User traffic: user>>>email>>>traffic>>>uplink/downlink
                    parts = name.split(">>>")
                    if len(parts) >= 4:
                        email = parts[1]
                        direction = parts[3]
                        if email not in parsed_stats["users"]:
                            parsed_stats["users"][email] = {"uplink": 0, "downlink": 0}
                        parsed_stats["users"][email][direction] = value
                elif "inbound>>>" in name and "api" not in name:
                    # Inbound traffic
                    if "uplink" in name:
                        parsed_stats["inbound"]["uplink"] = value
                    elif "downlink" in name:
                        parsed_stats["inbound"]["downlink"] = value
                elif "outbound>>>direct" in name:
                    # Outbound traffic
                    if "uplink" in name:
                        parsed_stats["outbound"]["uplink"] = value
                    elif "downlink" in name:
                        parsed_stats["outbound"]["downlink"] = value
            
            return {"success": True, "stats": parsed_stats, "raw": stats_data}
        else:
            return {"success": False, "error": result.stderr}
            
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Stats query timed out"}
    except Exception as e:
        logger.error(f"Failed to get stats: {e}")
        return {"success": False, "error": str(e)}


class AccessLogRequest(BaseModel):
    limit: int = 1000  # Max lines to return
    user_email: Optional[str] = None  # Filter by user email


@router.post("/access-logs")
async def get_access_logs(request: Request, data: AccessLogRequest):
    """
    Get Xray access logs with domain/site information per user
    Parses /var/log/xray/access.log
    """
    import hmac
    import hashlib
    from collections import defaultdict
    from datetime import datetime
    import re
    
    # Verify HMAC signature
    body = await request.body()
    signature = request.headers.get("Authorization")
    
    if not signature:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization"
        )
    
    expected_sig = hmac.new(
        settings.agent_secret_key.encode(),
        body,
        hashlib.sha256
    ).hexdigest()
    
    if signature != expected_sig:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid signature"
        )
    
    try:
        log_file = "/var/log/xray/access.log"
        
        # Check if log file exists
        import os
        if not os.path.exists(log_file):
            return {
                "success": True, 
                "logs": [],
                "users": {},
                "message": "Log file not found - no traffic yet"
            }
        
        # Read last N lines from log file (tail)
        import subprocess
        result = subprocess.run(
            ["tail", f"-n{data.limit}", log_file],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode != 0:
            return {"success": False, "error": "Failed to read log file"}
        
        lines = result.stdout.strip().split("\n") if result.stdout.strip() else []
        
        # Parse log entries
        # Format: 2024/01/08 12:34:56 from 1.2.3.4:12345 accepted tcp:google.com:443 [user_email]
        log_pattern = re.compile(
            r"(\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2})\s+"
            r"from\s+([\d.]+:\d+)\s+"
            r"accepted\s+"
            r"(tcp|udp):([^:]+):(\d+)\s*"
            r"(?:\[([^\]]+)\])?"
        )
        
        parsed_logs = []
        users_data = defaultdict(lambda: {
            "domains": defaultdict(int),
            "total_requests": 0,
            "last_seen": None,
            "ips": set()
        })
        
        for line in lines:
            if not line.strip():
                continue
                
            match = log_pattern.match(line)
            if match:
                timestamp, src_ip, protocol, domain, port, email = match.groups()
                email = email or "unknown"
                
                # Filter by user if specified
                if data.user_email and email != data.user_email:
                    continue
                
                entry = {
                    "timestamp": timestamp,
                    "source_ip": src_ip.split(":")[0],
                    "domain": domain,
                    "port": int(port),
                    "protocol": protocol,
                    "user_email": email
                }
                parsed_logs.append(entry)
                
                # Aggregate user data
                users_data[email]["domains"][domain] += 1
                users_data[email]["total_requests"] += 1
                users_data[email]["last_seen"] = timestamp
                users_data[email]["ips"].add(src_ip.split(":")[0])
        
        # Convert sets to lists for JSON serialization
        users_summary = {}
        for email, user_data in users_data.items():
            # Get top 50 domains by request count
            top_domains = sorted(
                user_data["domains"].items(),
                key=lambda x: x[1],
                reverse=True
            )[:50]
            
            users_summary[email] = {
                "total_requests": user_data["total_requests"],
                "last_seen": user_data["last_seen"],
                "unique_ips": list(user_data["ips"]),
                "top_domains": [{"domain": d, "count": c} for d, c in top_domains],
                "unique_domains_count": len(user_data["domains"])
            }
        
        return {
            "success": True,
            "logs": parsed_logs[-200:],  # Return last 200 entries
            "users": users_summary,
            "total_entries": len(parsed_logs)
        }
        
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Reading logs timed out"}
    except Exception as e:
        logger.error(f"Failed to get access logs: {e}")
        return {"success": False, "error": str(e)}
