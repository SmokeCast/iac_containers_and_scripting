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

También puedes ejecutar los tres workers con el script incluido:

```bash
./run-ingestion.sh
```

`IMAGE_TAG` permite seleccionar la versión publicada por los scripts de
`image-publishing`. Los tres servicios son procesos puntuales y no se reinician
automáticamente. Para ejecutarlos periódicamente, programa estos mismos
comandos desde cron en la MV de ingesta. El script `run-ingestion.sh` usa
`flock` para evitar ejecuciones solapadas.

Por ejemplo, para ejecutar la ingesta diariamente a las 02:00:

```cron
0 2 * * * /opt/smokecast/mv_ingesta/run-ingestion.sh >> /var/log/smokecast-ingesta.log 2>&1
```

El cron debe usar la ruta real donde clones esta carpeta. Los workers terminan
al completar la carga; cron es quien inicia una nueva ejecución periódica.
