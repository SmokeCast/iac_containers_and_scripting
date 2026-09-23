# MV de ingesta

Esta carpeta contiene el Compose de despliegue y las variables de la MV de
ingesta. El Compose usa imágenes publicadas en Docker Hub; el código fuente y
los Dockerfiles están en [`data-ingestion/`](../../../data-ingestion/).

```bash
cp env.example .env
# Cambia empuiquin24 en docker-compose.yml si utilizas otro usuario de Docker Hub.
# Define los hosts privados de la MV de bases de datos en .env.
docker compose pull
docker compose run --rm fires-ingestion
docker compose run --rm cities-ingestion
docker compose run --rm weather-ingestion
```

`IMAGE_TAG` permite seleccionar la versión publicada por los scripts de
`image-publishing`. Los tres servicios son procesos puntuales y no se reinician
automáticamente.
