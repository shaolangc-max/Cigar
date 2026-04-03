"""add ignored_raw_names table

Revision ID: a1b2c3d4e5f6
Revises: d7e8f9a0b1c2
Create Date: 2026-04-02

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'd7e8f9a0b1c2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'ignored_raw_names',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('source_slug', sa.String(length=50), nullable=False),
        sa.Column('raw_name', sa.String(length=500), nullable=False),
        sa.Column('ignored_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('source_slug', 'raw_name', name='uq_ignored_source_raw'),
    )
    with op.batch_alter_table('ignored_raw_names', schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f('ix_ignored_raw_names_source_slug'), ['source_slug'], unique=False
        )


def downgrade() -> None:
    with op.batch_alter_table('ignored_raw_names', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_ignored_raw_names_source_slug'))
    op.drop_table('ignored_raw_names')
