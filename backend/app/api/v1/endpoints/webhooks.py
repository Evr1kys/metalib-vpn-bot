"""
Webhook endpoints for payment processing
"""
from fastapi import APIRouter, Request, HTTPException, status, Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.database import get_db
from app.core.config import settings
from app.core.logging import logger
from app.services.payment_service import PaymentService
from app.integrations.platega import platega_client

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


def get_client_ip(request: Request) -> str:
    """Get real client IP from X-Forwarded-For or direct connection"""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@router.post("/platega")
@limiter.limit("100/minute")
async def platega_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
    x_signature: str = Header(None, alias="X-Signature"),
):
    """
    Platega payment webhook
    
    Docs: https://docs.platega.io/
    
    Webhook payload:
    {
        "merchant_id": "123",
        "payment_id": "abc123",
        "order_id": "order_123",
        "amount": 1000.00,
        "currency": "RUB",
        "status": "success",  # success, failed, pending
        "paid_at": "2026-01-07T12:00:00Z"
    }
    
    Security:
    - X-Signature header verification
    - Idempotency via payment_id
    """
    # Parse webhook data
    try:
        # Security: Verify source IP if configured
        client_ip = get_client_ip(request)
        allowed_ips = settings.platega_webhook_ips
        
        if allowed_ips and client_ip not in allowed_ips:
            logger.warning(f"Webhook from unauthorized IP: {client_ip}, allowed: {allowed_ips}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Unauthorized source IP"
            )
        
        data = await request.json()
        logger.info(f"Platega webhook raw data: {data}")
        
        # Platega sends data in different format
        # Try multiple field names
        payment_id = data.get("payment_id") or data.get("transactionId") or data.get("id")
        order_id = data.get("order_id") or data.get("orderId")
        
        # Platega sends payload as string with order_id inside
        payload = data.get("payload")
        if payload and isinstance(payload, str):
            try:
                import json
                payload_data = json.loads(payload)
                order_id = order_id or payload_data.get("order_id")
            except:
                pass
        elif payload and isinstance(payload, dict):
            order_id = order_id or payload.get("order_id")
        
        amount = data.get("amount") or data.get("paymentDetails", {}).get("amount")
        currency = data.get("currency") or data.get("paymentDetails", {}).get("currency") or "RUB"
        status_value = data.get("status") or data.get("state") or "unknown"
        merchant_id = data.get("merchant_id") or data.get("merchantId")
        
        logger.info(f"Platega webhook parsed: payment_id={payment_id}, order_id={order_id}, status={status_value}")
    
    except Exception as e:
        logger.error(f"Failed to parse webhook JSON: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON"
        )
    
    # Verify signature (required for security)
    # In production, signature MUST be verified
    if x_signature:
        if not platega_client.verify_webhook_signature(data, x_signature):
            logger.warning(f"Invalid webhook signature for payment_id={payment_id}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid signature"
            )
    elif settings.environment == "production":
        # In production, reject unsigned webhooks for security
        logger.error(f"Rejected webhook without signature from IP {client_ip} for payment_id={payment_id}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Signature required"
        )
    else:
        # In development, log warning but allow
        logger.warning(f"Webhook without signature from IP {client_ip} for payment_id={payment_id} (dev mode)")
    
    # Process webhook
    payment_service = PaymentService(db)
    
    try:
        # Map Platega status to our status
        payment_status_map = {
            "success": "paid",
            "paid": "paid",
            "completed": "paid",
            "confirmed": "paid",  # Platega sends CONFIRMED
            "failed": "failed",
            "canceled": "failed",
            "cancelled": "failed",
            "pending": "pending"
        }
        
        internal_status = payment_status_map.get(status_value.lower(), "pending")
        
        # Handle payment confirmation
        if internal_status == "paid":
            success = await payment_service.confirm_payment_by_external_id(
                external_id=payment_id,
                transaction_data={
                    "payment_id": payment_id,
                    "amount": amount,
                    "currency": currency,
                    "status": status_value
                }
            )
            
            if not success:
                logger.error(f"Payment confirmation failed: payment_id={payment_id}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Processing failed"
                )
        
        logger.info(f"Webhook processed successfully: payment_id={payment_id}, status={internal_status}")
        return {"status": "ok", "message": "Webhook processed"}
    
    except Exception as e:
        logger.error(f"Webhook processing error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/platega/test")
async def test_platega_webhook():
    """Test endpoint (only in debug mode)"""
    if not settings.debug:
        raise HTTPException(status_code=404)
    
    return {
        "message": "Platega webhook endpoint is working",
        "url": f"{settings.api_base_url}/api/v1/webhooks/platega",
    }
