"""
Plan Management API endpoints
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from decimal import Decimal

from app.api.deps import get_db, get_current_admin
from app.models import AdminUser, Plan

router = APIRouter()


class PlanCreate(BaseModel):
    """Plan create request"""
    name: str
    description: Optional[str] = None
    duration_days: int
    price: float
    currency: str = "RUB"
    max_devices: int = 1
    bandwidth_limit: Optional[int] = None
    features: list = []
    is_active: bool = True
    is_featured: bool = False
    sort_order: int = 0


class PlanUpdate(BaseModel):
    """Plan update request"""
    name: Optional[str] = None
    description: Optional[str] = None
    duration_days: Optional[int] = None
    price: Optional[float] = None
    max_devices: Optional[int] = None
    bandwidth_limit: Optional[int] = None
    features: Optional[list] = None
    is_active: Optional[bool] = None
    is_featured: Optional[bool] = None
    sort_order: Optional[int] = None


class PlanResponse(BaseModel):
    """Plan response"""
    id: str
    name: str
    description: Optional[str]
    duration_days: int
    price: str
    currency: str
    max_devices: int
    bandwidth_limit: Optional[int]
    features: list
    is_active: bool
    is_featured: bool
    sort_order: int
    created_at: str


@router.post("", response_model=PlanResponse)
async def create_plan(
    plan_data: PlanCreate,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin)
):
    """Create new plan"""
    # Ensure features is a list
    features = plan_data.features if isinstance(plan_data.features, list) else []
    
    plan = Plan(
        name=plan_data.name,
        description=plan_data.description,
        duration_days=plan_data.duration_days,
        price=Decimal(str(plan_data.price)),
        currency=plan_data.currency,
        max_devices=plan_data.max_devices,
        bandwidth_limit=plan_data.bandwidth_limit,
        features=features,
        is_active=plan_data.is_active,
        is_featured=plan_data.is_featured,
        sort_order=plan_data.sort_order
    )
    
    db.add(plan)
    await db.commit()
    await db.refresh(plan)
    
    return PlanResponse(
        id=str(plan.id),
        name=plan.name,
        description=plan.description,
        duration_days=plan.duration_days,
        price=str(plan.price),
        currency=plan.currency,
        max_devices=plan.max_devices,
        bandwidth_limit=plan.bandwidth_limit,
        features=plan.features,
        is_active=plan.is_active,
        is_featured=plan.is_featured,
        sort_order=plan.sort_order,
        created_at=plan.created_at.isoformat()
    )


@router.get("", response_model=List[PlanResponse])
async def list_plans(
    skip: int = 0,
    limit: int = 100,
    active_only: bool = False,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin)
):
    """List all plans"""
    stmt = select(Plan).offset(skip).limit(limit).order_by(Plan.sort_order, Plan.created_at.desc())
    
    if active_only:
        stmt = stmt.where(Plan.is_active == True)
    
    result = await db.execute(stmt)
    plans = result.scalars().all()
    
    return [
        PlanResponse(
            id=str(p.id),
            name=p.name,
            description=p.description,
            duration_days=p.duration_days,
            price=str(p.price),
            currency=p.currency,
            max_devices=p.max_devices,
            bandwidth_limit=p.bandwidth_limit,
            features=p.features,
            is_active=p.is_active,
            is_featured=p.is_featured,
            sort_order=p.sort_order,
            created_at=p.created_at.isoformat()
        )
        for p in plans
    ]


@router.get("/{plan_id}", response_model=PlanResponse)
async def get_plan(
    plan_id: str,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin)
):
    """Get plan by ID"""
    plan = await db.get(Plan, plan_id)
    
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    return PlanResponse(
        id=str(plan.id),
        name=plan.name,
        description=plan.description,
        duration_days=plan.duration_days,
        price=str(plan.price),
        currency=plan.currency,
        max_devices=plan.max_devices,
        bandwidth_limit=plan.bandwidth_limit,
        features=plan.features,
        is_active=plan.is_active,
        is_featured=plan.is_featured,
        sort_order=plan.sort_order,
        created_at=plan.created_at.isoformat()
    )


@router.put("/{plan_id}", response_model=PlanResponse)
async def update_plan(
    plan_id: str,
    plan_data: PlanUpdate,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin)
):
    """Update plan"""
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
        plan.price = Decimal(str(plan_data.price))
    if plan_data.max_devices is not None:
        plan.max_devices = plan_data.max_devices
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
        description=plan.description,
        duration_days=plan.duration_days,
        price=str(plan.price),
        currency=plan.currency,
        max_devices=plan.max_devices,
        bandwidth_limit=plan.bandwidth_limit,
        features=plan.features,
        is_active=plan.is_active,
        is_featured=plan.is_featured,
        sort_order=plan.sort_order,
        created_at=plan.created_at.isoformat()
    )


@router.delete("/{plan_id}")
async def delete_plan(
    plan_id: str,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin)
):
    """Delete plan"""
    plan = await db.get(Plan, plan_id)
    
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    # Check if plan has active subscriptions
    if plan.subscriptions:
        active_count = sum(1 for s in plan.subscriptions if s.status == "active")
        if active_count > 0:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot delete plan with {active_count} active subscriptions. Deactivate it instead."
            )
    
    await db.delete(plan)
    await db.commit()
    
    return {"success": True, "message": "Plan deleted"}
