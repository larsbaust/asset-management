"""
Revision ID: 20250420_add_location_id_to_inventorysession
Revises: 
Create Date: 2025-04-20 10:48:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column
from sqlalchemy import Integer, String

# revision identifiers, used by Alembic.
revision = '20250420_add_location_id_to_inventorysession'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Batch-Mode für SQLite
    with op.batch_alter_table('inventory_session', schema=None) as batch_op:
        batch_op.add_column(sa.Column('location_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key('fk_inventorysession_location', 'location', ['location_id'], ['id'])

    # Migration der alten Standortdaten (außerhalb des batch-Blocks)
    connection = op.get_bind()
    result = connection.execute(sa.text('SELECT id, location FROM inventory_session WHERE location IS NOT NULL'))
    for row in result:
        if row['location']:
            location_result = connection.execute(sa.text('SELECT id FROM location WHERE name = :name'), {'name': row['location']}).fetchone()
            if location_result:
                connection.execute(sa.text('UPDATE inventory_session SET location_id = :loc_id WHERE id = :sess_id'), {'loc_id': location_result['id'], 'sess_id': row['id']})

def downgrade():
    with op.batch_alter_table('inventory_session', schema=None) as batch_op:
        batch_op.drop_constraint('fk_inventorysession_location', type_='foreignkey')
        batch_op.drop_column('location_id')
