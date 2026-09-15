"""add broadcast features

Revision ID: broadcast_features
Revises: 
Create Date: 2026-01-05 13:50:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'broadcast_features'
down_revision = 'admin_telegram_id'
branch_labels = None
depends_on = None


def upgrade():
    # Add disable_broadcast_notifications to users
    op.add_column('users', sa.Column('disable_broadcast_notifications', sa.Boolean(), nullable=False, server_default='false'))
    
    # Create broadcast_logs table
    op.create_table('broadcast_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('photo_url', sa.String(length=500), nullable=True),
        sa.Column('buttons', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('target_filter', sa.String(length=50), nullable=False),
        sa.Column('target_plan_id', sa.String(length=36), nullable=True),
        sa.Column('force_send', sa.Boolean(), nullable=True),
        sa.Column('total_users', sa.Integer(), nullable=True),
        sa.Column('sent_count', sa.Integer(), nullable=True),
        sa.Column('failed_count', sa.Integer(), nullable=True),
        sa.Column('admin_id', sa.String(length=36), nullable=False),
        sa.Column('admin_username', sa.String(length=255), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    op.drop_table('broadcast_logs')
    op.drop_column('users', 'disable_broadcast_notifications')
