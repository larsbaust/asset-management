"""
Add location field to Order model
Revision ID: 20250419_add_order_location
Revises: 20250419_add_order_archived
Create Date: 2025-04-19
"""
from alembic import op
import sqlalchemy as sa

revision = '20250419_add_order_location'
down_revision = '20250419_add_order_archived'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('order', sa.Column('location', sa.String(length=100), nullable=True))

def downgrade():
    op.drop_column('order', 'location')
