"""
Script to create admin user
Usage: python scripts/create_admin.py <telegram_id>
"""
import asyncio
import sys
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models import User, AdminUser
from app.core.security import get_password_hash


async def create_admin_from_user(telegram_id: int):
    """Create admin user from existing telegram user"""
    async with AsyncSessionLocal() as db:
        # Find user by telegram_id
        stmt = select(User).where(User.telegram_id == telegram_id)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            print(f"❌ User with telegram_id {telegram_id} not found")
            print("💡 User must first interact with the bot to be registered")
            return False
        
        # Check if admin already exists
        stmt = select(AdminUser).where(AdminUser.telegram_id == telegram_id)
        result = await db.execute(stmt)
        existing_admin = result.scalar_one_or_none()
        
        if existing_admin:
            print(f"⚠️  Admin already exists for telegram_id {telegram_id}")
            print(f"   Username: {existing_admin.username}")
            print(f"   Active: {existing_admin.is_active}")
            return True
        
        # Create admin
        admin = AdminUser(
            telegram_id=telegram_id,
            username=user.username or f"user_{telegram_id}",
            password_hash=get_password_hash("admin123"),  # Default password
            role="superadmin",
            is_active=True
        )
        
        db.add(admin)
        await db.commit()
        await db.refresh(admin)
        
        print("✅ Admin created successfully!")
        print(f"   Telegram ID: {telegram_id}")
        print(f"   Username: {admin.username}")
        print(f"   Role: {admin.role}")
        print(f"   Default Password: admin123")
        print(f"\n🔐 Please change the password immediately after first login!")
        
        return True


async def list_admins():
    """List all admin users"""
    async with AsyncSessionLocal() as db:
        stmt = select(AdminUser)
        result = await db.execute(stmt)
        admins = result.scalars().all()
        
        if not admins:
            print("No admins found")
            return
        
        print("\n📋 Admin users:")
        print("-" * 80)
        for admin in admins:
            status = "✅ Active" if admin.is_active else "❌ Inactive"
            print(f"ID: {admin.id}")
            print(f"   Telegram ID: {admin.telegram_id}")
            print(f"   Username: {admin.username}")
            print(f"   Role: {admin.role}")
            print(f"   Status: {status}")
            print(f"   Created: {admin.created_at}")
            print("-" * 80)


async def remove_admin(telegram_id: int):
    """Remove admin privileges"""
    async with AsyncSessionLocal() as db:
        stmt = select(AdminUser).where(AdminUser.telegram_id == telegram_id)
        result = await db.execute(stmt)
        admin = result.scalar_one_or_none()
        
        if not admin:
            print(f"❌ Admin with telegram_id {telegram_id} not found")
            return False
        
        await db.delete(admin)
        await db.commit()
        
        print(f"✅ Admin privileges removed for telegram_id {telegram_id}")
        return True


def print_usage():
    """Print usage instructions"""
    print("""
MetaLib VPN - Admin Management Script

Usage:
    python scripts/create_admin.py <telegram_id>           # Create admin
    python scripts/create_admin.py list                    # List all admins
    python scripts/create_admin.py remove <telegram_id>    # Remove admin

Examples:
    python scripts/create_admin.py 123456789
    python scripts/create_admin.py list
    python scripts/create_admin.py remove 123456789

Note: User must first interact with the bot before being promoted to admin.
""")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "list":
        asyncio.run(list_admins())
    elif command == "remove":
        if len(sys.argv) < 3:
            print("❌ Error: telegram_id required for remove command")
            print_usage()
            sys.exit(1)
        try:
            telegram_id = int(sys.argv[2])
            asyncio.run(remove_admin(telegram_id))
        except ValueError:
            print("❌ Error: telegram_id must be a number")
            sys.exit(1)
    else:
        # Assume it's telegram_id for creating admin
        try:
            telegram_id = int(command)
            asyncio.run(create_admin_from_user(telegram_id))
        except ValueError:
            print(f"❌ Error: Unknown command '{command}'")
            print_usage()
            sys.exit(1)
