from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timedelta
from app.core.database import get_db
from app.api.deps import get_current_admin
from app.models import User, Subscription, Payment, Server
from app.models.payment import PaymentStatus

router = APIRouter()

@router.get("")
async def get_stats(
    db: AsyncSession = Depends(get_db),
    admin = Depends(get_current_admin)
):
    """Get dashboard statistics"""
    
    # Total users
    total_users_query = select(func.count(User.id))
    total_users = (await db.execute(total_users_query)).scalar() or 0
    
    # Active subscriptions
    active_subs_query = select(func.count(Subscription.id)).where(
        Subscription.is_active == True
    )
    active_subscriptions = (await db.execute(active_subs_query)).scalar() or 0
    
    # Total revenue
    revenue_query = select(func.sum(Payment.amount)).where(
        Payment.status == PaymentStatus.PAID
    )
    total_revenue = (await db.execute(revenue_query)).scalar() or 0
    
    # Total servers
    servers_query = select(func.count(Server.id)).where(
        Server.is_active == True
    )
    total_servers = (await db.execute(servers_query)).scalar() or 0
    
    # Users from last month
    month_ago = datetime.utcnow() - timedelta(days=30)
    prev_users_query = select(func.count(User.id)).where(
        User.created_at < month_ago
    )
    prev_users = (await db.execute(prev_users_query)).scalar() or 0
    
    # Active subs from last month
    prev_subs_query = select(func.count(Subscription.id)).where(
        Subscription.is_active == True,
        Subscription.created_at < month_ago
    )
    prev_subs = (await db.execute(prev_subs_query)).scalar() or 0
    
    # Revenue from last month
    prev_revenue_query = select(func.sum(Payment.amount)).where(
        Payment.status == PaymentStatus.PAID,
        Payment.created_at < month_ago
    )
    prev_revenue = (await db.execute(prev_revenue_query)).scalar() or 0
    
    # Calculate growth percentages
    users_growth = 0
    if prev_users > 0:
        users_growth = ((total_users - prev_users) / prev_users) * 100
    
    subs_growth = 0
    if prev_subs > 0:
        subs_growth = ((active_subscriptions - prev_subs) / prev_subs) * 100
    
    revenue_growth = 0
    if prev_revenue > 0:
        revenue_growth = ((total_revenue - prev_revenue) / prev_revenue) * 100
    
    # Chart data for last 7 days
    chart_data = []
    for i in range(6, -1, -1):
        day = datetime.utcnow() - timedelta(days=i)
        day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        
        # New users for this day
        users_query = select(func.count(User.id)).where(
            User.created_at >= day_start,
            User.created_at < day_end
        )
        new_users = (await db.execute(users_query)).scalar() or 0
        
        # Revenue for this day
        revenue_query = select(func.sum(Payment.amount)).where(
            Payment.status == PaymentStatus.PAID,
            Payment.created_at >= day_start,
            Payment.created_at < day_end
        )
        day_revenue = (await db.execute(revenue_query)).scalar() or 0
        
        chart_data.append({
            "date": day.strftime("%d.%m"),
            "users": new_users,
            "revenue": float(day_revenue)
        })
    
    return {
        "total_users": total_users,
        "active_subscriptions": active_subscriptions,
        "total_revenue": float(total_revenue),
        "total_servers": total_servers,
        "users_growth": round(users_growth, 1),
        "subs_growth": round(subs_growth, 1),
        "revenue_growth": round(revenue_growth, 1),
        "chart_data": chart_data
    }


@router.get("/traffic")
async def get_traffic_stats(
    db: AsyncSession = Depends(get_db),
    admin = Depends(get_current_admin)
):
    """Get VPN traffic statistics from all servers"""
    import aiohttp
    import hmac
    import hashlib
    import json
    from app.core.config import settings
    
    # Get all active servers
    servers_query = select(Server).where(Server.is_active == True)
    servers = (await db.execute(servers_query)).scalars().all()
    
    API_SECRET = settings.VPN_AGENT_SECRET_KEY or "metalib-xray-secret-key-2024"
    API_PORT = 8444
    
    all_stats = []
    
    for server in servers:
        server_ip = str(server.ip_address) if hasattr(server, 'ip_address') else str(server.ip)
        
        try:
            payload = "{}"
            signature = hmac.new(API_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"http://{server_ip}:{API_PORT}/stats",
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": signature
                    },
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    result = await resp.json()
                    
                    if result.get("success"):
                        stats = result.get("stats", {})
                        all_stats.append({
                            "server_id": str(server.id),
                            "server_name": server.name,
                            "server_ip": server_ip,
                            "inbound": stats.get("inbound", {}),
                            "outbound": stats.get("outbound", {}),
                            "users": stats.get("users", {}),
                            "status": "online"
                        })
                    else:
                        all_stats.append({
                            "server_id": str(server.id),
                            "server_name": server.name,
                            "server_ip": server_ip,
                            "error": result.get("error", "Unknown error"),
                            "status": "error"
                        })
                        
        except Exception as e:
            all_stats.append({
                "server_id": str(server.id),
                "server_name": server.name,
                "server_ip": server_ip,
                "error": str(e),
                "status": "offline"
            })
    
    # Calculate totals
    total_inbound_up = sum(s.get("inbound", {}).get("uplink", 0) or 0 for s in all_stats if s.get("status") == "online")
    total_inbound_down = sum(s.get("inbound", {}).get("downlink", 0) or 0 for s in all_stats if s.get("status") == "online")
    total_outbound_up = sum(s.get("outbound", {}).get("uplink", 0) or 0 for s in all_stats if s.get("status") == "online")
    total_outbound_down = sum(s.get("outbound", {}).get("downlink", 0) or 0 for s in all_stats if s.get("status") == "online")
    
    return {
        "servers": all_stats,
        "totals": {
            "inbound_uplink": total_inbound_up,
            "inbound_downlink": total_inbound_down,
            "outbound_uplink": total_outbound_up,
            "outbound_downlink": total_outbound_down,
            "total_traffic": total_inbound_up + total_inbound_down + total_outbound_up + total_outbound_down
        }
    }


@router.get("/access-logs")
async def get_access_logs(
    server_id: str = None,
    user_email: str = None,
    limit: int = 1000,
    db: AsyncSession = Depends(get_db),
    admin = Depends(get_current_admin)
):
    """
    Get VPN access logs with domains visited by each user.
    Returns per-user traffic data with visited sites.
    """
    import aiohttp
    import hmac
    import hashlib
    import json
    from app.core.config import settings
    from app.models import VPNAccount
    
    # Get all active servers or specific server
    if server_id:
        servers_query = select(Server).where(Server.id == server_id, Server.is_active == True)
    else:
        servers_query = select(Server).where(Server.is_active == True)
    
    servers = (await db.execute(servers_query)).scalars().all()
    
    API_SECRET = settings.VPN_AGENT_SECRET_KEY or "metalib-xray-secret-key-2024"
    API_PORT = 8444
    
    all_logs = []
    all_users = {}
    
    for server in servers:
        server_ip = str(server.ip_address) if hasattr(server, 'ip_address') else str(server.ip)
        
        try:
            payload = json.dumps({"limit": limit, "user_email": user_email})
            signature = hmac.new(API_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"http://{server_ip}:{API_PORT}/access-logs",
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": signature
                    },
                    json={"limit": limit, "user_email": user_email},
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as resp:
                    result = await resp.json()
                    
                    if result.get("success"):
                        # Add server info to logs
                        server_logs = result.get("logs", [])
                        for log in server_logs:
                            log["server_name"] = server.name
                            log["server_ip"] = server_ip
                        all_logs.extend(server_logs)
                        
                        # Merge user data
                        server_users = result.get("users", {})
                        for email, user_data in server_users.items():
                            if email not in all_users:
                                all_users[email] = {
                                    "total_requests": 0,
                                    "last_seen": None,
                                    "unique_ips": [],
                                    "top_domains": [],
                                    "unique_domains_count": 0,
                                    "servers": []
                                }
                            
                            all_users[email]["total_requests"] += user_data.get("total_requests", 0)
                            all_users[email]["unique_ips"].extend(user_data.get("unique_ips", []))
                            all_users[email]["servers"].append({
                                "name": server.name,
                                "ip": server_ip
                            })
                            
                            # Keep latest last_seen
                            if user_data.get("last_seen"):
                                if not all_users[email]["last_seen"] or user_data["last_seen"] > all_users[email]["last_seen"]:
                                    all_users[email]["last_seen"] = user_data["last_seen"]
                            
                            # Merge top domains
                            existing_domains = {d["domain"]: d["count"] for d in all_users[email]["top_domains"]}
                            for domain_entry in user_data.get("top_domains", []):
                                domain = domain_entry["domain"]
                                count = domain_entry["count"]
                                existing_domains[domain] = existing_domains.get(domain, 0) + count
                            
                            all_users[email]["top_domains"] = sorted(
                                [{"domain": d, "count": c} for d, c in existing_domains.items()],
                                key=lambda x: x["count"],
                                reverse=True
                            )[:50]
                            all_users[email]["unique_domains_count"] = len(existing_domains)
                        
        except Exception as e:
            # Log error but continue with other servers
            pass
    
    # Enrich user data with Telegram info from VPN accounts
    user_emails = list(all_users.keys())
    if user_emails:
        # Get VPN accounts by username (username format: user_{telegram_id})
        vpn_query = select(VPNAccount).where(VPNAccount.username.in_(user_emails))
        vpn_accounts = (await db.execute(vpn_query)).scalars().all()
        
        # Build mapping from username to user info
        email_to_user = {}
        for vpn in vpn_accounts:
            if vpn.subscription and vpn.subscription.user:
                user = vpn.subscription.user
                email_to_user[vpn.username] = {
                    "telegram_id": user.telegram_id,
                    "username": user.username,
                    "first_name": user.first_name,
                    "uuid": str(vpn.id) if vpn.id else None,
                    "subscription_id": str(vpn.subscription_id) if vpn.subscription_id else None
                }
        
        # Add user info to the response
        for email, user_data in all_users.items():
            if email in email_to_user:
                all_users[email]["user_info"] = email_to_user[email]
            else:
                # Try to extract telegram_id from email (format: user_TELEGRAM_ID)
                if email.startswith("user_"):
                    try:
                        tg_id = int(email.replace("user_", ""))
                        all_users[email]["user_info"] = {"telegram_id": tg_id}
                    except:
                        pass
    
    # Deduplicate IPs
    for email in all_users:
        all_users[email]["unique_ips"] = list(set(all_users[email]["unique_ips"]))
    
    return {
        "logs": all_logs,
        "users": all_users,
        "total_entries": len(all_logs)
    }


@router.get("/user-traffic/{user_email}")
async def get_user_traffic_detail(
    user_email: str,
    db: AsyncSession = Depends(get_db),
    admin = Depends(get_current_admin)
):
    """
    Get detailed traffic for a specific user.
    Returns all domains visited, IPs used, and timeline.
    """
    import aiohttp
    import hmac
    import hashlib
    import json
    from app.core.config import settings
    from app.models import VPNAccount
    
    # Get all active servers
    servers_query = select(Server).where(Server.is_active == True)
    servers = (await db.execute(servers_query)).scalars().all()
    
    API_SECRET = settings.VPN_AGENT_SECRET_KEY or "metalib-xray-secret-key-2024"
    API_PORT = 8444
    
    all_logs = []
    user_data = {
        "total_requests": 0,
        "domains": {},
        "ips": set(),
        "servers": [],
        "timeline": []
    }
    
    for server in servers:
        server_ip = str(server.ip_address) if hasattr(server, 'ip_address') else str(server.ip)
        
        try:
            payload = json.dumps({"limit": 5000, "user_email": user_email})
            signature = hmac.new(API_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"http://{server_ip}:{API_PORT}/access-logs",
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": signature
                    },
                    json={"limit": 5000, "user_email": user_email},
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as resp:
                    result = await resp.json()
                    
                    if result.get("success"):
                        logs = result.get("logs", [])
                        for log in logs:
                            log["server_name"] = server.name
                            log["server_ip"] = server_ip
                            all_logs.append(log)
                            
                            # Aggregate
                            domain = log.get("domain", "unknown")
                            user_data["domains"][domain] = user_data["domains"].get(domain, 0) + 1
                            user_data["ips"].add(log.get("source_ip", ""))
                            user_data["total_requests"] += 1
                        
                        if logs:
                            user_data["servers"].append({
                                "name": server.name,
                                "ip": server_ip,
                                "requests": len(logs)
                            })
                        
        except Exception as e:
            pass
    
    # Get user info from database
    user_info = None
    if user_email.startswith("user_"):
        try:
            tg_id = int(user_email.replace("user_", ""))
            user_query = select(User).where(User.telegram_id == tg_id)
            user = (await db.execute(user_query)).scalar_one_or_none()
            
            if user:
                user_info = {
                    "telegram_id": user.telegram_id,
                    "username": user.username,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "created_at": user.created_at.isoformat() if user.created_at else None
                }
                
                # Get VPN account info by username
                vpn_query = select(VPNAccount).where(VPNAccount.username == user_email)
                vpn = (await db.execute(vpn_query)).scalar_one_or_none()
                
                if vpn:
                    user_info["uuid"] = str(vpn.id) if vpn.id else None
                    user_info["protocol"] = vpn.protocol.value if vpn.protocol else None
                    user_info["vpn_created_at"] = vpn.created_at.isoformat() if vpn.created_at else None
        except:
            pass
    
    # Sort domains by count
    top_domains = sorted(
        [{"domain": d, "count": c} for d, c in user_data["domains"].items()],
        key=lambda x: x["count"],
        reverse=True
    )
    
    return {
        "user_email": user_email,
        "user_info": user_info,
        "total_requests": user_data["total_requests"],
        "unique_ips": list(user_data["ips"]),
        "servers": user_data["servers"],
        "top_domains": top_domains[:100],
        "all_domains": top_domains,
        "logs": all_logs[-500:]  # Last 500 log entries
    }
