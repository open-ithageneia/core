#!/bin/bash

set -o errexit
set -o pipefail
set -o nounset

echo "Collecting static files..."
python ./manage.py collectstatic --noinput --settings=open_ithageneia.settings_production

echo "Running migrations..."
python ./manage.py migrate --noinput --settings=open_ithageneia.settings_production

if [[ "${IS_PREVIEW_DEPLOYMENT:-}" == "1" || "${IS_PREVIEW_DEPLOYMENT:-}" == "true" || "${IS_PREVIEW_DEPLOYMENT:-}" == "True" ]]; then
	if [[ -n "${PREVIEW_SUPERUSER_USERNAME:-}" && -n "${PREVIEW_SUPERUSER_PASSWORD:-}" ]]; then
		export DJANGO_SUPERUSER_USERNAME="${PREVIEW_SUPERUSER_USERNAME}"
		export DJANGO_SUPERUSER_PASSWORD="${PREVIEW_SUPERUSER_PASSWORD}"
		python ./manage.py createsuperuser --noinput --settings=open_ithageneia.settings_production || true
	fi
fi

echo "Starting Gunicorn..."
exec "$@"
