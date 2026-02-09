#!/usr/bin/env bash

set -euo pipefail

# Builds and runs the production Docker image locally.
#
# Usage:
#   ./scripts/run_prod_local.sh
#
# Configure via environment variables:
#   IMAGE_TAG=open-ithageneia:prod-local
#   HOST_PORT=8000
#   SECRET_KEY=... (optional override)

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
IMAGE_TAG="${IMAGE_TAG:-open-ithageneia:prod-local}"
HOST_PORT="${HOST_PORT:-8000}"
CONTAINER_NAME="${CONTAINER_NAME:-open-ithageneia-prod-local}"

cd "$ROOT_DIR"

SECRET_KEY_VALUE="${SECRET_KEY:-local-only-insecure-secret-key}"

mkdir -p "${ROOT_DIR}/db"

echo "Building production image: $IMAGE_TAG"
docker build -t "$IMAGE_TAG" .

# If a container with the same name exists, remove it to avoid conflicts.
if docker ps -a --format '{{.Names}}' | grep -qx "$CONTAINER_NAME"; then
  docker rm -f "$CONTAINER_NAME" >/dev/null
fi

echo "Running container on http://localhost:${HOST_PORT}"
exec docker run --rm -it \
  --name "$CONTAINER_NAME" \
  -p "${HOST_PORT}:8000" \
  -e "SECRET_KEY=${SECRET_KEY_VALUE}" \
  -e "DEBUG=False" \
  -e "ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0" \
  -e "CSRF_TRUSTED_ORIGINS=http://localhost:${HOST_PORT},http://127.0.0.1:${HOST_PORT}" \
  -e DJANGO_SETTINGS_MODULE=open_ithageneia.settings_production \
  -v "open_ithageneia_db:/code/db" \
  "$IMAGE_TAG"
