"""final merge

Revision ID: b891b92e9038
Revises: 20250420_add_location_id_to_inventorysession, 20250420_add_location_id_to_order, 471447eb3ade
Create Date: 2025-04-20 10:51:08.642642

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b891b92e9038'
down_revision = ('20250420_add_location_id_to_inventorysession', '20250420_add_location_id_to_order', '471447eb3ade')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
