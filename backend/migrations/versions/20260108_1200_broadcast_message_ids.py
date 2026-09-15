"""add message_ids and new fields to broadcast_logs

Revision ID: broadcast_message_ids
Revises: vless_reality_001
Create Date: 2026-01-08 12:00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'broadcast_message_ids'
down_revision = 'vless_reality_001'
branch_labels = None
depends_on = None


def upgrade():
    # Add new columns to broadcast_logs
    op.add_column('broadcast_logs', sa.Column('target', sa.String(length=50), nullable=True))
    op.add_column('broadcast_logs', sa.Column('total_count', sa.Integer(), nullable=True))
    op.add_column('broadcast_logs', sa.Column('has_photo', sa.Boolean(), nullable=True, server_default='false'))
    op.add_column('broadcast_logs', sa.Column('has_buttons', sa.Boolean(), nullable=True, server_default='false'))
    op.add_column('broadcast_logs', sa.Column('buttons_data', postgresql.JSON(astext_type=sa.Text()), nullable=True))
    op.add_column('broadcast_logs', sa.Column('message_ids', postgresql.JSON(astext_type=sa.Text()), nullable=True))
    
    # Update target from target_filter where null
    op.execute("UPDATE broadcast_logs SET target = target_filter WHERE target IS NULL")
    op.execute("UPDATE broadcast_logs SET total_count = total_users WHERE total_count IS NULL")


def downgrade():
    op.drop_column('broadcast_logs', 'message_ids')
    op.drop_column('broadcast_logs', 'buttons_data')
    op.drop_column('broadcast_logs', 'has_buttons')
    op.drop_column('broadcast_logs', 'has_photo')
    op.drop_column('broadcast_logs', 'total_count')
    op.drop_column('broadcast_logs', 'target')
