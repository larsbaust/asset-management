"""
Add archived_at column to Asset

Revision ID: 20250519_add_archived_at_to_asset
Revises: 
Create Date: 2025-05-19
"""
from alembic import op
import sqlalchemy as sa

# Revision identifiers, used by Alembic.
revision = 'b03310994627'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('asset', sa.Column('archived_at', sa.DateTime(), nullable=True))

def downgrade():
    op.drop_column('asset', 'archived_at')
