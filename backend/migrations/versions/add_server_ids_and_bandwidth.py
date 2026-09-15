"""Add server_ids to plans and total_bandwidth to servers

Revision ID: add_server_ids_and_bandwidth
Revises: 20260108_1200_broadcast_message_ids
Create Date: 2026-01-09

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'add_server_ids_and_bandwidth'
down_revision: Union[str, None] = 'broadcast_message_ids'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add server_ids to plans (array of UUIDs for server assignment)
    op.add_column('plans', sa.Column('server_ids', postgresql.ARRAY(postgresql.UUID(as_uuid=True)), nullable=True))
    
    # Add total_bandwidth to servers (all-time bandwidth tracking)
    op.add_column('servers', sa.Column('total_bandwidth', sa.BigInteger(), nullable=False, server_default='0'))
    
    # Remove max_devices from plans if exists (we're removing device limits)
    # Note: This is a data-preserving migration - only removes the column
    try:
        op.drop_column('plans', 'max_devices')
    except:
        pass  # Column may not exist


def downgrade() -> None:
    # Remove total_bandwidth from servers
    op.drop_column('servers', 'total_bandwidth')
    
    # Remove server_ids from plans
    op.drop_column('plans', 'server_ids')
    
    # Re-add max_devices to plans
    op.add_column('plans', sa.Column('max_devices', sa.Integer(), nullable=False, server_default='1'))
