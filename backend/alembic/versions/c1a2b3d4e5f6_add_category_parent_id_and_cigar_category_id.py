"""add_category_parent_id_and_cigar_category_id

Revision ID: c1a2b3d4e5f6
Revises: 980b322d3eca
Create Date: 2026-03-30 21:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'c1a2b3d4e5f6'
down_revision: Union[str, None] = '980b322d3eca'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add parent_id to categories (self-referential, nullable)
    with op.batch_alter_table('categories') as batch_op:
        batch_op.add_column(sa.Column('parent_id', sa.Integer(), nullable=True))

    # Add category_id to cigars (nullable FK — purely display, scraper-isolated)
    with op.batch_alter_table('cigars') as batch_op:
        batch_op.add_column(sa.Column('category_id', sa.Integer(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('cigars') as batch_op:
        batch_op.drop_column('category_id')

    with op.batch_alter_table('categories') as batch_op:
        batch_op.drop_column('parent_id')
