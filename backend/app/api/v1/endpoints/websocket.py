"""
WebSocket endpoints for real-time notifications
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from typing import Dict, Set, Optional
import json
import asyncio
from datetime import datetime
import logging

from app.core.security import decode_token
from app.core.redis import get_redis

router = APIRouter(prefix="/ws", tags=["websocket"])
logger = logging.getLogger(__name__)

# Connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {
            "alerts": set(),
            "stats": set(),
            "notifications": set(),
        }
        self.admin_connections: Dict[str, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, channel: str, admin_id: Optional[str] = None):
        await websocket.accept()
        if channel in self.active_connections:
            self.active_connections[channel].add(websocket)
        if admin_id:
            self.admin_connections[admin_id] = websocket
        logger.info(f"WebSocket connected: channel={channel}, admin={admin_id}")
    
    def disconnect(self, websocket: WebSocket, channel: str, admin_id: Optional[str] = None):
        if channel in self.active_connections:
            self.active_connections[channel].discard(websocket)
        if admin_id and admin_id in self.admin_connections:
            del self.admin_connections[admin_id]
        logger.info(f"WebSocket disconnected: channel={channel}, admin={admin_id}")
    
    async def broadcast_to_channel(self, channel: str, message: dict):
        """Broadcast message to all connections in a channel"""
        if channel not in self.active_connections:
            return
        
        dead_connections = set()
        for connection in self.active_connections[channel]:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.warning(f"Failed to send to websocket: {e}")
                dead_connections.add(connection)
        
        # Clean up dead connections
        self.active_connections[channel] -= dead_connections
    
    async def send_to_admin(self, admin_id: str, message: dict):
        """Send message to specific admin"""
        if admin_id in self.admin_connections:
            try:
                await self.admin_connections[admin_id].send_json(message)
            except Exception as e:
                logger.warning(f"Failed to send to admin {admin_id}: {e}")
                del self.admin_connections[admin_id]
    
    async def broadcast_to_all_admins(self, message: dict):
        """Broadcast to all connected admins"""
        dead_admins = []
        for admin_id, connection in self.admin_connections.items():
            try:
                await connection.send_json(message)
            except Exception:
                dead_admins.append(admin_id)
        
        for admin_id in dead_admins:
            del self.admin_connections[admin_id]


manager = ConnectionManager()


@router.websocket("/alerts")
async def websocket_alerts(
    websocket: WebSocket,
    token: str = Query(...)
):
    """WebSocket for real-time alerts"""
    # Verify token
    try:
        payload = decode_token(token)
        if not payload:
            raise ValueError("Invalid token")
        admin_id = payload.get("sub")
    except Exception as e:
        logger.warning(f"WebSocket auth failed: {e}")
        await websocket.close(code=4001, reason="Unauthorized")
        return
    
    await manager.connect(websocket, "alerts", admin_id)
    
    try:
        # Subscribe to Redis alerts channel
        redis = await get_redis()
        pubsub = redis.pubsub()
        await pubsub.subscribe("alerts:new")
        
        # Send initial message
        await websocket.send_json({
            "type": "connected",
            "channel": "alerts",
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Listen for messages
        while True:
            try:
                # Check for Redis messages
                message = await asyncio.wait_for(
                    pubsub.get_message(ignore_subscribe_messages=True),
                    timeout=1.0
                )
                if message and message.get("type") == "message":
                    data = json.loads(message["data"])
                    await websocket.send_json({
                        "type": "alert",
                        "data": data,
                        "timestamp": datetime.utcnow().isoformat()
                    })
                
                # Check for client messages (ping/pong)
                try:
                    client_msg = await asyncio.wait_for(
                        websocket.receive_text(),
                        timeout=0.1
                    )
                    if client_msg == "ping":
                        await websocket.send_text("pong")
                except asyncio.TimeoutError:
                    pass
                
            except asyncio.TimeoutError:
                # Send heartbeat
                await websocket.send_json({"type": "heartbeat"})
                
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        manager.disconnect(websocket, "alerts", admin_id)
        await pubsub.unsubscribe("alerts:new")


@router.websocket("/stats")
async def websocket_stats(
    websocket: WebSocket,
    token: str = Query(...)
):
    """WebSocket for real-time stats updates"""
    try:
        payload = decode_token(token)
        if not payload:
            raise ValueError("Invalid token")
        admin_id = payload.get("sub")
    except Exception:
        await websocket.close(code=4001, reason="Unauthorized")
        return
    
    await manager.connect(websocket, "stats", admin_id)
    
    try:
        await websocket.send_json({
            "type": "connected",
            "channel": "stats",
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Send stats updates every 30 seconds
        while True:
            try:
                # Get latest stats from Redis cache
                redis = await get_redis()
                cached_stats = await redis.get("dashboard:stats")
                
                if cached_stats:
                    await websocket.send_json({
                        "type": "stats_update",
                        "data": json.loads(cached_stats),
                        "timestamp": datetime.utcnow().isoformat()
                    })
                
                # Wait for next update or client message
                try:
                    msg = await asyncio.wait_for(
                        websocket.receive_text(),
                        timeout=30.0
                    )
                    if msg == "ping":
                        await websocket.send_text("pong")
                    elif msg == "refresh":
                        # Force refresh stats
                        await websocket.send_json({
                            "type": "stats_refreshing",
                            "timestamp": datetime.utcnow().isoformat()
                        })
                except asyncio.TimeoutError:
                    pass
                    
            except asyncio.TimeoutError:
                await websocket.send_json({"type": "heartbeat"})
                
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(websocket, "stats", admin_id)


@router.websocket("/notifications")
async def websocket_notifications(
    websocket: WebSocket,
    token: str = Query(...)
):
    """WebSocket for admin notifications"""
    try:
        payload = decode_token(token)
        if not payload:
            raise ValueError("Invalid token")
        admin_id = payload.get("sub")
    except Exception:
        await websocket.close(code=4001, reason="Unauthorized")
        return
    
    await manager.connect(websocket, "notifications", admin_id)
    
    try:
        redis = await get_redis()
        pubsub = redis.pubsub()
        await pubsub.subscribe(f"notifications:{admin_id}", "notifications:broadcast")
        
        await websocket.send_json({
            "type": "connected",
            "channel": "notifications",
            "timestamp": datetime.utcnow().isoformat()
        })
        
        while True:
            try:
                message = await asyncio.wait_for(
                    pubsub.get_message(ignore_subscribe_messages=True),
                    timeout=1.0
                )
                if message and message.get("type") == "message":
                    data = json.loads(message["data"])
                    await websocket.send_json({
                        "type": "notification",
                        "data": data,
                        "timestamp": datetime.utcnow().isoformat()
                    })
                
                try:
                    client_msg = await asyncio.wait_for(
                        websocket.receive_text(),
                        timeout=0.1
                    )
                    if client_msg == "ping":
                        await websocket.send_text("pong")
                except asyncio.TimeoutError:
                    pass
                    
            except asyncio.TimeoutError:
                await websocket.send_json({"type": "heartbeat"})
                
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(websocket, "notifications", admin_id)
        await pubsub.unsubscribe(f"notifications:{admin_id}", "notifications:broadcast")


# Helper functions to send notifications
async def send_alert_notification(alert_data: dict):
    """Send alert to all connected admins via WebSocket"""
    redis = await get_redis()
    await redis.publish("alerts:new", json.dumps(alert_data))


async def send_admin_notification(admin_id: str, notification: dict):
    """Send notification to specific admin"""
    redis = await get_redis()
    await redis.publish(f"notifications:{admin_id}", json.dumps(notification))


async def broadcast_notification(notification: dict):
    """Broadcast notification to all admins"""
    redis = await get_redis()
    await redis.publish("notifications:broadcast", json.dumps(notification))


# Export manager for use in other modules
def get_websocket_manager() -> ConnectionManager:
    return manager
