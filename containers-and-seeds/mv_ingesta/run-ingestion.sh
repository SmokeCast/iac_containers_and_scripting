#!/usr/bin/env bash
set -Eeuo pipefail

# Ejecuta los tres workers como jobs puntuales. Está pensado para ser llamado
# manualmente o desde cron en la MV de ingesta.
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${SCRIPT_DIR}/.env"
LOCK_FILE="${INGESTION_LOCK_FILE:-/tmp/smokecast-ingesta.lock}"

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "No existe ${ENV_FILE}. Copia env.example a .env y completa sus valores." >&2
  exit 1
fi

cd "${SCRIPT_DIR}"

flock -n "${LOCK_FILE}" bash -c '
  set -Eeuo pipefail
  docker compose --env-file .env run --rm fires-ingestion
  docker compose --env-file .env run --rm cities-ingestion
  docker compose --env-file .env run --rm weather-ingestion
'
