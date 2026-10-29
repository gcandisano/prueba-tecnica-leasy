#!/bin/sh
set -eu

python src/manage.py migrate --noinput

# The seed command is not idempotent over time (dates depend on "now"), so it
# runs only once per data volume. The marker lives next to the database.
SEED_MARKER="$(dirname "$DJANGO_DB_PATH")/.demo-data-seeded"
if [ "${DJANGO_SEED_DEMO_DATA:-false}" = "true" ] && [ ! -f "$SEED_MARKER" ]; then
    python src/manage.py seed_assessment_data
    touch "$SEED_MARKER"
fi

exec "$@"
