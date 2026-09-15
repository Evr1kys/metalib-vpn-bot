"""
Enhanced Health Check Tasks with SSH Fallback

Features:
- HTTP health check to VPN agent (primary)
- SSH health check as fallback
- Parallel server checking for performance
- Detailed metrics collection
- Alert notifications for failures
"""
import os
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import select
from loguru import logger
import httpx

from worker.celery_app import celery_app
from app.core.database import get_worker_session
from app.models.server import Server, ServerStatus


class SSHHealthChecker:
    """
    SSH-based health checker for VPN servers.
    
    Used as fallback when HTTP agent is unavailable.
    Checks:
    - SSH connectivity
    - Xray process status
    - System resources (CPU, RAM, disk)
    - Network connectivity
    """
    
    def __init__(self, host: str, port: int = 22, username: str = "root", 
                 password: Optional[str] = None, key_path: Optional[str] = None):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.key_path = key_path or os.getenv("VPN_SERVER_SSH_KEY")
    
    async def check(self, timeout: int = 15) -> Dict[str, Any]:
        """
        Perform SSH health check.
        
        Returns:
            Dict with health status and metrics
        """
        try:
            import asyncssh
        except ImportError:
            logger.debug("asyncssh not installed, SSH health check disabled")
            return {"status": "skipped", "reason": "asyncssh not installed"}
        
        result = {
            "status": "unknown",
            "timestamp": datetime.utcnow().isoformat(),
            "host": self.host,
            "metrics": {}
        }
        
        try:
            # Connect via SSH
            connect_kwargs = {
                "host": self.host,
                "port": self.port,
                "username": self.username,
                "known_hosts": None,  # Skip host key verification
            }
            
            if self.key_path and os.path.exists(self.key_path):
                connect_kwargs["client_keys"] = [self.key_path]
            elif self.password:
                connect_kwargs["password"] = self.password
            
            async with asyncio.timeout(timeout):
                async with asyncssh.connect(**connect_kwargs) as conn:
                    # Check Xray process
                    xray_result = await conn.run("pgrep -c xray || echo 0", check=False)
                    xray_running = int(xray_result.stdout.strip()) > 0
                    result["metrics"]["xray_running"] = xray_running
                    
                    # Get system metrics - CPU load
                    cpu_result = await conn.run("cat /proc/loadavg | awk '{print $1}'", check=False)
                    result["metrics"]["cpu_load"] = float(cpu_result.stdout.strip())
                    
                    # Memory usage
                    mem_result = await conn.run(
                        "free | grep Mem | awk '{printf \"%.1f\", $3/$2 * 100}'",
                        check=False
                    )
                    result["metrics"]["memory_percent"] = float(mem_result.stdout.strip())
                    
                    # Disk usage
                    disk_result = await conn.run(
                        "df / | tail -1 | awk '{print $5}' | tr -d '%'",
                        check=False
                    )
                    result["metrics"]["disk_percent"] = int(disk_result.stdout.strip())
                    
                    # Network test
                    ping_result = await conn.run(
                        "ping -c 1 -W 2 8.8.8.8 >/dev/null 2>&1 && echo ok || echo fail",
                        check=False
                    )
                    result["metrics"]["network_ok"] = ping_result.stdout.strip() == "ok"
                    
                    # Active connections
                    conn_result = await conn.run(
                        "ss -tn state established '( sport = :443 )' | wc -l",
                        check=False
                    )
                    result["metrics"]["active_connections"] = max(0, int(conn_result.stdout.strip()) - 1)
                    
                    # Determine overall status
                    if not xray_running:
                        result["status"] = "degraded"
                        result["reason"] = "Xray not running"
                    elif not result["metrics"]["network_ok"]:
                        result["status"] = "degraded"
                        result["reason"] = "Network issues"
                    elif result["metrics"]["disk_percent"] > 90:
                        result["status"] = "degraded"
                        result["reason"] = f"Disk: {result['metrics']['disk_percent']}%"
                    elif result["metrics"]["memory_percent"] > 95:
                        result["status"] = "degraded"
                        result["reason"] = f"Memory: {result['metrics']['memory_percent']}%"
                    else:
                        result["status"] = "healthy"
            
            return result
            
        except asyncio.TimeoutError:
            result["status"] = "offline"
            result["reason"] = "Connection timeout"
            return result
        except Exception as e:
            result["status"] = "offline"
            result["reason"] = str(e)
            return result


async def check_server_health(server: Server) -> Dict[str, Any]:
    """
    Check server health using HTTP first, then SSH fallback.
    """
    server_ip = str(server.ip_address) if server.ip_address else None
    
    if not server_ip:
        return {"status": "offline", "reason": "No IP address", "method": "none"}
    
    # Try HTTP health check first (via VPN agent)
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"http://{server_ip}:8444/health",
                headers={"X-Agent-Token": os.getenv("VPN_AGENT_TOKEN", "")}
            )
            if response.status_code == 200:
                health = response.json()
                return {
                    "status": health.get("status", "unknown"),
                    "metrics": health.get("metrics", {}),
                    "method": "http_agent"
                }
    except Exception as e:
        logger.debug(f"HTTP health check failed for {server.name}: {e}")
    
    # Fallback to SSH health check
    ssh_password = getattr(server, 'ssh_password', None) or os.getenv("VPN_SERVER_SSH_PASSWORD")
    ssh_key = os.getenv("VPN_SERVER_SSH_KEY")
    
    if ssh_password or ssh_key:
        checker = SSHHealthChecker(
            host=server_ip,
            port=getattr(server, 'ssh_port', 22) or 22,
            username="root",
            password=ssh_password,
            key_path=ssh_key
        )
        result = await checker.check()
        result["method"] = "ssh_fallback"
        return result
    
    return {"status": "unknown", "reason": "Cannot reach server", "method": "none"}


async def send_health_alert(message: str):
    """Send health alert to admin Telegram"""
    from app.core.config import settings
    
    admin_chat_id = getattr(settings, 'admin_telegram_chat_id', None)
    if not admin_chat_id:
        return
    
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage",
                json={"chat_id": admin_chat_id, "text": message, "parse_mode": "HTML"}
            )
    except Exception as e:
        logger.error(f"Failed to send health alert: {e}")


@celery_app.task(name="worker.tasks.health_checks.check_all_servers")
def check_all_servers():
    """Check health of all active servers"""
    from worker.celery_app import run_async
    return run_async(check_all_servers_async())


async def check_all_servers_async():
    """
    Async implementation with parallel checks and SSH fallback.
    """
    db = get_worker_session()
    try:
        result = await db.execute(
            select(Server).where(Server.is_active == True)
        )
        servers = result.scalars().all()
        
        logger.info(f"Checking health of {len(servers)} servers")
        
        # Parallel health checks (max 10 concurrent)
        semaphore = asyncio.Semaphore(10)
        
        async def check_with_semaphore(server):
            async with semaphore:
                return await check_server_health(server)
        
        tasks = [check_with_semaphore(s) for s in servers]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        healthy = degraded = offline = 0
        
        for server, health in zip(servers, results):
            if isinstance(health, Exception):
                server.status = ServerStatus.OFFLINE
                offline += 1
                continue
            
            status = health.get("status", "unknown")
            method = health.get("method", "unknown")
            
            if status == "healthy":
                server.status = ServerStatus.HEALTHY
                healthy += 1
            elif status == "degraded":
                server.status = ServerStatus.DEGRADED
                degraded += 1
                # Create degraded alert
                await create_server_alert(db, server, "degraded", health)
            else:
                server.status = ServerStatus.OFFLINE
                offline += 1
                # Create offline alert
                await create_server_alert(db, server, "offline", health)
            
            server.last_health_check = datetime.utcnow()
            logger.info(f"Server {server.name}: {status} (via {method})")
        
        await db.commit()
        
        # Alert if too many servers offline
        if offline > 0 and offline >= len(servers) * 0.5:
            await send_health_alert(f"⚠️ {offline}/{len(servers)} VPN серверов недоступны!")
        
        return {"checked": len(servers), "healthy": healthy, "degraded": degraded, "offline": offline}
    finally:
        await db.close()


async def create_server_alert(db, server, status_type: str, health: dict):
    """Create alert for server issues"""
    try:
        from app.services.alert_service import server_offline_alert, server_degraded_alert
        
        if status_type == "offline":
            await server_offline_alert(
                db, 
                server.name, 
                str(server.id),
                health.get("reason", "Unknown")
            )
        elif status_type == "degraded":
            await server_degraded_alert(
                db,
                server.name,
                str(server.id),
                health.get("metrics", {})
            )
    except Exception as e:
        logger.error(f"Failed to create server alert: {e}")


@celery_app.task(name="worker.tasks.health_checks.check_server")
def check_server(server_id: str):
    """Check health of specific server"""
    from worker.celery_app import run_async
    return run_async(check_server_async(server_id))


async def check_server_async(server_id: str):
    """Async implementation of single server check with SSH fallback"""
    db = get_worker_session()
    try:
        result = await db.execute(
            select(Server).where(Server.id == server_id)
        )
        server = result.scalar_one_or_none()
        
        if not server:
            return {"error": "Server not found"}
        
        health = await check_server_health(server)
        status = health.get("status", "unknown")
        
        if status == "healthy":
            server.status = ServerStatus.HEALTHY
        elif status == "degraded":
            server.status = ServerStatus.DEGRADED
        else:
            server.status = ServerStatus.OFFLINE
        
        server.last_health_check = datetime.utcnow()
        await db.commit()
        
        return {"status": "ok", "server_status": server.status.value, "health": health}
    except Exception as e:
        logger.error(f"Server check failed: {e}")
        return {"status": "error", "error": str(e)}
    finally:
        await db.close()


@celery_app.task(name="worker.tasks.health_checks.deep_server_check")
def deep_server_check(server_id: str):
    """Deep server check with comprehensive SSH metrics"""
    from worker.celery_app import run_async
    return run_async(deep_server_check_async(server_id))


async def deep_server_check_async(server_id: str):
    """Perform deep server analysis via SSH"""
    db = get_worker_session()
    try:
        result = await db.execute(
            select(Server).where(Server.id == server_id)
        )
        server = result.scalar_one_or_none()
        
        if not server:
            return {"error": "Server not found"}
        
        server_ip = str(server.ip_address) if server.ip_address else None
        if not server_ip:
            return {"error": "No IP address"}
        
        ssh_password = getattr(server, 'ssh_password', None) or os.getenv("VPN_SERVER_SSH_PASSWORD")
        
        if not ssh_password and not os.getenv("VPN_SERVER_SSH_KEY"):
            return {"error": "No SSH credentials"}
        
        checker = SSHHealthChecker(host=server_ip, username="root", password=ssh_password)
        health = await checker.check(timeout=30)
        
        return {"server_id": server_id, "server_name": server.name, "health": health}
    finally:
        await db.close()
