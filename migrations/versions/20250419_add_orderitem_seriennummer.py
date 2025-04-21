"""
Add seriennummer field to OrderItem
Revision ID: 20250419_add_orderitem_seriennummer
Revises: 20250419_add_order_tracking_number
Create Date: 2025-04-19
"""
from alembic import op
import sqlalchemy as sa

revision = '20250419_add_orderitem_seriennummer'
down_revision = '20250419_add_order_tracking_number'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('order_item', sa.Column('seriennummer', sa.String(length=100), nullable=True))

def downgrade():
    op.drop_column('order_item', 'seriennummer')
