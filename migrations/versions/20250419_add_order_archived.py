"""
Add archived field to Order model
Revision ID: 20250419_add_order_archived
Revises: 
Create Date: 2025-04-19
"""
from alembic import op
import sqlalchemy as sa

# Alembic identifiers
revision = '20250419_add_order_archived'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('order', sa.Column('archived', sa.Boolean(), nullable=False, server_default=sa.false()))

def downgrade():
    op.drop_column('order', 'archived')
