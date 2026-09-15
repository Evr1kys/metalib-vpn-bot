"""
Subscription Service - business logic for subscriptions
"""
from typing import Optional, List
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.models import (
    Subscription, SubscriptionStatus, Payment, User, Plan,
    VPNAccount, Device
)
from app.core.logging import logger
from app.core.telegram_logger import send_user_notification


class SubscriptionService:
    """Subscription service"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_subscription(self, user_id: str, plan_id: str) -> Subscription:
        """Create new subscription (pending until payment)"""
        subscription = Subscription(
            user_id=user_id,
            plan_id=plan_id,
            status=SubscriptionStatus.PENDING,
        )
        
        self.db.add(subscription)
        await self.db.commit()
        await self.db.refresh(subscription)
        
        logger.info(f"Subscription created: id={subscription.id}, user_id={user_id}")
        return subscription
    
    async def activate_subscription(self, payment: Payment) -> Subscription:
        """
        Activate subscription after successful payment
        
        Args:
            payment: Paid payment
        
        Returns:
            Activated subscription with VPN account
        """
        # Find or create subscription
        if payment.subscription_id:
            subscription = await self.db.get(Subscription, payment.subscription_id)
        else:
            # Create new subscription
            subscription = Subscription(
                user_id=payment.user_id,
                plan_id=payment.plan_id,
                status=SubscriptionStatus.PENDING,
            )
            self.db.add(subscription)
            await self.db.flush()
            
            # Link payment to subscription
            payment.subscription_id = subscription.id
        
        # Get plan
        plan = await self.db.get(Plan, payment.plan_id)
        
        # Activate subscription
        now = datetime.utcnow()
        subscription.status = SubscriptionStatus.ACTIVE
        subscription.started_at = now
        subscription.expires_at = now + timedelta(days=plan.duration_days)
        
        await self.db.commit()
        await self.db.refresh(subscription)
        
        logger.info(f"Subscription activated: id={subscription.id}, expires_at={subscription.expires_at}")
        
        # Provision VPN access immediately
        from app.services.xray_service import XrayService
        from sqlalchemy import select as sql_select
        from app.models import Server
        
        # Get available server (first active server for now)
        server_stmt = sql_select(Server).where(Server.is_active == True).limit(1)
        server_result = await self.db.execute(server_stmt)
        server = server_result.scalars().first()
        
        if server:
            xray_service = XrayService(self.db)
            try:
                user = await self.db.get(User, subscription.user_id)
                vpn_account = await xray_service.generate_vless_account(
                    subscription_id=str(subscription.id),
                    server_id=str(server.id),
                    email=f"user_{user.telegram_id}" if user else None
                )
                subscription.server_id = server.id
                await self.db.commit()
                logger.info(f"VPN account provisioned: {vpn_account.id}")
            except Exception as e:
                logger.error(f"Failed to provision VPN: {e}")
        else:
            logger.warning("No active server found for VPN provisioning")
        
        # Process referral bonus if user was referred
        await self._process_referral_bonus(subscription.user_id)
        
        # Send payment receipt to user with inline keyboard
        try:
            user = await self.db.get(User, subscription.user_id)
            if user and user.telegram_id:
                expires_date = subscription.expires_at.strftime("%d.%m.%Y")
                started_date = subscription.started_at.strftime("%d.%m.%Y %H:%M")
                
                # Get plan and payment info
                plan_name = plan.name if plan else "VPN подписка"
                plan_duration = plan.duration_days if plan else 30
                payment_amount = float(payment.amount) if payment else 0
                payment_currency = payment.currency if payment else "RUB"
                
                receipt_text = f"""🎉 <b>Поздравляем с покупкой!</b>

━━━━━━━━━━━━━━━━━━━━━━
✅ <b>Оплата прошла успешно</b>
━━━━━━━━━━━━━━━━━━━━━━

💎 <b>Тариф:</b> {plan_name}
⏱ <b>Период:</b> {plan_duration} дней
💰 <b>Сумма:</b> {payment_amount:.0f} ₽

📅 <b>Дата оплаты:</b> {started_date}
📅 <b>Активна до:</b> {expires_date}

━━━━━━━━━━━━━━━━━━━━━━

🚀 Нажмите кнопку ниже, чтобы
получить VPN ключ и начать!

Спасибо за покупку! 💜"""
                
                # Inline keyboard with "Моя подписка" button
                keyboard = {
                    "inline_keyboard": [
                        [{"text": "🔑 Получить VPN ключ", "callback_data": "my_vpn"}],
                        [{"text": "📊 Моя подписка", "callback_data": "my_subscription"}],
                        [{"text": "🏠 Главное меню", "callback_data": "back_to_main"}]
                    ]
                }
                
                await send_user_notification(user.telegram_id, receipt_text, reply_markup=keyboard)
                logger.info(f"Payment receipt sent to user {user.telegram_id}")
        except Exception as e:
            logger.warning(f"Failed to send payment receipt: {e}")
        
        return subscription
    
    async def renew_subscription(self, subscription_id: str) -> Payment:
        """Renew subscription (create new payment)"""
        subscription = await self.db.get(Subscription, subscription_id)
        
        if not subscription:
            raise ValueError("Subscription not found")
        
        # Create payment for renewal
        from app.services.payment_service import PaymentService
        payment_service = PaymentService(self.db)
        
        payment = await payment_service.create_payment(
            user_id=subscription.user_id,
            plan_id=subscription.plan_id,
        )
        
        logger.info(f"Subscription renewal initiated: subscription_id={subscription_id}")
        return payment
    
    async def cancel_subscription(self, subscription_id: str) -> None:
        """Cancel subscription"""
        subscription = await self.db.get(Subscription, subscription_id)
        
        if not subscription:
            raise ValueError("Subscription not found")
        
        subscription.status = SubscriptionStatus.CANCELLED
        subscription.auto_renew = False
        
        # Revoke VPN access
        from app.services.vpn_service import VPNService
        vpn_service = VPNService(self.db)
        
        for vpn_account in subscription.vpn_accounts:
            await vpn_service.revoke_access(vpn_account.id)
        
        await self.db.commit()
        logger.info(f"Subscription cancelled: id={subscription_id}")
    
    async def check_expiring_subscriptions(self, days: int = 3) -> List[Subscription]:
        """
        Find subscriptions expiring in N days
        
        Args:
            days: Number of days until expiry
        
        Returns:
            List of expiring subscriptions
        """
        target_date = datetime.utcnow() + timedelta(days=days)
        next_day = target_date + timedelta(days=1)
        
        stmt = select(Subscription).where(
            and_(
                Subscription.status == SubscriptionStatus.ACTIVE,
                Subscription.expires_at >= target_date,
                Subscription.expires_at < next_day,
            )
        )
        
        result = await self.db.execute(stmt)
        subscriptions = result.scalars().all()
        
        logger.info(f"Found {len(subscriptions)} subscriptions expiring in {days} days")
        return list(subscriptions)
    
    async def expire_subscriptions(self) -> int:
        """
        Expire subscriptions that have passed expiry date
        
        Returns:
            Number of expired subscriptions
        """
        stmt = select(Subscription).where(
            and_(
                Subscription.status == SubscriptionStatus.ACTIVE,
                Subscription.expires_at < datetime.utcnow(),
            )
        )
        
        result = await self.db.execute(stmt)
        subscriptions = result.scalars().all()
        
        count = 0
        for subscription in subscriptions:
            subscription.status = SubscriptionStatus.EXPIRED
            
            # Revoke VPN access
            from app.services.vpn_service import VPNService
            vpn_service = VPNService(self.db)
            
            for vpn_account in subscription.vpn_accounts:
                await vpn_service.revoke_access(vpn_account.id)
            
            count += 1
        
        await self.db.commit()
        logger.info(f"Expired {count} subscriptions")
        
        return count
    
    async def get_active_subscription(self, user_id: str) -> Optional[Subscription]:
        """Get user's active subscription"""
        stmt = select(Subscription).where(
            and_(
                Subscription.user_id == user_id,
                Subscription.status == SubscriptionStatus.ACTIVE,
            )
        )
        
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _process_referral_bonus(self, user_id: str) -> None:
        """
        Process referral bonus when user makes first purchase.
        Adds bonus days to referrer's active subscription.
        """
        from app.models.referral import Referral, ReferralStatus
        from app.api.v1.endpoints.admin import _system_settings
        from datetime import datetime
        
        # Check if referral system is enabled
        if not _system_settings.get("referrals_enabled", True):
            return
        
        BONUS_DAYS = _system_settings.get("referral_bonus_days", 3)  # Configurable bonus days
        
        try:
            # Find pending referral for this user (referred user)
            stmt = select(Referral).where(
                and_(
                    Referral.referred_id == user_id,
                    Referral.status == ReferralStatus.PENDING
                )
            )
            result = await self.db.execute(stmt)
            referral = result.scalar_one_or_none()
            
            if not referral:
                return  # User has no referrer or already processed
            
            # Get referrer's active subscription
            referrer_sub_stmt = select(Subscription).where(
                and_(
                    Subscription.user_id == referral.referrer_id,
                    Subscription.status == SubscriptionStatus.ACTIVE
                )
            )
            referrer_sub_result = await self.db.execute(referrer_sub_stmt)
            referrer_subscription = referrer_sub_result.scalar_one_or_none()
            
            if not referrer_subscription:
                logger.info(f"Referrer {referral.referrer_id} has no active subscription, skipping bonus")
                return
            
            # Add bonus days to referrer's subscription
            referrer_subscription.expires_at = referrer_subscription.expires_at + timedelta(days=BONUS_DAYS)
            
            # Update referral status
            referral.status = ReferralStatus.COMPLETED
            referral.bonus_days = BONUS_DAYS
            referral.rewarded_at = datetime.utcnow()
            
            await self.db.commit()
            
            # Notify referrer
            referrer = await self.db.get(User, referral.referrer_id)
            if referrer and referrer.telegram_id:
                new_expires = referrer_subscription.expires_at.strftime("%d.%m.%Y")
                message = f"""🎉 <b>Реферальный бонус!</b>

Ваш друг оформил подписку. 
Вам начислено <b>+{BONUS_DAYS} дней</b> к подписке!

📅 Подписка активна до: <b>{new_expires}</b>

Продолжайте приглашать друзей и получайте бонусы!"""
                await send_user_notification(referrer.telegram_id, message)
            
            logger.info(f"Referral bonus granted: +{BONUS_DAYS} days to user {referral.referrer_id}")
            
        except Exception as e:
            logger.error(f"Error processing referral bonus: {e}")
