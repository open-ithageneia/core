#!/bin/bash

set -o errexit
set -o pipefail
set -o nounset

echo "Collecting static files..."
python ./manage.py collectstatic --noinput --settings=open_ithageneia.settings_production

echo "Running migrations..."
python ./manage.py migrate --noinput --settings=open_ithageneia.settings_production

echo "Starting Gunicorn..."
exec "$@"
