"""add description and images to cigars

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-04-07

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('cigars', schema=None) as batch_op:
        batch_op.add_column(sa.Column('description',      sa.Text(),          nullable=True))
        batch_op.add_column(sa.Column('image_single_url', sa.String(500),     nullable=True))
        batch_op.add_column(sa.Column('image_box_url',    sa.String(500),     nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('cigars', schema=None) as batch_op:
        batch_op.drop_column('image_box_url')
        batch_op.drop_column('image_single_url')
        batch_op.drop_column('description')
