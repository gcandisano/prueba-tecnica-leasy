#!/bin/sh
set -eu

python src/manage.py migrate --noinput

if [ "${DJANGO_SEED_DEMO_DATA:-false}" = "true" ]; then
    python src/manage.py seed_demo_data_if_empty
fi

exec "$@"
