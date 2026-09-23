#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  echo "Uso: $0 <dockerhub-usuario> [tag]" >&2
  echo "Ejemplo: $0 empuiquin24 latest" >&2
}

if [[ $# -lt 1 || $# -gt 2 ]]; then
  usage
  exit 2
fi

DOCKERHUB_USER="$1"
IMAGE_TAG="${2:-latest}"
if [[ ! "$DOCKERHUB_USER" =~ ^[a-z0-9][a-z0-9._-]*$ || ! "$IMAGE_TAG" =~ ^[A-Za-z0-9][A-Za-z0-9._-]*$ ]]; then
  echo "Usuario o tag inválido." >&2
  exit 2
fi

command -v docker >/dev/null 2>&1 || { echo "Docker no está instalado." >&2; exit 1; }
docker info >/dev/null 2>&1 || { echo "Docker no está disponible. Inicia Docker antes de continuar." >&2; exit 1; }

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
if [[ -d "$SCRIPT_DIR/../../data-ingestion" ]]; then
  PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
elif [[ -d "$SCRIPT_DIR/data-ingestion" ]]; then
  PROJECT_ROOT="$SCRIPT_DIR"
elif [[ -d "$SCRIPT_DIR/../data-ingestion" ]]; then
  PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
else
  echo "No se encontró la raíz del proyecto con data-ingestion." >&2
  exit 1
fi

declare -a SERVICES=(
  "container01-fires|Dockerfile|smokecast-ingesta-fires"
  "container02-cities|Dockerfile|smokecast-ingesta-cities"
  "container03-weather|Dockerfile|smokecast-ingesta-weather"
)

for entry in "${SERVICES[@]}"; do
  IFS='|' read -r context dockerfile image_name <<< "$entry"
  image="${DOCKERHUB_USER}/${image_name}:${IMAGE_TAG}"
  echo "==> Construyendo ${image}"
  docker build --pull --file "$PROJECT_ROOT/data-ingestion/$context/$dockerfile" \
    --tag "$image" "$PROJECT_ROOT/data-ingestion/$context"
  echo "==> Publicando ${image}"
  docker push "$image"
done

echo "Contenedores de ingesta publicados con tag ${IMAGE_TAG}."
