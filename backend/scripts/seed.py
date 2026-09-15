"""
Seed database with initial data
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import AsyncSessionLocal
from app.core.security import get_password_hash
from app.models.plan import Plan
from app.models.admin import AdminUser, AdminRole
from loguru import logger


async def seed_plans(db: AsyncSession):
    """Seed subscription plans"""
    plans = [
        Plan(
            name="Базовый",
            description="Идеален для одного устройства",
            duration_days=30,
            price=199,
            currency="RUB",
            max_devices=1,
            traffic_limit_gb=None,  # Unlimited
            speed_limit_mbps=None,  # Unlimited
            is_active=True,
            sort_order=1
        ),
        Plan(
            name="Стандарт",
            description="Для всех ваших устройств",
            duration_days=30,
            price=349,
            currency="RUB",
            max_devices=3,
            traffic_limit_gb=None,
            speed_limit_mbps=None,
            is_active=True,
            sort_order=2
        ),
        Plan(
            name="Премиум",
            description="Максимальная свобода",
            duration_days=30,
            price=499,
            currency="RUB",
            max_devices=5,
            traffic_limit_gb=None,
            speed_limit_mbps=None,
            is_active=True,
            sort_order=3
        ),
        Plan(
            name="Базовый (3 мес)",
            description="Выгодно на 3 месяца",
            duration_days=90,
            price=499,
            currency="RUB",
            max_devices=1,
            traffic_limit_gb=None,
            speed_limit_mbps=None,
            is_active=True,
            sort_order=4
        ),
        Plan(
            name="Стандарт (3 мес)",
            description="Выгодно на 3 месяца",
            duration_days=90,
            price=899,
            currency="RUB",
            max_devices=3,
            traffic_limit_gb=None,
            speed_limit_mbps=None,
            is_active=True,
            sort_order=5
        ),
        Plan(
            name="Премиум (Год)",
            description="Максимальная выгода - год подключения",
            duration_days=365,
            price=4999,
            currency="RUB",
            max_devices=5,
            traffic_limit_gb=None,
            speed_limit_mbps=None,
            is_active=True,
            sort_order=6
        ),
    ]
    
    for plan in plans:
        db.add(plan)
    
    await db.commit()
    logger.info(f"Created {len(plans)} subscription plans")


async def seed_admin_user(db: AsyncSession):
    """Create default admin user"""
    admin = AdminUser(
        username="admin",
        email="admin@metalibvpn.com",
        password_hash=get_password_hash("admin123"),  # Change in production!
        full_name="Administrator",
        role=AdminRole.SUPER_ADMIN,
        is_active=True
    )
    
    db.add(admin)
    await db.commit()
    
    logger.info("Created default admin user (username: admin, password: admin123)")


async def main():
    """Main seeding function"""
    logger.info("Starting database seeding...")
    
    async with AsyncSessionLocal() as db:
        # Seed plans
        await seed_plans(db)
        
        # Seed admin user
        await seed_admin_user(db)
    
    logger.info("Database seeding completed!")


if __name__ == "__main__":
    asyncio.run(main())
