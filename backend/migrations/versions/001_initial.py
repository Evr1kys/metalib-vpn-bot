"""Initial migration

Revision ID: 001_initial
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid

# revision identifiers, used by Alembic.
revision = '001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('telegram_id', sa.BigInteger(), nullable=False, unique=True),
        sa.Column('username', sa.String(length=255), nullable=True),
        sa.Column('first_name', sa.String(length=255), nullable=True),
        sa.Column('last_name', sa.String(length=255), nullable=True),
        sa.Column('language_code', sa.String(length=10), nullable=True, default='ru'),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('is_blocked', sa.Boolean(), nullable=False, default=False),
        sa.Column('referrer_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()'), onupdate=sa.text('NOW()'))
    )
    op.create_index('ix_users_telegram_id', 'users', ['telegram_id'])
    op.create_index('ix_users_username', 'users', ['username'])
    
    # Create server_groups table
    op.create_table(
        'server_groups',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('country_code', sa.String(length=2), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()'))
    )
    
    # Create servers table
    op.create_table(
        'servers',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('host', sa.String(length=255), nullable=False),
        sa.Column('agent_port', sa.Integer(), nullable=False, default=8001),
        sa.Column('agent_secret_key', sa.String(length=255), nullable=False),
        sa.Column('group_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('server_groups.id'), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, default='online'),
        sa.Column('max_users', sa.Integer(), nullable=False, default=1000),
        sa.Column('current_users', sa.Integer(), nullable=False, default=0),
        sa.Column('cpu_usage', sa.Float(), nullable=True),
        sa.Column('memory_usage', sa.Float(), nullable=True),
        sa.Column('disk_usage', sa.Float(), nullable=True),
        sa.Column('network_upload', sa.BigInteger(), nullable=True),
        sa.Column('network_download', sa.BigInteger(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('last_health_check', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()'))
    )
    op.create_index('ix_servers_host', 'servers', ['host'])
    op.create_index('ix_servers_status', 'servers', ['status'])
    
    # Create plans table
    op.create_table(
        'plans',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('duration_days', sa.Integer(), nullable=False),
        sa.Column('price', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=False, default='RUB'),
        sa.Column('max_devices', sa.Integer(), nullable=False, default=1),
        sa.Column('traffic_limit_gb', sa.Integer(), nullable=True),
        sa.Column('speed_limit_mbps', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('sort_order', sa.Integer(), nullable=False, default=0),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()'))
    )
    
    # Create vpn_accounts table
    op.create_table(
        'vpn_accounts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('server_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('servers.id'), nullable=False),
        sa.Column('protocol', sa.String(length=50), nullable=False),
        sa.Column('username', sa.String(length=255), nullable=False),
        sa.Column('config_encrypted', sa.Text(), nullable=False),
        sa.Column('public_key', sa.Text(), nullable=True),
        sa.Column('client_ip', sa.String(length=45), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('bytes_sent', sa.BigInteger(), nullable=False, default=0),
        sa.Column('bytes_received', sa.BigInteger(), nullable=False, default=0),
        sa.Column('last_handshake', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()'))
    )
    op.create_index('ix_vpn_accounts_user_id', 'vpn_accounts', ['user_id'])
    op.create_index('ix_vpn_accounts_username', 'vpn_accounts', ['username'], unique=True)
    
    # Create subscriptions table
    op.create_table(
        'subscriptions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('plan_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('plans.id'), nullable=False),
        sa.Column('vpn_account_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('vpn_accounts.id'), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, default='pending'),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('cancelled_at', sa.DateTime(), nullable=True),
        sa.Column('auto_renew', sa.Boolean(), nullable=False, default=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()'))
    )
    op.create_index('ix_subscriptions_user_id', 'subscriptions', ['user_id'])
    op.create_index('ix_subscriptions_status', 'subscriptions', ['status'])
    op.create_index('ix_subscriptions_expires_at', 'subscriptions', ['expires_at'])
    
    # Create payments table
    op.create_table(
        'payments',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('subscription_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('subscriptions.id'), nullable=True),
        sa.Column('external_id', sa.String(length=255), nullable=True),
        sa.Column('provider', sa.String(length=50), nullable=False, default='platega'),
        sa.Column('amount', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=False, default='RUB'),
        sa.Column('status', sa.String(length=50), nullable=False, default='pending'),
        sa.Column('payment_url', sa.Text(), nullable=True),
        sa.Column('paid_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()'))
    )
    op.create_index('ix_payments_user_id', 'payments', ['user_id'])
    op.create_index('ix_payments_external_id', 'payments', ['external_id'], unique=True)
    op.create_index('ix_payments_status', 'payments', ['status'])
    
    # Create devices table
    op.create_table(
        'devices',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('subscription_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('subscriptions.id'), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('device_type', sa.String(length=50), nullable=True),
        sa.Column('device_id', sa.String(length=255), nullable=True),
        sa.Column('fingerprint', sa.Text(), nullable=True),
        sa.Column('protocol', sa.String(length=50), nullable=False),
        sa.Column('binding_token', sa.String(length=10), nullable=True),
        sa.Column('binding_token_expires_at', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('last_seen_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()'))
    )
    op.create_index('ix_devices_subscription_id', 'devices', ['subscription_id'])
    op.create_index('ix_devices_binding_token', 'devices', ['binding_token'])
    
    # Create device_sessions table
    op.create_table(
        'device_sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('device_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('devices.id'), nullable=False),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('bytes_sent', sa.BigInteger(), nullable=False, default=0),
        sa.Column('bytes_received', sa.BigInteger(), nullable=False, default=0),
        sa.Column('started_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('ended_at', sa.DateTime(), nullable=True)
    )
    op.create_index('ix_device_sessions_device_id', 'device_sessions', ['device_id'])
    
    # Create admin_users table
    op.create_table(
        'admin_users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('username', sa.String(length=255), nullable=False, unique=True),
        sa.Column('email', sa.String(length=255), nullable=False, unique=True),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=255), nullable=True),
        sa.Column('role', sa.String(length=50), nullable=False, default='admin'),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('last_login', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()'))
    )
    op.create_index('ix_admin_users_username', 'admin_users', ['username'])
    op.create_index('ix_admin_users_email', 'admin_users', ['email'])
    
    # Create audit_logs table
    op.create_table(
        'audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('admin_user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('admin_users.id'), nullable=True),
        sa.Column('action', sa.String(length=255), nullable=False),
        sa.Column('resource_type', sa.String(length=100), nullable=False),
        sa.Column('resource_id', sa.String(length=255), nullable=True),
        sa.Column('details', postgresql.JSONB(), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()'))
    )
    op.create_index('ix_audit_logs_admin_user_id', 'audit_logs', ['admin_user_id'])
    op.create_index('ix_audit_logs_action', 'audit_logs', ['action'])
    op.create_index('ix_audit_logs_created_at', 'audit_logs', ['created_at'])
    
    # Create promo_codes table
    op.create_table(
        'promo_codes',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('code', sa.String(length=50), nullable=False, unique=True),
        sa.Column('discount_percent', sa.Integer(), nullable=True),
        sa.Column('discount_amount', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('max_uses', sa.Integer(), nullable=True),
        sa.Column('used_count', sa.Integer(), nullable=False, default=0),
        sa.Column('valid_from', sa.DateTime(), nullable=True),
        sa.Column('valid_until', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()'))
    )
    op.create_index('ix_promo_codes_code', 'promo_codes', ['code'])
    
    # Create referrals table
    op.create_table(
        'referrals',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('referrer_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('referred_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('reward_amount', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('reward_paid', sa.Boolean(), nullable=False, default=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()'))
    )
    op.create_index('ix_referrals_referrer_id', 'referrals', ['referrer_id'])
    op.create_index('ix_referrals_referred_id', 'referrals', ['referred_id'])
    
    # Create notifications table
    op.create_table(
        'notifications',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('type', sa.String(length=50), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('is_read', sa.Boolean(), nullable=False, default=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()'))
    )
    op.create_index('ix_notifications_user_id', 'notifications', ['user_id'])
    op.create_index('ix_notifications_is_read', 'notifications', ['is_read'])


def downgrade() -> None:
    op.drop_table('notifications')
    op.drop_table('referrals')
    op.drop_table('promo_codes')
    op.drop_table('audit_logs')
    op.drop_table('admin_users')
    op.drop_table('device_sessions')
    op.drop_table('devices')
    op.drop_table('payments')
    op.drop_table('subscriptions')
    op.drop_table('vpn_accounts')
    op.drop_table('plans')
    op.drop_table('servers')
    op.drop_table('server_groups')
    op.drop_table('users')
