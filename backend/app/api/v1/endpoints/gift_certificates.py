"""
Gift Certificate API endpoints
"""
from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from pydantic import BaseModel
import uuid

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models import User, Plan, Payment, GiftCertificate, GiftCertificateStatus
from app.api.deps import get_current_admin

router = APIRouter()


# ============== Schemas ==============

class GiftCertificateCreate(BaseModel):
    plan_id: str
    sender_name: Optional[str] = None
    recipient_name: Optional[str] = None
    message: Optional[str] = None


class GiftCertificateRedeem(BaseModel):
    code: str


class GiftCertificateResponse(BaseModel):
    id: str
    code: str
    plan_name: str
    plan_duration_days: int
    amount: float
    status: str
    sender_name: Optional[str]
    recipient_name: Optional[str]
    message: Optional[str]
    expires_at: datetime
    created_at: datetime


class GiftCertificateAdminResponse(GiftCertificateResponse):
    buyer_telegram_id: Optional[int]
    buyer_username: Optional[str]
    recipient_telegram_id: Optional[int]
    recipient_username: Optional[str]
    redeemed_at: Optional[datetime]


# ============== Public Endpoints ==============

@router.post("/create")
async def create_gift_certificate(
    data: GiftCertificateCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a gift certificate (requires payment)"""
    # Get plan
    plan = await db.get(Plan, uuid.UUID(data.plan_id))
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    # Generate unique code
    code = GiftCertificate.generate_code()
    while True:
        existing = await db.execute(
            select(GiftCertificate).where(GiftCertificate.code == code)
        )
        if not existing.scalar_one_or_none():
            break
        code = GiftCertificate.generate_code()
    
    # Create certificate with PENDING status until payment
    certificate = GiftCertificate(
        code=code,
        buyer_id=current_user.id,
        plan_id=plan.id,
        amount=float(plan.price),
        currency=plan.currency,
        sender_name=data.sender_name or current_user.first_name,
        recipient_name=data.recipient_name,
        message=data.message,
        expires_at=datetime.utcnow() + timedelta(days=365),  # 1 год на активацию
        status=GiftCertificateStatus.PENDING  # PENDING until payment confirmed
    )
    db.add(certificate)
    await db.commit()
    await db.refresh(certificate)
    
    return {
        "certificate_id": str(certificate.id),
        "code": certificate.code,
        "amount": certificate.amount,
        "requires_payment": True,
        "payment_url": f"/api/v1/payments/gift/{certificate.id}"
    }


@router.post("/redeem")
async def redeem_gift_certificate(
    data: GiftCertificateRedeem,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Redeem a gift certificate"""
    # Find certificate
    stmt = select(GiftCertificate).where(
        and_(
            GiftCertificate.code == data.code.upper().strip(),
            GiftCertificate.status == GiftCertificateStatus.ACTIVE
        )
    )
    result = await db.execute(stmt)
    certificate = result.scalar_one_or_none()
    
    if not certificate:
        raise HTTPException(status_code=404, detail="Invalid or expired certificate code")
    
    if certificate.expires_at < datetime.utcnow():
        certificate.status = GiftCertificateStatus.EXPIRED
        await db.commit()
        raise HTTPException(status_code=400, detail="Certificate has expired")
    
    if certificate.recipient_id:
        raise HTTPException(status_code=400, detail="Certificate already redeemed")
    
    # Mark as redeemed
    certificate.recipient_id = current_user.id
    certificate.status = GiftCertificateStatus.REDEEMED
    certificate.redeemed_at = datetime.utcnow()
    
    # Create subscription for user
    from app.services.subscription_service import SubscriptionService
    sub_service = SubscriptionService(db)
    
    subscription = await sub_service.create_subscription(
        user_id=str(current_user.id),
        plan_id=str(certificate.plan_id),
        payment_id=str(certificate.payment_id) if certificate.payment_id else None
    )
    
    await db.commit()
    
    return {
        "success": True,
        "message": "Certificate redeemed successfully!",
        "subscription_id": str(subscription.id) if subscription else None,
        "plan_name": certificate.plan.name if certificate.plan else "VPN",
        "sender_name": certificate.sender_name,
        "gift_message": certificate.message
    }


@router.get("/check/{code}")
async def check_gift_certificate(
    code: str,
    db: AsyncSession = Depends(get_db)
):
    """Check if a gift certificate is valid (public)"""
    stmt = select(GiftCertificate).where(GiftCertificate.code == code.upper().strip())
    result = await db.execute(stmt)
    certificate = result.scalar_one_or_none()
    
    if not certificate:
        return {"valid": False, "message": "Certificate not found"}
    
    if certificate.status != GiftCertificateStatus.ACTIVE:
        return {"valid": False, "message": f"Certificate is {certificate.status.value}"}
    
    if certificate.expires_at < datetime.utcnow():
        return {"valid": False, "message": "Certificate has expired"}
    
    # Get plan
    plan = await db.get(Plan, certificate.plan_id)
    
    return {
        "valid": True,
        "plan_name": plan.name if plan else "VPN Subscription",
        "duration_days": plan.duration_days if plan else 30,
        "sender_name": certificate.sender_name,
        "message": certificate.message,
        "expires_at": certificate.expires_at.isoformat()
    }


@router.get("/my")
async def get_my_certificates(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get user's purchased and received gift certificates"""
    # Purchased
    purchased_stmt = select(GiftCertificate).where(
        GiftCertificate.buyer_id == current_user.id
    ).order_by(GiftCertificate.created_at.desc())
    purchased_result = await db.execute(purchased_stmt)
    purchased = purchased_result.scalars().all()
    
    # Received
    received_stmt = select(GiftCertificate).where(
        GiftCertificate.recipient_id == current_user.id
    ).order_by(GiftCertificate.redeemed_at.desc())
    received_result = await db.execute(received_stmt)
    received = received_result.scalars().all()
    
    return {
        "purchased": [
            {
                "id": str(c.id),
                "code": c.code,
                "status": c.status.value,
                "recipient_name": c.recipient_name,
                "amount": c.amount,
                "created_at": c.created_at.isoformat()
            }
            for c in purchased
        ],
        "received": [
            {
                "id": str(c.id),
                "sender_name": c.sender_name,
                "message": c.message,
                "redeemed_at": c.redeemed_at.isoformat() if c.redeemed_at else None
            }
            for c in received
        ]
    }


# ============== Admin Endpoints ==============

@router.get("/admin/list")
async def admin_list_certificates(
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """Admin: List all gift certificates"""
    stmt = select(GiftCertificate).order_by(GiftCertificate.created_at.desc())
    
    if status:
        stmt = stmt.where(GiftCertificate.status == GiftCertificateStatus(status))
    
    stmt = stmt.offset(offset).limit(limit)
    result = await db.execute(stmt)
    certificates = result.scalars().all()
    
    return {
        "certificates": [
            {
                "id": str(c.id),
                "code": c.code,
                "status": c.status.value,
                "amount": c.amount,
                "buyer_id": str(c.buyer_id) if c.buyer_id else None,
                "recipient_id": str(c.recipient_id) if c.recipient_id else None,
                "created_at": c.created_at.isoformat(),
                "redeemed_at": c.redeemed_at.isoformat() if c.redeemed_at else None
            }
            for c in certificates
        ]
    }


@router.post("/admin/create")
async def admin_create_certificate(
    data: GiftCertificateCreate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """Admin: Create a free gift certificate"""
    plan = await db.get(Plan, uuid.UUID(data.plan_id))
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    code = GiftCertificate.generate_code()
    
    certificate = GiftCertificate(
        code=code,
        plan_id=plan.id,
        amount=0,  # Free from admin
        sender_name=data.sender_name or "MetaLib VPN",
        recipient_name=data.recipient_name,
        message=data.message or "Подарок от MetaLib VPN!",
        expires_at=datetime.utcnow() + timedelta(days=365),
        status=GiftCertificateStatus.ACTIVE
    )
    db.add(certificate)
    await db.commit()
    
    return {
        "certificate_id": str(certificate.id),
        "code": certificate.code,
        "message": "Gift certificate created successfully"
    }
