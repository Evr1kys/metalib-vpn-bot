"""Add VLESS+Reality support

Revision ID: vless_reality_001
Revises: 20260105_1645_broadcast_features
Create Date: 2026-01-07 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'vless_reality_001'
down_revision = 'broadcast_features'
branch_labels = None
depends_on = None


def upgrade():
    """Add VLESS+Reality protocol to VPN protocol enum"""
    
    # Add new enum value to vpn_protocol
    # PostgreSQL requires special handling for enum types
    op.execute("ALTER TYPE vpn_protocol ADD VALUE 'vless+reality'")
    
    # No table structure changes needed
    pass


def downgrade():
    """Remove VLESS+Reality protocol"""
    
    # Note: PostgreSQL doesn't support removing enum values easily
    # This would require recreating the type, which is complex
    # In production, we typically don't downgrade enum additions
    pass
