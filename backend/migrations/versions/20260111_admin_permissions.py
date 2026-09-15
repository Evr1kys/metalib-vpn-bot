"""Add admin permissions and extended fields

Revision ID: admin_permissions_v1
Revises: add_server_ids_and_bandwidth
Create Date: 2026-01-11

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'admin_permissions_v1'
down_revision: Union[str, None] = 'add_server_ids_and_bandwidth'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new columns to admin_users table
    op.add_column('admin_users', sa.Column('custom_permissions', sa.JSON(), nullable=True))
    op.add_column('admin_users', sa.Column('description', sa.Text(), nullable=True))
    op.add_column('admin_users', sa.Column('avatar_url', sa.String(500), nullable=True))
    
    # Update admin_role enum to include new roles
    # PostgreSQL requires recreating the enum
    op.execute("ALTER TYPE admin_role ADD VALUE IF NOT EXISTS 'moderator'")
    op.execute("ALTER TYPE admin_role ADD VALUE IF NOT EXISTS 'viewer'")


def downgrade() -> None:
    op.drop_column('admin_users', 'custom_permissions')
    op.drop_column('admin_users', 'description')
    op.drop_column('admin_users', 'avatar_url')
    # Note: Cannot remove enum values in PostgreSQL
