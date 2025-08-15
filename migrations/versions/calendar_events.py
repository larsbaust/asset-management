"""
Migration für Kalender-Events und Erinnerungen

Revision ID: calendar_events_20250717
Revises: (hier die ID der vorherigen Migration einfügen)
Create Date: 2025-07-17 17:15:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic
revision = 'calendar_events_20250717'
down_revision = None  # Hier die ID der vorherigen Migration einfügen
branch_labels = None
depends_on = None


def upgrade():
    # Tabelle für Kalender-Events erstellen
    op.create_table(
        'calendar_events',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=128), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('start_datetime', sa.DateTime(), nullable=False),
        sa.Column('end_datetime', sa.DateTime(), nullable=True),
        sa.Column('all_day', sa.Boolean(), default=False),
        sa.Column('location', sa.String(length=256), nullable=True),
        sa.Column('event_type', sa.String(length=50), nullable=False),
        sa.Column('color_token', sa.String(length=50), nullable=True),
        sa.Column('status', sa.String(length=50), default='planned'),
        sa.Column('order_id', sa.Integer(), nullable=True),
        sa.Column('inventory_planning_id', sa.Integer(), nullable=True),
        sa.Column('created_by_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), default=sa.func.now(), onupdate=sa.func.now()),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ),
        sa.ForeignKeyConstraint(['inventory_planning_id'], ['inventory_planning.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Tabelle für Event-Erinnerungen erstellen
    op.create_table(
        'event_reminders',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('event_id', sa.Integer(), nullable=False),
        sa.Column('remind_at', sa.DateTime(), nullable=False),
        sa.Column('status', sa.String(length=50), default='pending'),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now()),
        sa.Column('delivered_at', sa.DateTime(), nullable=True),
        sa.Column('read_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['event_id'], ['calendar_events.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Indizes für schnellere Abfragen
    op.create_index('ix_calendar_events_start_datetime', 'calendar_events', ['start_datetime'])
    op.create_index('ix_calendar_events_event_type', 'calendar_events', ['event_type'])
    op.create_index('ix_calendar_events_status', 'calendar_events', ['status'])
    op.create_index('ix_event_reminders_remind_at', 'event_reminders', ['remind_at'])
    op.create_index('ix_event_reminders_status', 'event_reminders', ['status'])


def downgrade():
    # Indizes entfernen
    op.drop_index('ix_event_reminders_status', 'event_reminders')
    op.drop_index('ix_event_reminders_remind_at', 'event_reminders')
    op.drop_index('ix_calendar_events_status', 'calendar_events')
    op.drop_index('ix_calendar_events_event_type', 'calendar_events')
    op.drop_index('ix_calendar_events_start_datetime', 'calendar_events')
    
    # Tabellen entfernen
    op.drop_table('event_reminders')
    op.drop_table('calendar_events')
