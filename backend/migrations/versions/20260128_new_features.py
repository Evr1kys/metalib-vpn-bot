"""Add new feature tables - gifts, trials, smart connect, kb, partners, promotions

Revision ID: new_features_001
Revises: 20260111_support
Create Date: 2026-01-28 10:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'new_features_001'
down_revision = '20260111_support'
branch_labels = None
depends_on = None


def upgrade():
    # Gift Certificates table
    op.create_table(
        'gift_certificates',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('code', sa.String(50), unique=True, nullable=False, index=True),
        sa.Column('buyer_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('recipient_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('recipient_name', sa.String(100), nullable=True),
        sa.Column('plan_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('plans.id'), nullable=False),
        sa.Column('status', sa.String(20), default='pending', nullable=False),
        sa.Column('message', sa.Text, nullable=True),
        sa.Column('payment_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('payments.id'), nullable=True),
        sa.Column('redeemed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )

    # Server Locations table
    op.create_table(
        'server_locations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('country', sa.String(100), nullable=False),
        sa.Column('country_code', sa.String(2), nullable=False),
        sa.Column('city', sa.String(100), nullable=True),
        sa.Column('flag', sa.String(10), default='🌍'),
        sa.Column('latitude', sa.Float, nullable=True),
        sa.Column('longitude', sa.Float, nullable=True),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('sort_order', sa.Integer, default=0),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )

    # Trials table
    op.create_table(
        'trials',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('status', sa.String(20), default='active', nullable=False),
        sa.Column('duration_hours', sa.Integer, default=24),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('device_fingerprint', sa.String(255), nullable=True),
        sa.Column('source', sa.String(50), default='bot'),
        sa.Column('subscription_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('subscriptions.id'), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('converted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )
    op.create_index('ix_trials_user_id', 'trials', ['user_id'])
    op.create_index('ix_trials_ip_address', 'trials', ['ip_address'])

    # Trial Settings (singleton)
    op.create_table(
        'trial_settings',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('is_enabled', sa.Boolean, default=True),
        sa.Column('duration_hours', sa.Integer, default=24),
        sa.Column('max_devices', sa.Integer, default=1),
        sa.Column('max_per_ip', sa.Integer, default=3),
        sa.Column('max_per_fingerprint', sa.Integer, default=3),
        sa.Column('require_telegram', sa.Boolean, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )

    # Smart Connect Profiles
    op.create_table(
        'smart_connect_profiles',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('name', sa.String(100), default='Default'),
        sa.Column('use_case', sa.String(50), default='general'),
        sa.Column('preferred_location_ids', postgresql.ARRAY(postgresql.UUID(as_uuid=True)), nullable=True),
        sa.Column('preferred_server_types', postgresql.ARRAY(sa.String), nullable=True),
        sa.Column('auto_switch', sa.Boolean, default=True),
        sa.Column('min_speed_mbps', sa.Integer, nullable=True),
        sa.Column('max_latency_ms', sa.Integer, nullable=True),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )

    # Server Health Checks
    op.create_table(
        'server_health_checks',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('server_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('servers.id'), nullable=False),
        sa.Column('status', sa.String(20), default='healthy'),
        sa.Column('ping_ms', sa.Integer, nullable=True),
        sa.Column('packet_loss', sa.Float, default=0),
        sa.Column('cpu_usage', sa.Float, nullable=True),
        sa.Column('memory_usage', sa.Float, nullable=True),
        sa.Column('bandwidth_usage', sa.Float, nullable=True),
        sa.Column('active_connections', sa.Integer, default=0),
        sa.Column('error_message', sa.Text, nullable=True),
        sa.Column('checked_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_server_health_checks_server_id', 'server_health_checks', ['server_id'])
    op.create_index('ix_server_health_checks_checked_at', 'server_health_checks', ['checked_at'])

    # Server Alerts
    op.create_table(
        'server_alerts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('server_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('servers.id'), nullable=False),
        sa.Column('alert_type', sa.String(50), nullable=False),
        sa.Column('severity', sa.String(20), default='warning'),
        sa.Column('message', sa.Text, nullable=False),
        sa.Column('is_resolved', sa.Boolean, default=False),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('resolved_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Speed Test Results
    op.create_table(
        'speed_test_results',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('server_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('servers.id'), nullable=False),
        sa.Column('download_speed', sa.Float, nullable=False),
        sa.Column('upload_speed', sa.Float, nullable=False),
        sa.Column('ping_ms', sa.Integer, nullable=False),
        sa.Column('jitter_ms', sa.Integer, nullable=True),
        sa.Column('test_server', sa.String(255), nullable=True),
        sa.Column('client_ip', sa.String(45), nullable=True),
        sa.Column('client_isp', sa.String(100), nullable=True),
        sa.Column('tested_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Operator Server Recommendations
    op.create_table(
        'operator_server_recommendations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('operator', sa.String(20), nullable=False),
        sa.Column('server_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('servers.id'), nullable=False),
        sa.Column('priority', sa.Integer, default=1),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )

    # FAQ Categories
    op.create_table(
        'faq_categories',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('slug', sa.String(100), unique=True, nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('icon', sa.String(10), default='📂'),
        sa.Column('sort_order', sa.Integer, default=0),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )

    # Knowledge Base Articles
    op.create_table(
        'knowledge_base_articles',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('slug', sa.String(255), unique=True, nullable=False, index=True),
        sa.Column('content', sa.Text, nullable=False),
        sa.Column('excerpt', sa.Text, nullable=True),
        sa.Column('category', sa.String(50), default='general'),
        sa.Column('faq_category_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('faq_categories.id'), nullable=True),
        sa.Column('status', sa.String(20), default='draft'),
        sa.Column('is_faq', sa.Boolean, default=False),
        sa.Column('is_featured', sa.Boolean, default=False),
        sa.Column('is_pinned', sa.Boolean, default=False),
        sa.Column('author_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('views_count', sa.Integer, default=0),
        sa.Column('likes_count', sa.Integer, default=0),
        sa.Column('dislikes_count', sa.Integer, default=0),
        sa.Column('sort_order', sa.Integer, default=0),
        sa.Column('meta_title', sa.String(255), nullable=True),
        sa.Column('meta_description', sa.String(500), nullable=True),
        sa.Column('tags', postgresql.ARRAY(sa.String), nullable=True),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )

    # Article Views
    op.create_table(
        'article_views',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('article_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('knowledge_base_articles.id'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.Text, nullable=True),
        sa.Column('viewed_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Article Likes
    op.create_table(
        'article_likes',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('article_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('knowledge_base_articles.id'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('is_like', sa.Boolean, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Partners
    op.create_table(
        'partners',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False, unique=True),
        sa.Column('referral_code', sa.String(50), unique=True, nullable=False, index=True),
        sa.Column('status', sa.String(20), default='pending'),
        sa.Column('tier', sa.String(20), default='bronze'),
        sa.Column('commission_percent', sa.Integer, default=20),
        sa.Column('telegram_channel', sa.String(255), nullable=True),
        sa.Column('website', sa.String(255), nullable=True),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('total_clicks', sa.Integer, default=0),
        sa.Column('total_sales', sa.Integer, default=0),
        sa.Column('total_earned', sa.Numeric(12, 2), default=0),
        sa.Column('pending_payout', sa.Numeric(12, 2), default=0),
        sa.Column('is_verified', sa.Boolean, default=False),
        sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )

    # Partner Clicks
    op.create_table(
        'partner_clicks',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('partner_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('partners.id'), nullable=False),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.Text, nullable=True),
        sa.Column('referer', sa.Text, nullable=True),
        sa.Column('landing_page', sa.String(500), nullable=True),
        sa.Column('is_unique', sa.Boolean, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_partner_clicks_partner_id', 'partner_clicks', ['partner_id'])

    # Partner Sales
    op.create_table(
        'partner_sales',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('partner_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('partners.id'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('payment_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('payments.id'), nullable=False),
        sa.Column('amount', sa.Numeric(12, 2), nullable=False),
        sa.Column('commission_percent', sa.Integer, nullable=False),
        sa.Column('commission_amount', sa.Numeric(12, 2), nullable=False),
        sa.Column('is_paid', sa.Boolean, default=False),
        sa.Column('payout_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_partner_sales_partner_id', 'partner_sales', ['partner_id'])

    # Partner Payouts
    op.create_table(
        'partner_payouts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('partner_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('partners.id'), nullable=False),
        sa.Column('amount', sa.Numeric(12, 2), nullable=False),
        sa.Column('method', sa.String(50), nullable=False),
        sa.Column('details', postgresql.JSONB, nullable=True),
        sa.Column('status', sa.String(20), default='pending'),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('processed_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('transaction_id', sa.String(255), nullable=True),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )

    # Partner Settings (singleton)
    op.create_table(
        'partner_settings',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('is_enabled', sa.Boolean, default=True),
        sa.Column('min_payout_amount', sa.Numeric(12, 2), default=1000),
        sa.Column('default_commission', sa.Integer, default=20),
        sa.Column('bronze_threshold', sa.Integer, default=0),
        sa.Column('bronze_commission', sa.Integer, default=20),
        sa.Column('silver_threshold', sa.Integer, default=10),
        sa.Column('silver_commission', sa.Integer, default=25),
        sa.Column('gold_threshold', sa.Integer, default=50),
        sa.Column('gold_commission', sa.Integer, default=30),
        sa.Column('platinum_threshold', sa.Integer, default=100),
        sa.Column('platinum_commission', sa.Integer, default=40),
        sa.Column('cookie_days', sa.Integer, default=30),
        sa.Column('require_approval', sa.Boolean, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )

    # Promotions
    op.create_table(
        'promotions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('promo_type', sa.String(20), default='discount'),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('discount_percent', sa.Integer, nullable=True),
        sa.Column('discount_amount', sa.Numeric(12, 2), nullable=True),
        sa.Column('promo_code_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('promo_codes.id'), nullable=True),
        sa.Column('plan_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('plans.id'), nullable=True),
        sa.Column('banner_url', sa.String(500), nullable=True),
        sa.Column('badge_text', sa.String(50), nullable=True),
        sa.Column('is_timer_enabled', sa.Boolean, default=False),
        sa.Column('timer_end', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('priority', sa.Integer, default=0),
        sa.Column('total_uses', sa.Integer, default=0),
        sa.Column('max_uses', sa.Integer, nullable=True),
        sa.Column('starts_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('ends_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )

    # Promotion Uses
    op.create_table(
        'promotion_uses',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('promotion_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('promotions.id'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('payment_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('payments.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Savings Calculator Config (singleton)
    op.create_table(
        'savings_calculator_config',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('is_enabled', sa.Boolean, default=True),
        sa.Column('monthly_price', sa.Numeric(12, 2), nullable=False),
        sa.Column('yearly_price', sa.Numeric(12, 2), nullable=False),
        sa.Column('yearly_discount_percent', sa.Integer, default=50),
        sa.Column('show_comparison', sa.Boolean, default=True),
        sa.Column('comparison_vpn_name', sa.String(100), nullable=True),
        sa.Column('comparison_vpn_price', sa.Numeric(12, 2), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )

    # Add new columns to servers table
    try:
        op.add_column('servers', sa.Column('location_id', postgresql.UUID(as_uuid=True), nullable=True))
        op.add_column('servers', sa.Column('server_type', sa.String(20), default='general'))
        op.add_column('servers', sa.Column('ping_ms', sa.Integer, nullable=True))
        op.add_column('servers', sa.Column('supports_gaming', sa.Boolean, default=False))
        op.add_column('servers', sa.Column('supports_streaming', sa.Boolean, default=False))
        op.add_column('servers', sa.Column('supports_torrents', sa.Boolean, default=False))
        op.add_column('servers', sa.Column('recommended_for', postgresql.ARRAY(sa.String), nullable=True))
    except Exception:
        pass  # Columns may already exist


def downgrade():
    # Drop new server columns
    try:
        op.drop_column('servers', 'recommended_for')
        op.drop_column('servers', 'supports_torrents')
        op.drop_column('servers', 'supports_streaming')
        op.drop_column('servers', 'supports_gaming')
        op.drop_column('servers', 'ping_ms')
        op.drop_column('servers', 'server_type')
        op.drop_column('servers', 'location_id')
    except Exception:
        pass

    # Drop tables in reverse order
    op.drop_table('savings_calculator_config')
    op.drop_table('promotion_uses')
    op.drop_table('promotions')
    op.drop_table('partner_settings')
    op.drop_table('partner_payouts')
    op.drop_table('partner_sales')
    op.drop_table('partner_clicks')
    op.drop_table('partners')
    op.drop_table('article_likes')
    op.drop_table('article_views')
    op.drop_table('knowledge_base_articles')
    op.drop_table('faq_categories')
    op.drop_table('operator_server_recommendations')
    op.drop_table('speed_test_results')
    op.drop_table('server_alerts')
    op.drop_table('server_health_checks')
    op.drop_table('smart_connect_profiles')
    op.drop_table('trial_settings')
    op.drop_table('trials')
    op.drop_table('server_locations')
    op.drop_table('gift_certificates')
