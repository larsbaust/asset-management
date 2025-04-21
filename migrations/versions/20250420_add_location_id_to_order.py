"""
Add location_id to Order (ForeignKey) and migrate existing data

Revision ID: 20250420_add_location_id_to_order
Revises: f8b1a1fb5800
Create Date: 2025-04-20 10:38:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column
from sqlalchemy import String, Integer

# revision identifiers, used by Alembic.
revision = '20250420_add_location_id_to_order'
down_revision = 'f8b1a1fb5800'
branch_labels = None
depends_on = None

def upgrade():
    with op.batch_alter_table('order', schema=None) as batch_op:
        batch_op.add_column(sa.Column('location_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key('fk_order_location_id', 'location', ['location_id'], ['id'])

    # Datenmigration: Übertrage alte Standortnamen auf location_id
    conn = op.get_bind()
    order_table = table('order',
        column('id', Integer),
        column('location', String),
        column('location_id', Integer)
    )
    location_table = table('location',
        column('id', Integer),
        column('name', String)
    )
    orders = conn.execute(sa.select(
        order_table.c.id, order_table.c.location
    )).fetchall()
    for order_id, location_name in orders:
        if location_name:
            location_id = conn.execute(sa.select(location_table.c.id).where(
                sa.func.lower(sa.func.trim(location_table.c.name)) == sa.func.lower(sa.func.trim(location_name))
            )).scalar()
            if location_id:
                conn.execute(
                    order_table.update().where(order_table.c.id == order_id).values(location_id=location_id)
                )

def downgrade():
    with op.batch_alter_table('order', schema=None) as batch_op:
        batch_op.drop_constraint('fk_order_location_id', type_='foreignkey')
        batch_op.drop_column('location_id')
