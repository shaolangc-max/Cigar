"""initial

Revision ID: 0001
Revises:
Create Date: 2026-03-28
"""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "brands",
        sa.Column("id",       sa.Integer, primary_key=True),
        sa.Column("name",     sa.String(100), nullable=False, unique=True),
        sa.Column("slug",     sa.String(100), nullable=False, unique=True),
        sa.Column("country",  sa.String(50),  nullable=True),
        sa.Column("image_url",sa.String(500), nullable=True),
    )
    op.create_index("ix_brands_slug", "brands", ["slug"])

    op.create_table(
        "series",
        sa.Column("id",       sa.Integer, primary_key=True),
        sa.Column("brand_id", sa.Integer, sa.ForeignKey("brands.id"), nullable=False),
        sa.Column("name",     sa.String(100), nullable=False),
        sa.Column("slug",     sa.String(150), nullable=False, unique=True),
    )
    op.create_index("ix_series_brand_id", "series", ["brand_id"])
    op.create_index("ix_series_slug",     "series", ["slug"])

    op.create_table(
        "cigars",
        sa.Column("id",         sa.Integer, primary_key=True),
        sa.Column("series_id",  sa.Integer, sa.ForeignKey("series.id"), nullable=False),
        sa.Column("name",       sa.String(200), nullable=False),
        sa.Column("slug",       sa.String(250), nullable=False, unique=True),
        sa.Column("vitola",     sa.String(100), nullable=True),
        sa.Column("length_mm",  sa.Float,       nullable=True),
        sa.Column("ring_gauge", sa.Float,       nullable=True),
        sa.Column("image_url",  sa.String(500), nullable=True),
    )
    op.create_index("ix_cigars_series_id", "cigars", ["series_id"])
    op.create_index("ix_cigars_slug",      "cigars", ["slug"])

    op.create_table(
        "sources",
        sa.Column("id",             sa.Integer, primary_key=True),
        sa.Column("name",           sa.String(100), nullable=False, unique=True),
        sa.Column("slug",           sa.String(100), nullable=False, unique=True),
        sa.Column("base_url",       sa.String(500), nullable=False),
        sa.Column("currency",       sa.String(10),  nullable=False),
        sa.Column("active",         sa.Boolean,     nullable=False, server_default="true"),
        sa.Column("scraper_config", sa.JSON,        nullable=True),
    )
    op.create_index("ix_sources_slug", "sources", ["slug"])

    op.create_table(
        "prices",
        sa.Column("id",           sa.Integer, primary_key=True),
        sa.Column("cigar_id",     sa.Integer, sa.ForeignKey("cigars.id"),   nullable=False),
        sa.Column("source_id",    sa.Integer, sa.ForeignKey("sources.id"),  nullable=False),
        sa.Column("price_single", sa.Float,   nullable=True),
        sa.Column("price_box",    sa.Float,   nullable=True),
        sa.Column("box_count",    sa.Integer, nullable=True),
        sa.Column("currency",     sa.String(10), nullable=False),
        sa.Column("product_url",  sa.String(500), nullable=True),
        sa.Column("in_stock",     sa.Boolean, nullable=False, server_default="true"),
        sa.Column("scraped_at",   sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("cigar_id", "source_id", name="uq_price_cigar_source"),
    )
    op.create_index("ix_prices_cigar_id",  "prices", ["cigar_id"])
    op.create_index("ix_prices_source_id", "prices", ["source_id"])

    op.create_table(
        "price_history",
        sa.Column("id",           sa.Integer, primary_key=True),
        sa.Column("cigar_id",     sa.Integer, sa.ForeignKey("cigars.id"),  nullable=False),
        sa.Column("source_id",    sa.Integer, sa.ForeignKey("sources.id"), nullable=False),
        sa.Column("price_single", sa.Float,   nullable=True),
        sa.Column("price_box",    sa.Float,   nullable=True),
        sa.Column("currency",     sa.String(10), nullable=False),
        sa.Column("scraped_at",   sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_price_history_cigar_id",  "price_history", ["cigar_id"])
    op.create_index("ix_price_history_source_id", "price_history", ["source_id"])
    op.create_index("ix_price_history_scraped_at","price_history", ["scraped_at"])

    op.create_table(
        "exchange_rates",
        sa.Column("currency",    sa.String(10), primary_key=True),
        sa.Column("rate_to_usd", sa.Float,      nullable=False),
        sa.Column("updated_at",  sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("exchange_rates")
    op.drop_table("price_history")
    op.drop_table("prices")
    op.drop_table("sources")
    op.drop_table("cigars")
    op.drop_table("series")
    op.drop_table("brands")
