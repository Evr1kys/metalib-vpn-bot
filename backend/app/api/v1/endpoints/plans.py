"""
Plans endpoints
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from app.core.database import get_db
from app.models import Plan
from app.api.deps import verify_bot_token, get_current_admin, AdminUser

router = APIRouter()


class PlanCreateRequest(BaseModel):
    """Plan creation request"""
    name: str
    description: str | None = None
    duration_days: int
    price: float
    currency: str = "RUB"
    server_ids: list[str] | None = None  # Assigned servers, null = all servers
    bandwidth_limit: int | None = None
    features: list = []
    is_featured: bool = False
    sort_order: int = 0


class PlanUpdateRequest(BaseModel):
    """Plan update request"""
    name: str | None = None
    description: str | None = None
    duration_days: int | None = None
    price: float | None = None
    currency: str | None = None
    server_ids: list[str] | None = None
    bandwidth_limit: int | None = None
    features: list | None = None
    is_active: bool | None = None
    is_featured: bool | None = None
    sort_order: int | None = None


class PlanResponse(BaseModel):
    """Plan response"""
    id: str
    name: str
    description: str
    duration_days: int
    price: float
    currency: str
    server_ids: list[str] | None = None
    features: list
    is_featured: bool
    is_active: bool = True
    
    class Config:
        from_attributes = True


@router.get("/", response_model=List[PlanResponse])
async def get_plans(
    db: AsyncSession = Depends(get_db)
):
    """Get all active plans (public endpoint)"""
    stmt = select(Plan).where(Plan.is_active == True).order_by(Plan.sort_order, Plan.price)
    result = await db.execute(stmt)
    plans = result.scalars().all()
    
    return [
        PlanResponse(
            id=str(plan.id),
            name=plan.name,
            description=plan.description or "",
            duration_days=plan.duration_days,
            price=float(plan.price),
            currency=plan.currency,
            server_ids=[str(sid) for sid in plan.server_ids] if plan.server_ids else None,
            features=plan.features if isinstance(plan.features, list) else [],
            is_featured=plan.is_featured,
            is_active=plan.is_active,
        )
        for plan in plans
    ]


@router.get("/{plan_id}", response_model=PlanResponse, dependencies=[Depends(verify_bot_token)])
async def get_plan(
    plan_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get plan by ID"""
    plan = await db.get(Plan, plan_id)
    
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    return PlanResponse(
        id=str(plan.id),
        name=plan.name,
        description=plan.description or "",
        duration_days=plan.duration_days,
        price=float(plan.price),
        currency=plan.currency,
        server_ids=[str(sid) for sid in plan.server_ids] if plan.server_ids else None,
        features=plan.features if isinstance(plan.features, list) else [],
        is_featured=plan.is_featured,
    )


# Admin endpoints

@router.get("/admin/all", response_model=List[PlanResponse])
async def admin_get_all_plans(
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin)
):
    """Get all plans including inactive ones (admin only)"""
    stmt = select(Plan).order_by(Plan.sort_order, Plan.price)
    result = await db.execute(stmt)
    plans = result.scalars().all()
    
    return [
        PlanResponse(
            id=str(plan.id),
            name=plan.name,
            description=plan.description or "",
            duration_days=plan.duration_days,
            price=float(plan.price),
            currency=plan.currency,
            server_ids=[str(sid) for sid in plan.server_ids] if plan.server_ids else None,
            features=plan.features if isinstance(plan.features, list) else [],
            is_featured=plan.is_featured,
            is_active=plan.is_active,
        )
        for plan in plans
    ]


@router.post("/admin/", response_model=PlanResponse)
async def admin_create_plan(
    plan_data: PlanCreateRequest,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin)
):
    """Create new plan (admin only)"""
    import uuid as uuid_lib
    
    # Convert server_ids strings to UUIDs
    server_uuids = None
    if plan_data.server_ids:
        server_uuids = [uuid_lib.UUID(sid) for sid in plan_data.server_ids]
    
    plan = Plan(
        name=plan_data.name,
        description=plan_data.description,
        duration_days=plan_data.duration_days,
        price=plan_data.price,
        currency=plan_data.currency,
        server_ids=server_uuids,
        bandwidth_limit=plan_data.bandwidth_limit,
        features=plan_data.features,
        is_featured=plan_data.is_featured,
        sort_order=plan_data.sort_order,
        is_active=True,
    )
    
    db.add(plan)
    await db.commit()
    await db.refresh(plan)
    
    return PlanResponse(
        id=str(plan.id),
        name=plan.name,
        description=plan.description or "",
        duration_days=plan.duration_days,
        price=float(plan.price),
        currency=plan.currency,
        server_ids=[str(sid) for sid in plan.server_ids] if plan.server_ids else None,
        features=plan.features if isinstance(plan.features, list) else [],
        is_featured=plan.is_featured,
        is_active=plan.is_active,
    )


@router.patch("/admin/{plan_id}", response_model=PlanResponse)
async def admin_update_plan(
    plan_id: str,
    plan_data: PlanUpdateRequest,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin)
):
    """Update plan (admin only)"""
    import uuid as uuid_lib
    
    plan = await db.get(Plan, plan_id)
    
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    # Update fields
    if plan_data.name is not None:
        plan.name = plan_data.name
    if plan_data.description is not None:
        plan.description = plan_data.description
    if plan_data.duration_days is not None:
        plan.duration_days = plan_data.duration_days
    if plan_data.price is not None:
        plan.price = plan_data.price
    if plan_data.currency is not None:
        plan.currency = plan_data.currency
    if plan_data.server_ids is not None:
        plan.server_ids = [uuid_lib.UUID(sid) for sid in plan_data.server_ids] if plan_data.server_ids else None
    if plan_data.bandwidth_limit is not None:
        plan.bandwidth_limit = plan_data.bandwidth_limit
    if plan_data.features is not None:
        plan.features = plan_data.features
    if plan_data.is_active is not None:
        plan.is_active = plan_data.is_active
    if plan_data.is_featured is not None:
        plan.is_featured = plan_data.is_featured
    if plan_data.sort_order is not None:
        plan.sort_order = plan_data.sort_order
    
    await db.commit()
    await db.refresh(plan)
    
    return PlanResponse(
        id=str(plan.id),
        name=plan.name,
        description=plan.description or "",
        duration_days=plan.duration_days,
        price=float(plan.price),
        currency=plan.currency,
        server_ids=[str(sid) for sid in plan.server_ids] if plan.server_ids else None,
        features=plan.features if isinstance(plan.features, list) else [],
        is_featured=plan.is_featured,
        is_active=plan.is_active,
    )


@router.delete("/admin/{plan_id}")
async def admin_delete_plan(
    plan_id: str,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin)
):
    """Delete plan (admin only)"""
    plan = await db.get(Plan, plan_id)
    
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    # Soft delete by setting is_active to False
    plan.is_active = False
    await db.commit()
    
    return {"status": "ok", "message": "Plan deactivated"}
