"""Support system tables

Revision ID: 20260111_support
Revises: admin_permissions_v1
Create Date: 2026-01-11

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision = '20260111_support'
down_revision = 'admin_permissions_v1'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create enums one by one (asyncpg doesn't support multiple statements)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE ticketstatus AS ENUM ('open', 'in_progress', 'waiting_user', 'resolved', 'closed');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$
    """)
    
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE ticketpriority AS ENUM ('low', 'normal', 'high', 'urgent');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$
    """)
    
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE messagesender AS ENUM ('user', 'admin', 'system');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$
    """)
    
    # Create support_tickets table
    op.execute("""
        CREATE TABLE IF NOT EXISTS support_tickets (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID REFERENCES users(id),
            telegram_user_id BIGINT NOT NULL,
            telegram_username VARCHAR(255),
            telegram_first_name VARCHAR(255),
            telegram_last_name VARCHAR(255),
            subject VARCHAR(500),
            status ticketstatus NOT NULL DEFAULT 'open',
            priority ticketpriority NOT NULL DEFAULT 'normal',
            assigned_admin_id UUID REFERENCES admin_users(id),
            created_at TIMESTAMP NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
            last_message_at TIMESTAMP NOT NULL DEFAULT NOW(),
            resolved_at TIMESTAMP,
            message_count INTEGER NOT NULL DEFAULT 0,
            unread_count INTEGER NOT NULL DEFAULT 0
        )
    """)
    
    op.execute("CREATE INDEX IF NOT EXISTS ix_support_tickets_telegram_user_id ON support_tickets(telegram_user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_support_tickets_status ON support_tickets(status)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_support_tickets_assigned_admin_id ON support_tickets(assigned_admin_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_support_tickets_created_at ON support_tickets(created_at)")
    
    # Create support_messages table
    op.execute("""
        CREATE TABLE IF NOT EXISTS support_messages (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            ticket_id UUID NOT NULL REFERENCES support_tickets(id),
            sender_type messagesender NOT NULL,
            sender_admin_id UUID REFERENCES admin_users(id),
            text TEXT,
            telegram_message_id BIGINT,
            attachments TEXT,
            is_read BOOLEAN NOT NULL DEFAULT false,
            delivered_at TIMESTAMP,
            created_at TIMESTAMP NOT NULL DEFAULT NOW()
        )
    """)
    
    op.execute("CREATE INDEX IF NOT EXISTS ix_support_messages_ticket_id ON support_messages(ticket_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_support_messages_created_at ON support_messages(created_at)")
    
    # Create support_settings table
    op.execute("""
        CREATE TABLE IF NOT EXISTS support_settings (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            auto_reply_enabled BOOLEAN DEFAULT true,
            auto_reply_message TEXT DEFAULT 'Спасибо за обращение! Наш специалист ответит вам в ближайшее время.',
            working_hours_enabled BOOLEAN DEFAULT false,
            working_hours_start VARCHAR(5) DEFAULT '09:00',
            working_hours_end VARCHAR(5) DEFAULT '18:00',
            working_hours_timezone VARCHAR(50) DEFAULT 'Europe/Moscow',
            outside_hours_message TEXT DEFAULT 'Сейчас нерабочее время. Мы ответим вам в рабочие часы.',
            notify_new_ticket BOOLEAN DEFAULT true,
            notify_new_message BOOLEAN DEFAULT true,
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS support_settings CASCADE")
    op.execute("DROP TABLE IF EXISTS support_messages CASCADE")
    op.execute("DROP TABLE IF EXISTS support_tickets CASCADE")
    op.execute("DROP TYPE IF EXISTS messagesender CASCADE")
    op.execute("DROP TYPE IF EXISTS ticketpriority CASCADE")
    op.execute("DROP TYPE IF EXISTS ticketstatus CASCADE")
