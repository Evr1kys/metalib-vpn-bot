"""
Payment Service - business logic for payments
"""
from typing import Optional, Dict, Any
from decimal import Decimal
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models import Payment, PaymentStatus, User, Plan, Subscription, PromoCode
from app.integrations.platega import platega_client
from app.core.logging import logger
from app.core.redis import acquire_lock, release_lock
from app.core.config import settings


class PaymentService:
    """Payment service"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.platega = platega_client
    
    async def create_payment(
        self,
        user_id: str,
        plan_id: str,
        promo_code: Optional[str] = None,
    ) -> Payment:
        """
        Create a new payment
        
        Args:
            user_id: User UUID
            plan_id: Plan UUID
            promo_code: Optional promo code
        
        Returns:
            Created payment
        """
        # Get user and plan
        user = await self.db.get(User, user_id)
        plan = await self.db.get(Plan, plan_id)
        
        if not user:
            raise ValueError("User not found")
        
        if not plan or not plan.is_active:
            raise ValueError("Plan not found or inactive")
        
        # Calculate amount
        original_amount = plan.price
        discount_amount = Decimal(0)
        promo_code_obj = None
        
        if promo_code:
            promo_code_obj = await self._validate_promo_code(promo_code, user_id, plan_id, original_amount)
            if promo_code_obj:
                discount_amount = promo_code_obj.calculate_discount(float(original_amount))
        
        final_amount = original_amount - discount_amount
        
        # Create payment record
        payment = Payment(
            user_id=user_id,
            plan_id=plan_id,
            promo_code_id=promo_code_obj.id if promo_code_obj else None,
            amount=final_amount,
            original_amount=original_amount,
            discount_amount=discount_amount,
            currency=plan.currency,
            status=PaymentStatus.PENDING,
        )
        
        self.db.add(payment)
        await self.db.flush()  # Get payment.id
        
        # Create payment in Platega
        try:
            platega_response = await self.platega.create_payment(
                amount=final_amount,
                order_id=str(payment.id),
                description=f"VPN подписка: {plan.name} ({plan.duration_days} дней)",
                user_email=user.username if hasattr(user, 'email') else None,
                success_url="https://t.me/metalibvpn_bot?start=payment_success",
                fail_url="https://t.me/metalibvpn_bot?start=payment_failed",
                callback_url=f"{settings.api_base_url}/api/v1/webhooks/platega"
            )
            
            if not platega_response.get("success"):
                raise Exception(f"Platega error: {platega_response.get('error')}")
            
            # Update payment with Platega data
            payment.external_id = platega_response.get("payment_id")
            payment.payment_url = platega_response.get("payment_url")
            payment.payment_metadata = platega_response
            
            await self.db.commit()
            await self.db.refresh(payment)
            
            logger.info(f"Payment created: id={payment.id}, external_id={payment.external_id}")
            
            return payment
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to create payment: {e}")
            raise
    
    async def confirm_payment_by_external_id(
        self,
        external_id: str,
        transaction_data: Dict[str, Any]
    ) -> bool:
        """
        Confirm payment by external payment ID
        
        Args:
            external_id: Platega payment ID
            transaction_data: Transaction details from webhook
        
        Returns:
            True if successful
        """
        # Idempotency lock
        lock_key = f"payment:confirm:{external_id}"
        if not await acquire_lock(lock_key, timeout=60):
            logger.warning(f"Payment confirmation already processing: {external_id}")
            return True
        
        try:
            # Find payment by external_id
            stmt = select(Payment).where(Payment.external_id == external_id)
            result = await self.db.execute(stmt)
            payment = result.scalar_one_or_none()
            
            if not payment:
                logger.error(f"Payment not found for external_id: {external_id}")
                return False
            
            # Check if already paid
            if payment.status == PaymentStatus.PAID:
                logger.info(f"Payment already confirmed: {payment.id}")
                return True
            
            # Update payment status
            payment.status = PaymentStatus.PAID
            payment.paid_at = datetime.utcnow()
            payment.payment_metadata = {
                **(payment.payment_metadata or {}),
                "transaction": transaction_data
            }
            
            await self.db.commit()
            
            # Activate subscription
            from app.services.subscription_service import SubscriptionService
            subscription_service = SubscriptionService(self.db)
            await subscription_service.activate_subscription(payment)
            
            logger.info(f"Payment confirmed: {payment.id}, external_id={external_id}")
            return True
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Payment confirmation error: {e}")
            return False
        
        finally:
            await release_lock(lock_key)
    
    async def handle_webhook(self, webhook_data: Dict[str, Any]) -> bool:
        """
        Handle payment webhook from Platega
        
        Args:
            webhook_data: Parsed webhook data
        
        Returns:
            True if processed successfully
        """
        event_type = webhook_data.get("event_type")
        payment_id = webhook_data.get("payment_id")
        order_id = webhook_data.get("order_id")
        
        logger.info(f"Processing webhook: event={event_type}, payment_id={payment_id}, order_id={order_id}")
        
        # Idempotency lock
        lock_key = f"webhook:{payment_id}"
        if not await acquire_lock(lock_key, timeout=60):
            logger.warning(f"Webhook already processing: {payment_id}")
            return True  # Already processing
        
        try:
            # Find payment by external_id or id
            stmt = select(Payment).where(
                (Payment.external_id == payment_id) | (Payment.id == order_id)
            )
            result = await self.db.execute(stmt)
            payment = result.scalar_one_or_none()
            
            if not payment:
                logger.error(f"Payment not found: {payment_id}")
                return False
            
            # Handle different event types
            if event_type == "payment.paid":
                await self._handle_payment_paid(payment, webhook_data)
            
            elif event_type == "payment.failed":
                await self._handle_payment_failed(payment, webhook_data)
            
            elif event_type == "payment.refunded":
                await self._handle_payment_refunded(payment, webhook_data)
            
            elif event_type == "payment.chargeback":
                await self._handle_payment_chargeback(payment, webhook_data)
            
            else:
                logger.warning(f"Unknown event type: {event_type}")
            
            await self.db.commit()
            return True
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Webhook processing error: {e}")
            return False
        
        finally:
            await release_lock(lock_key)
    
    async def _handle_payment_paid(self, payment: Payment, webhook_data: Dict[str, Any]):
        """Handle successful payment"""
        if payment.status == PaymentStatus.PAID:
            logger.info(f"Payment already paid: {payment.id}")
            return
        
        payment.status = PaymentStatus.PAID
        payment.paid_at = datetime.utcnow()
        payment.payment_method = webhook_data.get("payment_method")
        payment.payment_metadata = {**payment.payment_metadata, **webhook_data.get("raw_data", {})}
        
        # Activate subscription
        from app.services.subscription_service import SubscriptionService
        subscription_service = SubscriptionService(self.db)
        await subscription_service.activate_subscription(payment)
        
        logger.info(f"Payment paid: {payment.id}")
    
    async def _handle_payment_failed(self, payment: Payment, webhook_data: Dict[str, Any]):
        """Handle failed payment"""
        payment.status = PaymentStatus.FAILED
        payment.payment_metadata = {**payment.payment_metadata, **webhook_data.get("raw_data", {})}
        
        logger.info(f"Payment failed: {payment.id}")
    
    async def _handle_payment_refunded(self, payment: Payment, webhook_data: Dict[str, Any]):
        """Handle refunded payment"""
        payment.status = PaymentStatus.REFUNDED
        payment.refunded_at = datetime.utcnow()
        payment.payment_metadata = {**payment.payment_metadata, **webhook_data.get("raw_data", {})}
        
        # Cancel subscription if active
        if payment.subscription_id:
            subscription = await self.db.get(Subscription, payment.subscription_id)
            if subscription:
                from app.services.subscription_service import SubscriptionService
                subscription_service = SubscriptionService(self.db)
                await subscription_service.cancel_subscription(subscription.id)
        
        logger.info(f"Payment refunded: {payment.id}")
    
    async def _handle_payment_chargeback(self, payment: Payment, webhook_data: Dict[str, Any]):
        """Handle chargeback"""
        payment.status = PaymentStatus.CHARGEBACK
        payment.payment_metadata = {**payment.payment_metadata, **webhook_data.get("raw_data", {})}
        
        # Suspend subscription
        if payment.subscription_id:
            subscription = await self.db.get(Subscription, payment.subscription_id)
            if subscription:
                from app.models import SubscriptionStatus
                subscription.status = SubscriptionStatus.SUSPENDED
        
        logger.warning(f"Payment chargeback: {payment.id}")
    
    async def _validate_promo_code(
        self,
        code: str,
        user_id: str,
        plan_id: str,
        amount: Decimal
    ) -> Optional[PromoCode]:
        """Validate promo code"""
        stmt = select(PromoCode).where(PromoCode.code == code.upper())
        result = await self.db.execute(stmt)
        promo = result.scalar_one_or_none()
        
        if not promo or not promo.is_valid():
            return None
        
        # Check plan restriction
        if promo.plan_ids and plan_id not in [str(pid) for pid in promo.plan_ids]:
            return None
        
        # Check minimum amount
        if promo.min_purchase_amount and amount < promo.min_purchase_amount:
            return None
        
        # Check user usage limit
        from app.models import PromoCodeUse
        stmt = select(PromoCodeUse).where(
            PromoCodeUse.promo_code_id == promo.id,
            PromoCodeUse.user_id == user_id
        )
        result = await self.db.execute(stmt)
        existing_uses = len(result.scalars().all())
        
        if existing_uses >= promo.max_uses_per_user:
            return None
        
        return promo
