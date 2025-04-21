"""
Rename seriennummer to serial_number in OrderItem
Revision ID: 20250419_rename_orderitem_serial_number
Revises: 20250419_add_asset_seriennummer
Create Date: 2025-04-19
"""
from alembic import op
import sqlalchemy as sa

revision = '20250419_rename_orderitem_serial_number'
down_revision = '20250419_add_asset_seriennummer'
branch_labels = None
depends_on = None

def upgrade():
    op.alter_column('order_item', 'seriennummer', new_column_name='serial_number', existing_type=sa.String(length=100))

def downgrade():
    op.alter_column('order_item', 'serial_number', new_column_name='seriennummer', existing_type=sa.String(length=100))
