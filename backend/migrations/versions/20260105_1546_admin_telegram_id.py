"""add telegram_id to admin_users

Revision ID: admin_telegram_id
Revises: 61ae62d1d268
Create Date: 2026-01-05 15:46:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'admin_telegram_id'
down_revision = '61ae62d1d268'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add telegram_id column to admin_users
    op.add_column('admin_users', sa.Column('telegram_id', sa.BigInteger(), nullable=True))
    op.create_index(op.f('ix_admin_users_telegram_id'), 'admin_users', ['telegram_id'], unique=False)
    
    # Make email nullable since we'll use telegram_id
    op.alter_column('admin_users', 'email',
               existing_type=sa.VARCHAR(length=255),
               nullable=True)


def downgrade() -> None:
    op.alter_column('admin_users', 'email',
               existing_type=sa.VARCHAR(length=255),
               nullable=False)
    op.drop_index(op.f('ix_admin_users_telegram_id'), table_name='admin_users')
    op.drop_column('admin_users', 'telegram_id')
