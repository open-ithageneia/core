#!/bin/bash

set -o errexit
set -o pipefail
set -o nounset

PORT=${PORT:-8000}

# Ensure sqlite db directory exists (useful when /code/db is a volume)
mkdir -p /code/db

echo "Collecting static files..."
python ./manage.py collectstatic --noinput --settings=open_ithageneia.settings_production

echo "Running migrations..."
python ./manage.py migrate --noinput --settings=open_ithageneia.settings_production

echo "Starting Gunicorn..."
exec gunicorn --bind 0.0.0.0:$PORT --workers 2 --threads 4 --timeout 0 open_ithageneia.wsgi
