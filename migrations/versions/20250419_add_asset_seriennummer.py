"""
Add seriennummer field to Asset
Revision ID: 20250419_add_asset_seriennummer
Revises: 20250419_add_orderitem_seriennummer
Create Date: 2025-04-19
"""
from alembic import op
import sqlalchemy as sa

revision = '20250419_add_asset_seriennummer'
down_revision = '20250419_add_orderitem_seriennummer'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('asset', sa.Column('seriennummer', sa.String(length=100), nullable=True))

def downgrade():
    op.drop_column('asset', 'seriennummer')
