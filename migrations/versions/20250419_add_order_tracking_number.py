"""
Add tracking_number field to Order model
Revision ID: 20250419_add_order_tracking_number
Revises: 20250419_add_order_location
Create Date: 2025-04-19
"""
from alembic import op
import sqlalchemy as sa

revision = '20250419_add_order_tracking_number'
down_revision = '20250419_add_order_location'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('order', sa.Column('tracking_number', sa.String(length=100), nullable=True))

def downgrade():
    op.drop_column('order', 'tracking_number')
