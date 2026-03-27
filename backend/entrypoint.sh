#!/bin/sh
set -e

echo "Running migrations..."
alembic upgrade head

echo "Seeding sources..."
python -m app.scrapers.sources_seed

echo "Seeding cigars..."
python -m app.scrapers.cigars_seed

exec "$@"
