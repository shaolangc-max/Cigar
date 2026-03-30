"""add_categories_table_and_series_category_id

Revision ID: 980b322d3eca
Revises: f3bc22bdabfe
Create Date: 2026-03-30 19:53:28.674854

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '980b322d3eca'
down_revision: Union[str, None] = 'f3bc22bdabfe'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'categories',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('brand_id', sa.Integer(), sa.ForeignKey('brands.id'), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('slug', sa.String(150), nullable=False),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
    )
    op.create_index('ix_categories_brand_id', 'categories', ['brand_id'])
    op.create_index('ix_categories_slug', 'categories', ['slug'], unique=True)

    with op.batch_alter_table('series') as batch_op:
        batch_op.add_column(sa.Column('category_id', sa.Integer(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('series') as batch_op:
        batch_op.drop_column('category_id')
    op.drop_table('categories')
