"""
Server Orchestrator - server selection and management
"""
from typing import Optional, List
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from app.models import Server, ServerStatus, ManagementType
from app.core.logging import logger


class ServerOrchestrator:
    """Server orchestration and load balancing"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def select_server(
        self,
        region: Optional[str] = None,
        protocol: Optional[str] = None,
    ) -> Optional[Server]:
        """
        Select best server for new user
        
        Args:
            region: Preferred region (optional)
            protocol: VPN protocol (optional, for filtering)
        
        Returns:
            Selected server or None
        """
        # Build query for available servers
        conditions = [
            Server.is_active == True,
            Server.drain_mode == False,
            Server.status == ServerStatus.HEALTHY,
        ]
        
        if region:
            conditions.append(Server.region == region)
        
        stmt = select(Server).where(and_(*conditions))
        result = await self.db.execute(stmt)
        servers = list(result.scalars().all())
        
        if not servers:
            logger.warning(f"No available servers found (region={region})")
            return None
        
        # Filter by capacity
        available_servers = [s for s in servers if s.can_accept_users()]
        
        if not available_servers:
            logger.warning(f"No servers with capacity (region={region})")
            return None
        
        # Select least loaded server
        selected = min(available_servers, key=lambda s: s.load_percentage())
        
        logger.info(
            f"Selected server: id={selected.id}, name={selected.name}, "
            f"load={selected.load_percentage():.1f}%"
        )
        
        return selected
    
    async def increment_server_load(self, server_id: str) -> None:
        """Increment server user count"""
        server = await self.db.get(Server, server_id)
        if server:
            server.current_users += 1
            await self.db.commit()
            logger.debug(f"Server load incremented: {server.name} ({server.current_users}/{server.max_users})")
    
    async def decrement_server_load(self, server_id: str) -> None:
        """Decrement server user count"""
        server = await self.db.get(Server, server_id)
        if server:
            server.current_users = max(0, server.current_users - 1)
            await self.db.commit()
            logger.debug(f"Server load decremented: {server.name} ({server.current_users}/{server.max_users})")
    
    async def health_check(self, server_id: str) -> bool:
        """
        Perform health check on server
        
        Returns:
            True if healthy
        """
        server = await self.db.get(Server, server_id)
        
        if not server:
            return False
        
        try:
            # Check agent health
            if server.management_type == ManagementType.AGENT:
                from app.integrations.vpn.agent_client import AgentClient
                
                agent = AgentClient(
                    url=server.agent_url,
                    token=server.agent_token,
                )
                
                health = await agent.health_check()
                
                if health.get("status") == "ok":
                    server.status = ServerStatus.HEALTHY
                    server.health_check_failures = 0
                else:
                    server.status = ServerStatus.DEGRADED
                    server.health_check_failures += 1
            
            # SSH health check (simple ping)
            elif server.management_type == ManagementType.SSH:
                # TODO: Implement SSH health check
                server.status = ServerStatus.HEALTHY
                server.health_check_failures = 0
            
            server.last_health_check = datetime.utcnow()
            await self.db.commit()
            
            return server.status == ServerStatus.HEALTHY
            
        except Exception as e:
            logger.error(f"Health check failed for server {server.name}: {e}")
            
            server.health_check_failures += 1
            
            if server.health_check_failures >= 3:
                server.status = ServerStatus.OFFLINE
            else:
                server.status = ServerStatus.DEGRADED
            
            server.last_health_check = datetime.utcnow()
            await self.db.commit()
            
            return False
    
    async def drain_server(self, server_id: str) -> None:
        """Put server in drain mode (stop accepting new users)"""
        server = await self.db.get(Server, server_id)
        
        if server:
            server.drain_mode = True
            await self.db.commit()
            logger.info(f"Server {server.name} set to drain mode")
    
    async def activate_server(self, server_id: str) -> None:
        """Activate server"""
        server = await self.db.get(Server, server_id)
        
        if server:
            server.drain_mode = False
            server.is_active = True
            await self.db.commit()
            logger.info(f"Server {server.name} activated")
    
    async def get_servers_by_region(self, region: str) -> List[Server]:
        """Get all servers in region"""
        stmt = select(Server).where(Server.region == region)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
    
    async def get_all_active_servers(self) -> List[Server]:
        """Get all active servers"""
        stmt = select(Server).where(
            and_(
                Server.is_active == True,
                Server.status != ServerStatus.OFFLINE,
            )
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
